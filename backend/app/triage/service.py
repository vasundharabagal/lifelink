"""Unified triage service coordinating Tier 1 rules and Tier 2 LLM extraction (Spec §5.2, §5.4, §5.6).

Enforces the non-negotiable escalate-only safety invariant:
1. Deterministic rules engine is the ultimate authority on priority and protocol selection.
2. The optional LLM extractor only proposes candidate condition tokens.
3. Conditions are merged via programmatic union; priority is re-evaluated deterministically.
4. AI can only escalate urgency, never de-escalate or omit red flags.
5. Failures or timeouts trigger clean fallback with audit logging without stalling SOS flow.
"""
import logging
from typing import Optional
import uuid
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.enums import Priority
from app.schemas.triage import TriageInput, TriageResult
from app.services.audit import log_audit_event
from app.triage.llm_adapter import get_llm_extractor
from app.triage.rules import evaluate_rules
from app.triage.sanitizer import sanitize_description

logger = logging.getLogger(__name__)

# Urgency rank mapping: lower number = higher urgency
_PRIORITY_RANK = {
    Priority.P1_CRITICAL: 1,
    Priority.P2_SERIOUS: 2,
    Priority.P3_STABLE: 3,
}


class TriageService:
    """Orchestrates multi-tier clinical emergency classification."""

    async def evaluate_triage(
        self,
        input_data: TriageInput,
        is_demo: bool = False,
        db: Optional[Session] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> TriageResult:
        """Evaluate triage input across deterministic rules and optional LLM extractor."""
        # 1. Sanitize user description
        sanitized_desc = sanitize_description(input_data.description)
        sanitized_input = input_data.model_copy(update={"description": sanitized_desc})

        # 2. Tier 1 Deterministic Rules Extraction (Baseline Authority)
        tier1_result = evaluate_rules(sanitized_input, source="rules")

        # 3. Check if Tier 2 LLM Extraction is active and applicable
        llm_disabled = (is_demo and settings.DEMO_DISABLE_LLM) or settings.LLM_PROVIDER == "none"
        if not sanitized_desc or llm_disabled:
            return tier1_result

        # 4. Invoke Tier 2 LLM Extractor
        extractor = get_llm_extractor(is_demo=is_demo)
        llm_result = await extractor.extract(sanitized_desc)

        # 5. Handle LLM Fallback or Error
        if llm_result.fallback_triggered or not llm_result.success or not llm_result.payload:
            logger.info("Tier 2 LLM extraction fallback triggered: %s", llm_result.error)
            if db:
                try:
                    log_audit_event(
                        db=db,
                        action="TRIAGE_LLM_FALLBACK",
                        resource_type="triage",
                        resource_id="preview",
                        outcome="allow",
                        actor_user_id=user_id,
                        actor_role="citizen",
                        meta={"reason": llm_result.error or "timeout_or_unparseable"},
                    )
                except Exception as log_err:
                    logger.warning("Failed to record TRIAGE_LLM_FALLBACK audit log: %s", log_err)
            return tier1_result

        # 6. Programmatic Union: Merge Condition Tokens
        llm_conditions = set(llm_result.payload.conditions)
        if not llm_conditions:
            return tier1_result

        merged_conditions = set(tier1_result.observed_conditions) | llm_conditions

        # 7. Deterministic Re-evaluation over Programmatic Union
        hybrid_result = evaluate_rules(
            sanitized_input,
            additional_conditions=merged_conditions,
            source="hybrid",
        )

        # 8. Enforce Escalate-Only Invariant (D-44)
        # Verify priority is equal or higher urgency
        tier1_rank = _PRIORITY_RANK.get(tier1_result.priority, 2)
        hybrid_rank = _PRIORITY_RANK.get(hybrid_result.priority, 2)

        final_priority = hybrid_result.priority
        final_ambulance = hybrid_result.ambulance_required

        if hybrid_rank > tier1_rank:
            # Anomaly safety guard: LLM attempt to downgrade is overridden
            logger.warning(
                "Escalate-only violation prevented: Tier 1 (%s) > Hybrid (%s). Clamping to Tier 1.",
                tier1_result.priority,
                hybrid_result.priority,
            )
            final_priority = tier1_result.priority
            final_ambulance = tier1_result.ambulance_required

        if tier1_result.ambulance_required and not final_ambulance:
            final_ambulance = True

        # Ensure all red flags from tier 1 remain present
        all_red_flags = sorted(
            list(set(tier1_result.red_flags) | set(hybrid_result.red_flags)),
            key=lambda x: x.value,
        )

        final_confidence = max(tier1_result.confidence, llm_result.payload.confidence)

        return hybrid_result.model_copy(
            update={
                "priority": final_priority,
                "ambulance_required": final_ambulance,
                "red_flags": all_red_flags,
                "confidence": round(final_confidence, 2),
            }
        )


# Process-wide singleton
triage_service = TriageService()
