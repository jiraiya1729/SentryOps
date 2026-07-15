import uuid
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.guardian.state import (GuardianState, InvestigationState, InvestigationStatus, Severity)
from app.guardian.nodes.gather import gather_evidence_node
from app.guardian.nodes.analyze import analyze_node
from app.guardian.nodes.remediate import decide_remediation_node
from app.guardian.nodes.execute import execute_node

def should_remediate(state: GuardianState) -> str:
    if state.severity in (Severity.CRITICAL, Severity.HIGH):
        if state.root_causes:
            return "decide_remediation"
    return "end"


def needs_approval(state: GuardianState) -> str:
    pending = [r for r in state.remediations if r.requires_approval and not r.approved]
    if pending:
        return "await_approval"
    
    actionable = [r for r in state.remediations if not r.executed]
    if actionable:
        return "execute"
    return "end"


def approval_result(state: GuardianState) -> str:
    approved = [r for r in state.remediations if r.approved and not r.executed]
    if approved:
        return "execute"
    return "end"

def build_guardian_graph():
    graph = StateGraph(GuardianState)

    graph.add_node("gather_evidence", gather_evidence_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("decide_remediation", decide_remediation_node)
    graph.add_node("await_approval", await_approval_node)
    graph.add_node("execute", execute_node)

    graph.set_entry_point("gather_evidence")

    graph.add_edge("gather_evidence", "analyze")
    graph.add_conditional_edges("analyze", should_remediate, {"decide_remediation": "decide_remediation", "end":END})
    graph.add_conditional_edges("decide_remediation", needs_approval, {"await_approval": "await_approval", "execute": "execute", "end": END})
    graph.add_conditional_edges("await_approval", approval_result, {"execute": "execute", "end": END}) 
    graph.add_edge("execute", END)

    return graph


investigation_app = build_guardian_graph().compile(checkpointer=MemorySaver())


async def await_approval_node(state: GuardianState) -> dict:
    return {
        "status": InvestigationState.AWAITING_APPROVAL,
        "nodes_visited": state.nodes_visited + ["await_approval"]
    }

async def start_investigation(
    trigger_type: str,
    trigger_source: str,
    description: str,
    namespace: str | None = None,
    resource_kind: str | None = None, 
    resource_name: str | None = None,
    metadata: dict | None = None,
) -> str:
    from app.guardian.state import InvestigationTrigger

    investigation_id = str(uuid.uuid4())

    initial_state = {
        "investigation_id": investigation_id,
        "status": InvestigationState.GATHERING,
        "started_at": datetime.now(timezone.utc),
        "trigger": InvestigationTrigger(
            type=trigger_type,
            source=trigger_source,
            description=description,
            metadata=metadata or {},
        ),
        "namespace": namespace,
        "resource_kind": resource_kind,
        "resource_name": resource_name,
        "evidence": [],
        "root_causes": [],
        "remediations": [],
        "nodes_visited": [],
    }

    config = {"configurable": {"thread_id": investigation_id}}
    await investigation_app.ainvoke(initial_state, config)
    return investigation_id


async def resume_investigation(investigation_id: str, approved: bool) -> dict:
    config = {"configurable": {"thread_id": investigation_id}}
    state = await investigation_app.aget_state(config)

    if approved:
        remediations = state.value.get("remediations", [])
        for r in remediations:
            if r.requires_approval:
                r.approved = True
        await investigation_app.aupdate_state(config, {"remediations": remediations})
    
    result = await investigation_app.ainvoke(None, config)
    return result