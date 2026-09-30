"""Standalone golden triage evaluation runner and metrics calculator (Spec §5.7, TRIAGE-05).

Evaluates the triage rules engine (and hybrid engine) against the 45-case golden dataset.
Calculates overall accuracy, per-class red-flag recall, safe over-triggering rate,
and strictly asserts that unsafe downgrades count is exactly 0.
"""
import argparse
import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from app.domain.enums import ConditionCode, Priority, ProtocolId
from app.schemas.triage import TriageAnswers, TriageInput, TriageResult
from app.triage.rules import evaluate_rules
from app.triage.service import triage_service

logger = logging.getLogger(__name__)

_DEFAULT_GOLDEN_PATH = Path(__file__).resolve().parents[2] / "tests" / "golden" / "golden_triage.jsonl"


@dataclass
class EvalCaseResult:
    """Outcome of evaluating an individual golden case."""
    case_id: str
    category: str
    expected_priority: str
    actual_priority: str
    expected_ambulance: bool
    actual_ambulance: bool
    expected_protocol: str
    actual_protocol: str
    is_red_flag: bool
    is_unsafe_downgrade: bool
    is_safe_upgrade: bool
    is_priority_match: bool
    is_protocol_match: bool
    downgrade_reason: Optional[str] = None


@dataclass
class EvalSummary:
    """Aggregate evaluation metrics across the golden dataset."""
    total_cases: int = 0
    priority_accuracy: float = 0.0
    protocol_accuracy: float = 0.0
    red_flag_recall: float = 0.0
    red_flag_precision: float = 0.0
    unsafe_downgrades: int = 0
    safe_upgrades: int = 0
    case_results: List[EvalCaseResult] = field(default_factory=list)
    failures: List[Dict[str, Any]] = field(default_factory=list)


def evaluate_case(case_data: Dict[str, Any], use_llm: bool = False) -> EvalCaseResult:
    """Evaluate a single golden case against the triage engine."""
    case_id = case_data["id"]
    category = case_data.get("category", "UNKNOWN")
    expected_priority = case_data["expected_priority"]
    expected_ambulance = case_data["expected_ambulance"]
    expected_protocol = case_data["expected_protocol"]
    is_red_flag = case_data.get("is_red_flag", False)
    expected_conditions = set(case_data.get("expected_conditions", []))

    # Parse input answers
    ans_data = case_data.get("answers")
    answers = None
    if ans_data:
        answers = TriageAnswers(
            awake=ans_data.get("awake"),
            breathing=ans_data.get("breathing"),
            severe_bleeding=ans_data.get("severe_bleeding"),
        )

    triage_input = TriageInput(
        quick_type=case_data.get("quick_type"),
        answers=answers,
        description=case_data.get("description_text"),
    )

    if use_llm:
        # Run async triage service synchronously for evaluator CLI
        result = asyncio.run(triage_service.evaluate_triage(triage_input, is_demo=False))
    else:
        result = evaluate_rules(triage_input)

    actual_priority = result.priority.value
    actual_ambulance = result.ambulance_required
    actual_protocol = result.protocol_id.value

    # Matches
    is_priority_match = (actual_priority == expected_priority)
    is_protocol_match = (actual_protocol == expected_protocol)

    # Safe upgrade check (over-triggering for safety is allowed)
    is_safe_upgrade = False
    if expected_priority == "P2_SERIOUS" and actual_priority == "P1_CRITICAL":
        is_safe_upgrade = True
    elif expected_priority == "P3_STABLE" and actual_priority in ("P1_CRITICAL", "P2_SERIOUS"):
        is_safe_upgrade = True

    # Strict 3-Point Unsafe Downgrade Definition (D-51):
    # 1. Priority downgrade (P1 -> P2/P3, or P2 -> P3)
    # 2. Ambulance omission (expected true, actual false)
    # 3. Missing red flag when case is red flag
    is_unsafe_downgrade = False
    downgrade_reasons = []

    # Check 1: Priority downgrade
    if expected_priority == "P1_CRITICAL" and actual_priority != "P1_CRITICAL":
        is_unsafe_downgrade = True
        downgrade_reasons.append(f"Priority downgraded from {expected_priority} to {actual_priority}")
    elif expected_priority == "P2_SERIOUS" and actual_priority == "P3_STABLE":
        is_unsafe_downgrade = True
        downgrade_reasons.append(f"Priority downgraded from {expected_priority} to {actual_priority}")

    # Check 2: Ambulance omission
    if expected_ambulance and not actual_ambulance:
        is_unsafe_downgrade = True
        downgrade_reasons.append("Ambulance required omitted (expected True, actual False)")

    # Check 3: Missing red flag
    if is_red_flag:
        actual_cond_values = {c.value for c in result.observed_conditions}
        # If none of the expected conditions were detected in observed conditions
        if expected_conditions and not (expected_conditions & actual_cond_values):
            is_unsafe_downgrade = True
            downgrade_reasons.append(f"Expected red-flag conditions {expected_conditions} missing from {actual_cond_values}")

    return EvalCaseResult(
        case_id=case_id,
        category=category,
        expected_priority=expected_priority,
        actual_priority=actual_priority,
        expected_ambulance=expected_ambulance,
        actual_ambulance=actual_ambulance,
        expected_protocol=expected_protocol,
        actual_protocol=actual_protocol,
        is_red_flag=is_red_flag,
        is_unsafe_downgrade=is_unsafe_downgrade,
        is_safe_upgrade=is_safe_upgrade,
        is_priority_match=is_priority_match,
        is_protocol_match=is_protocol_match,
        downgrade_reason="; ".join(downgrade_reasons) if downgrade_reasons else None,
    )


def evaluate_dataset(
    dataset_path: Optional[Path] = None,
    use_llm: bool = False,
) -> EvalSummary:
    """Evaluate all cases in the golden triage dataset and return aggregate summary metrics."""
    path = dataset_path or _DEFAULT_GOLDEN_PATH
    if not path.exists():
        raise FileNotFoundError(f"Golden dataset not found at {path}")

    case_results: List[EvalCaseResult] = []
    failures: List[Dict[str, Any]] = []

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_cases = len(lines)
    priority_matches = 0
    protocol_matches = 0
    unsafe_downgrades = 0
    safe_upgrades = 0

    red_flag_cases_total = 0
    red_flag_detected_correctly = 0
    p1_predicted_total = 0

    for line in lines:
        case_data = json.loads(line)
        res = evaluate_case(case_data, use_llm=use_llm)
        case_results.append(res)

        if res.is_priority_match:
            priority_matches += 1
        elif res.is_safe_upgrade:
            safe_upgrades += 1

        if res.is_protocol_match:
            protocol_matches += 1

        if res.is_unsafe_downgrade:
            unsafe_downgrades += 1
            failures.append({
                "id": res.case_id,
                "category": res.category,
                "reason": res.downgrade_reason,
                "expected_priority": res.expected_priority,
                "actual_priority": res.actual_priority,
                "expected_protocol": res.expected_protocol,
                "actual_protocol": res.actual_protocol,
            })

        if res.is_red_flag:
            red_flag_cases_total += 1
            if res.actual_priority == "P1_CRITICAL":
                red_flag_detected_correctly += 1

        if res.actual_priority == "P1_CRITICAL":
            p1_predicted_total += 1

    red_flag_recall = (
        red_flag_detected_correctly / red_flag_cases_total
        if red_flag_cases_total > 0 else 1.0
    )
    red_flag_precision = (
        red_flag_detected_correctly / p1_predicted_total
        if p1_predicted_total > 0 else 1.0
    )

    return EvalSummary(
        total_cases=total_cases,
        priority_accuracy=round((priority_matches + safe_upgrades) / total_cases, 4) if total_cases else 0.0,
        protocol_accuracy=round(protocol_matches / total_cases, 4) if total_cases else 0.0,
        red_flag_recall=round(red_flag_recall, 4),
        red_flag_precision=round(red_flag_precision, 4),
        unsafe_downgrades=unsafe_downgrades,
        safe_upgrades=safe_upgrades,
        case_results=case_results,
        failures=failures,
    )


def print_summary(summary: EvalSummary) -> None:
    """Pretty-print formatted metrics summary table to stdout."""
    border = "=" * 68
    sep = "-" * 68

    print(f"\n{border}")
    print("  LIFELINK CLINICAL AI & TRIAGE EVALUATION REPORT (Spec Sec 5.7)")
    print(f"{border}")
    print(f"  Total Cases Evaluated:         {summary.total_cases}")
    print(f"  Overall Priority Accuracy:     {summary.priority_accuracy * 100:.1f}% (incl. safe upgrades)")
    print(f"  Primary Protocol Accuracy:     {summary.protocol_accuracy * 100:.1f}%")
    print(f"  Red-Flag Recall:               {summary.red_flag_recall * 100:.1f}% (Target: >= 95.0%)")
    print(f"  Red-Flag Precision:            {summary.red_flag_precision * 100:.1f}%")
    print(f"  Safe Over-Trigger Upgrades:    {summary.safe_upgrades}")
    print(f"{sep}")

    if summary.unsafe_downgrades == 0:
        print("  Unsafe Downgrades:             0 (PASSED - ZERO TOLERANCE GATE)")
    else:
        print(f"  Unsafe Downgrades:             {summary.unsafe_downgrades} (FAILED)")

    print(f"{border}")

    if summary.failures:
        print("\n  FAILURES & UNSAFE DOWNGRADES DIAGNOSTICS:")
        for fail in summary.failures:
            print(f"  - [{fail['id']}] {fail['category']}: {fail['reason']}")
            print(f"    Expected: Priority={fail['expected_priority']}, Protocol={fail['expected_protocol']}")
            print(f"    Actual:   Priority={fail['actual_priority']}, Protocol={fail['actual_protocol']}")
        print(f"{border}\n")


def main() -> None:
    """CLI entrypoint for triage evaluation runner."""
    parser = argparse.ArgumentParser(description="Evaluate LIFELINK triage engine against golden dataset.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_DEFAULT_GOLDEN_PATH,
        help="Path to golden triage JSONL dataset",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable Tier 2 LLM extraction during evaluation",
    )
    args = parser.parse_args()

    summary = evaluate_dataset(dataset_path=args.dataset, use_llm=args.llm)
    print_summary(summary)

    # Gate verification: fail if unsafe downgrades > 0 or red-flag recall < 0.95
    if summary.unsafe_downgrades > 0 or summary.red_flag_recall < 0.95:
        logger.error(
            "Evaluation quality gate failed: unsafe_downgrades=%d, red_flag_recall=%.2f",
            summary.unsafe_downgrades,
            summary.red_flag_recall,
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
