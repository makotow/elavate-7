"""Zero-Trust Security, HMAC Composite Token Auth, Model Armor Input/Output Guardrails & Cloud SDP SPII Redaction."""
import hmac
import hashlib
import re
from contextvars import ContextVar
from typing import Any

# Context variable holding the currently authenticated employee ID for the active request/turn
current_authenticated_employee_id: ContextVar[str] = ContextVar("current_authenticated_employee_id", default="EMP-9021")

import os

SECRET_HMAC_KEY = os.environ.get(
    "SECRET_HMAC_KEY", "hr-agent-mvp1-composite-token-secret-key-2026"
).encode("utf-8")


def generate_composite_token(employee_id: str) -> str:
    """Generates an HMAC-SHA256 signed Composite Authentication Token (FR-3.1)."""
    sig = hmac.new(SECRET_HMAC_KEY, employee_id.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"{employee_id}:{sig}"


def verify_composite_token(token: str) -> str:
    """Verifies the Composite Token signature or defaults to EMP-769 in Demo Mode (User Auth Omitted)."""
    if not token or ":" not in token:
        return token.strip() if (token and token.strip().startswith("EMP-")) else "EMP-769"
    emp_id, sig = token.split(":", 1)
    expected_sig = hmac.new(SECRET_HMAC_KEY, emp_id.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    if hmac.compare_digest(sig, expected_sig):
        return emp_id
    raise PermissionError("Invalid Composite Authentication Token signature (FR-3.1 Security Breach).")


def check_input_safety(prompt: str) -> dict[str, Any]:
    """Emulates Model Armor Inline Input Guardrails (< 65ms overhead: FR-1.3, FR-5.4, NFR-1.1)."""
    p_lower = prompt.lower()

    # 1. Prompt Injection / Jailbreak Detection (FR-1.3)
    injection_patterns = [
        "ignore previous instructions",
        "ignore all previous",
        "disregard your system prompt",
        "you are now dan",
        "do anything now",
        "system override",
        "bypass security",
        "print your system instructions",
    ]
    for pat in injection_patterns:
        if pat in p_lower:
            return {
                "allowed": False,
                "category": "PROMPT_INJECTION_OR_JAILBREAK",
                "reason": f"Model Armor Security Block (FR-1.3): Detected adversarial prompt override pattern ('{pat}').",
                "safe_refusal_message": (
                    "申し訳ありませんが、セキュリティおよびAIガバナンスポリシー（Model Armor FR-1.3）により、"
                    "システムの指示を上書きするリクエストや不正な命令は処理できません。"
                ),
            }

    # 2. Domain Containment Check (FR-5.4 Off-topic filter)
    off_topic_patterns = [
        "write a python script",
        "write asorting algorithm",
        "quicksort in python",
        "recipe for chocolate cake",
        "who won the world cup",
        "stock price of",
        "translate this novel",
    ]
    for pat in off_topic_patterns:
        if pat in p_lower:
            return {
                "allowed": False,
                "category": "OFF_TOPIC_DOMAIN_CONTAINMENT",
                "reason": f"Model Armor Domain Containment (FR-5.4): Prompt falls outside corporate HR/IT domain ('{pat}').",
                "safe_refusal_message": (
                    "私は社内HR規程（休暇・福利厚生・異動）およびITサポート（WorkWeek / ServiceImmediately）専用の"
                    "アシスタントです（FR-5.4 Domain Containment）。一般のプログラミングや業務外のご質問にはお答えできません。"
                ),
            }

    return {"allowed": True, "category": "SAFE", "reason": "Passed Model Armor Input Guardrails."}


from app.gcp_services import redact_spii_with_cloud_dlp


def redact_spii(text: str) -> str:
    """Executes Google Cloud Sensitive Data Protection (Cloud DLP API `content:deidentify`) inline SPII masking (FR-1.4, NFR-1.3)."""
    return redact_spii_with_cloud_dlp(text)
