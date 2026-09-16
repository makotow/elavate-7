"""Parametrized Pytest Verification for all 16 Golden Dataset Test Cases (SDD Section 9)."""
import json
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DATASET_PATH = PROJECT_ROOT / "tests" / "eval" / "datasets" / "golden_dataset.json"
RESULTS_JSON_PATH = PROJECT_ROOT / "artifacts" / "grade_results" / "results_latest.json"


with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
    GOLDEN_CASES = json.load(f)

with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
    EVAL_RESULTS_DATA = json.load(f)
    EVAL_RESULTS_MAP = {r["case_id"]: r for r in EVAL_RESULTS_DATA["results"]}


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c["case_id"] for c in GOLDEN_CASES])
def test_golden_dataset_case_verification(case: dict) -> None:
    """Verifies each of the 16 Golden Dataset cases achieved 100% pass across all 4 metrics."""
    case_id = case["case_id"]
    assert case_id in EVAL_RESULTS_MAP, f"Missing evaluation result for case {case_id}"
    res = EVAL_RESULTS_MAP[case_id]

    assert res["passed"] is True, f"Case {case_id} failed: {res['details']}"
    assert res["metrics"]["task_and_grounding_accuracy"] == 1.0
    assert res["metrics"]["citation_link_integrity"] == 1.0
    assert res["metrics"]["guardrail_and_trajectory_check"] == 1.0
    assert res["metrics"]["zero_trust_security_and_spii_check"] == 1.0
