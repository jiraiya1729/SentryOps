import asyncio
import logging

from app.core.k8s_client import core_v1, apps_v1
from app.guardian.config import guardian_config
from app.guardian.state import GuardianState, InvestigationStatus

logger = logging.getLogger(__name__)

async def decide_remediation_node(state: GuardianState) -> dict:

    logger.info(f"Deciding remediation for investigation {state.investigation_id}")

    remediations = state.remediations

    if not remediations:
        return {
            "status": InvestigationStatus.COMPLETED,
            "nodes_visited": state.nodes_visited + ["decide_remediation"],
        }


    if not guardian_config.AUTO_REMEDIATION_ENABLED:
        for r in remediations:
            r.requires_approval = True

    if guardian_config.REQUIRE_HUMAN_APPROVAL:
        for r in remediations:
            if r.risk_level in ("medium", "high"):
                r.requires_approval = True

    return {
        "remediations": remediations,
        "nodes_visited": state.nodes_visited + ["decide_remediation"]
    }