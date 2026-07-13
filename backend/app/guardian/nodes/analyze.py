import json
import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.guardian.config import guardian_config
from app.guardian.state import GuardianState, InvestigationState, RootCause, Remediation, Severity

logger = logging.getLogger(__name__)

ANALYZE_PROMPT = """
You are an expert SRE investigating a Kubernetes cluster issue. Analyze the evidence below and provide a root cause analysis.

## Investigation Context
- Trigger: {trigger_description}
- Namespace: {namespace}
- Resource: {resource_kind}/{resource_name}

## Evidence Gathered
{evidence_text}

## Your Task
Analyze the evidence and provide:
1. **Root Cause**: What is the primary cause of this issue? Be specific.
2. **Confidence**: How confident are you (0.0-1.0)?
3. **Category**: One of: resource_exhaustion, crash_loop, config_error, network_issue, scheduling_failure, image_issue, storage_issue, dependency_failure, unknown
4. **Severity**: critical, high, medium, low, info
5. **Affected Resources**: List all resources involved
6. **Remediation**: What actions should be taken? For each action, specify:
   - Description of the action
   - Type: manual, auto_scale, restart, rollback, config_change
   - Risk level: low, medium, high
   - Whether it needs human approval

Respond in this exact JSON format:
```json
{{
  "root_causes": [
    {{
      "summary": "...",
      "confidence": 0.85,
      "category": "...",
      "affected_resources": ["ns/kind/name", ...],
      "evidence_refs": ["which evidence supports this"]
    }}
  ],
  "severity": "high",
  "summary": "One paragraph executive summary of the issue and its impact",
  "remediations": [
    {{
      "action": "Human-readable description",
      "type": "restart",
      "risk_level": "low",
      "requires_approval": true
    }}
  ]
}}
```


"""

def _format_evidence(evidence: list) -> str:
    
    sections = []
    for i, e in enumerate(evidence, 1):
        section = f"### Evidence {i}: {e.source.upper()}\n"
        section += f"**Summary**: {e.summary}\n"
        if isinstance(e.data, dict):
            section += f"**Data**: {json.dumps(e.data, indent=2, default=str)[:2000]}\n"
        elif isinstance(e.data, list):
            section += f"**Data** ({len(e.data)} items): {json.dumps(e.data[:10], indent=2, default=str)[:2000]}\n"
        else:
            section += f"**Data**: {str(e.data)[:2000]}\n"
        sections.append(section)
    return "\n".join(sections)

async def analyze_node(state: GuardianState)-> dict:
    
    logger.info(f"Analyzing investigation {state.investigation_id}")

    if not state.evidence:
        logger.warning(" No evidence to analyze")
        return {
            "status": InvestigationState.COMPLETED,
            "summary": "Investigation completed with no evidence gathered",
            "severity": Severity.INFO,
            "nodes_visited": state.nodes_visited + ["analyze"],
        }

    trigger_desc = state.trigger.description if state.trigger else "Unknown trigger"
    evidence_text = _format_evidence(state.evidence)

    prompt = ANALYZE_PROMPT.format(
      trigger_description = trigger_desc,
      namespace = state.namespace or "all",
      resource_kind = state.resource_kind or "unknown",
      resource_name = state.resource_name or "unknown",
      evidence_text = evidence_text,
    )

    try:
      model = ChatBedrockConverse(
        model = guardian_config.GUARDIAN_MODEL,
        region_name = settings.AWS_REGION,
        temperature = 0,
        max_tokens = guardian_config.GUARDIAN_MAX_TOKENS,
      )

      response = await model.ainvoke([HumanMessage(content=prompt)])

      response_text = response.content if isinstance(response.content, str) else str(response.content)

      json_str = response_text
      if "```json" in json_str:
        json_str = json_str.split("```json")[-1].split("```")[0]
      elif "```" in json_str:
        json_str = json_str.split("```")

      analysis = json.loads(json_str.strip())

      root_cause = [
        RootCause(
          summary = rc["summary"],
          confidence = rc.get("confidence", 0.5),
          category = rc.get("category", "unknown"),
          affected_resources = rc.get("affected_resources", []),
          evidence_refs = rc.get("evidence_refs", []),
        )

        for rc in analysis.get("root_causes", [])

      ]

      remediations = [
        Remediation(
          action = r["action"],
          type = r.get("type", "manual"),
          risk_level = r.get("risk_level", "medium"),
          requires_approval = r.get("requires_approval", True)
        )
        for r in analysis.get("remediations", [])
      ]

      severity_map = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO
      }

      severity = severity_map.get(analysis.get("severity", "medium", Severity.MEDIUM))

      return {
        "status": InvestigationState.ANALYZED,
        "root_causes": root_causes,
        "remediations": remediations,
        "severity": severity,
        "summary": analysis.get("summary", "Analysis complete."),
        "nodes_visited": state.nodes_visited + ["analyze"],
      }

      

      
    except json.JSONDecodeError as e:
      logger.error(f"Failed to parse claude analysis response: {e}")
      return {
        "status": InvestigationState.COMPLETED,
        "summary": f"Analysis completed but response parsing failed: {e}",
        "severity": Severity.MEDIUM,
        "nodes_visited": state.nodes_visited + ["analyze"],
        "error": str(e),
      }

    except Exception as e:
      logger.error(f"Analysis node failed: {e}")
      return {
        "status": InvestigationState.FAILED,
        "error": str(e),
        "nodes_visited": state.nodes_visited + ["analyze"]
      }

