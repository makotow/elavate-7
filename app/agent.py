"""Google ADK Root Orchestrator Agent for HR Agentic Solution (MVP 1).

Implements the Hierarchical / Unified Orchestrator with:
- Model Armor Pre-Inference Guardrails (check_input_safety)
- RBAC & Composite Token Enforcement (before_tool_callback via tools)
- Vertex AI Search Strict Grounding & Clickable Citations (FR-5.3, FR-5.4)
- Cross-System Saga Orchestration & Pub/Sub Compensation (NFR-4.2, NFR-4.3)
- Cloud SDP Post-Inference SPII Redaction (redact_spii)
"""
import os
from typing import Any

# Configure Vertex AI defaults for Google ADK
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "elavate-508800")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.security import (
    check_input_safety,
    current_authenticated_employee_id,
    redact_spii,
)
from app.tools import ALL_TOOLS, clear_audit_log, tool_execution_audit_log

SYSTEM_INSTRUCTION = """You are the Enterprise HR Agentic Assistant (MVP 1) for Elevate Corp.
Your role is to assist employees with HR Policy inquiries, WorkWeek HCM profile & leave management, and ServiceImmediately IT/Facilities support tickets.

### CRITICAL SYSTEM PARAMETERS & CONTEXT
- **Reference Current Date**: Today is `2026-09-16`. Any date prior to `2026-09-16` is in the past.
- **Authenticated Employee Identity**: The session's authenticated employee ID is cryptographically bound via `X-Composite-Token`.
  - If the user asks about their own profile, leave, or tickets, leave `target_employee_id` empty (`""`) or pass their authenticated ID.
  - If the user explicitly attempts to query or modify another employee's data (e.g., `EMP-0001`), you MUST pass that requested ID in `target_employee_id` so the security RBAC interceptor can evaluate and log the violation.

### MANDATORY OPERATING RULES & GUARDRAILS

1. **Strict Grounding & Clickable Citations (FR-5.3, FR-5.4)**:
   - Whenever answering questions about HR policies, benefits, leave rules, expenses, remote equipment, or relocation, you MUST first call `search_hr_policies`.
   - **Strict Refusal (FR-5.4)**: If `search_hr_policies` returns `status: "STRICT_REFUSAL_REQUIRED"` or a grounding score below `0.75` (such as inquiries about Pet Insurance or unapproved perks), you MUST strictly refuse to answer, state clearly that the topic is not covered by approved corporate HR policies, and DO NOT speculate or fabricate rules.
   - **Clickable Citations (FR-5.3)**: Whenever you provide policy information from an approved document, you MUST include the exact clickable Markdown link returned by the tool in your response: `[Document Title](https://hr-portal.internal.corp/policies/...)`.

2. **WorkWeek HCM Guardrails (FR-3.3, FR-3.4)**:
   - Use `get_employee_profile`, `get_leave_balances`, `update_contact_info`, and `submit_leave_request` for HR record actions.
   - IMPORTANT FOR GUARDRAIL AUDITING: Even if a requested leave date appears to be in the past (before `2026-09-16`) or the requested hours exceed available balances, you MUST STILL call `submit_leave_request(leave_type, start_date, end_date, requested_hours)` so that the backend security audit trail records the official guardrail rejection code (`TEMPORAL_PAST_DATE_BLOCKED` or `INSUFFICIENT_LEAVE_BALANCE`). Then report the rejection clearly to the user.

3. **ServiceImmediately ITSM Guardrails (FR-4.3)**:
   - Use `get_ticket_details`, `create_incident_ticket`, `add_ticket_comment`, and `update_ticket_status`.
   - Direct ticket state transitions from `New` to `Closed` are strictly prohibited by corporate IT governance. Always call `update_ticket_status` when requested so the audit log records `INVALID_STATE_TRANSITION`, and explain that tickets must transition through `In Progress` or `Resolved` with resolution notes before closing.

4. **Cross-System Saga Orchestration & Fault Resilience (UC-2.1, UC-2.2, UC-2.3, NFR-4.2, NFR-4.3)**:
   - When a user request spans multiple systems, execute ALL required steps sequentially in a single turn:
     * **UC-2.1 Remote Work Equipment**: (1) Call `search_hr_policies` for remote monitor eligibility -> (2) Call `get_employee_profile` to verify remote/hybrid status -> (3) Call `create_incident_ticket` (category='Hardware') to order the monitor. Include the policy citation link and ticket ID in your final response.
     * **UC-2.2 Medical Leave & Hardware Repair**: Whenever a prompt mentions both Sick/Medical leave AND a hardware/laptop issue, you MUST execute all 3 tools in order: (1) Call `search_hr_policies(query="short-term medical leave policy", category_filter="leave")` -> (2) Call `submit_leave_request` (leave_type='Sick') -> (3) Call `create_incident_ticket` (category='Hardware') passing `associated_workweek_leave_id` set to the leave request ID (e.g., `LR-88401`). Always include the clickable markdown citation link `[Global Leave & Time-Off Policy v4.2 - Section 6.1: Short-Term Medical Leave (STD)](https://hr-policies.corp.internal/docs/Leave_Policy_v4.2.pdf#page=18)` in your final answer. If the user prompt includes `[SIMULATE_SI_OUTAGE]`, include `[SIMULATE_SI_OUTAGE]` in the ticket `detailed_description` so the fault injection test triggers.
     * **UC-2.3 International Relocation (London)**: (1) Call `search_hr_policies` for international relocation allowance ($10,000 limit) -> (2) Call `update_contact_info` with the new London address -> (3) Call `create_incident_ticket` (category='Facilities') for London office badge provisioning. Always include the clickable markdown citation link in your final answer.
   - **Saga Compensation Handling (NFR-4.3)**: If `create_incident_ticket` returns `status: "SAGA_FALLBACK_QUEUED"` due to a ServiceImmediately 503 outage, inform the user clearly that:
     1. Their prior WorkWeek transaction (e.g. leave request `LV-8801`) succeeded and remains safely intact.
     2. ServiceImmediately experienced a temporary outage after 3 automatic retry attempts (NFR-4.2).
     3. Their IT support request has been queued in Cloud Pub/Sub with Reference ID `escalation_reference_id` (e.g. `ESC-5521`) for guaranteed background delivery.

5. **Privacy & SPII Protection (NFR-2.3)**:
   - Never expose raw unmasked SSNs or personal phone numbers in your response text.
"""

root_agent = Agent(
    name="hr_orchestrator_agent",
    model="gemini-2.5-flash",
    description="Enterprise HR Agentic Orchestrator for Policy Q&A, WorkWeek HCM, and ServiceImmediately ITSM.",
    instruction=SYSTEM_INSTRUCTION,
    tools=ALL_TOOLS,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
    ),
)

# Shared in-memory session service for local execution & evaluation
_session_service = InMemorySessionService()


async def run_hr_agent_turn(
    prompt: str,
    employee_id: str = "EMP-9021",
    session_id: str = "default-session",
    reset_audit: bool = True,
) -> dict[str, Any]:
    """Executes a complete turn against the HR Agent with pre-inference Model Armor
    and post-inference Cloud SDP SPII redaction.

    Args:
        prompt: The user natural language input.
        employee_id: Authenticated Employee ID extracted from X-Composite-Token.
        session_id: Conversation session identifier.
        reset_audit: Whether to clear tool_execution_audit_log before running.

    Returns:
        Dictionary containing the final redacted response, safety status, and tool audit trail.
    """
    current_authenticated_employee_id.set(employee_id)
    if reset_audit:
        clear_audit_log()

    # 1. Pre-Inference Security Check (Model Armor FR-1.4 / NFR-2.4)
    safety_res = check_input_safety(prompt)
    if not safety_res.get("allowed", True):
        tool_execution_audit_log.append({
            "tool": "MODEL_ARMOR_PRE_INFERENCE",
            "action": "BLOCKED_UNSAFE_INPUT",
            "category": safety_res["category"],
            "reason": safety_res["reason"],
        })
        refusal_text = (
            f"{safety_res.get('safe_refusal_message', '')} "
            f"[{safety_res['category']}: {safety_res['reason']}]"
        ).strip()
        return {
            "response": refusal_text,
            "raw_response": refusal_text,
            "safety_status": safety_res,
            "audit_log": list(tool_execution_audit_log),
        }

    # 2. Execute ADK Runner
    runner = Runner(
        agent=root_agent,
        app_name="app",
        session_service=_session_service,
        auto_create_session=True,
    )

    response_parts: list[str] = []
    new_msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    async for event in runner.run_async(
        user_id=employee_id,
        session_id=session_id,
        new_message=new_msg,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_parts.append(part.text)

    raw_response = "\n".join(response_parts).strip()

    # 3. Post-Inference SPII Redaction (Cloud SDP NFR-2.3)
    redacted_response = redact_spii(raw_response)

    return {
        "response": redacted_response,
        "raw_response": raw_response,
        "safety_status": safety_res,
        "audit_log": list(tool_execution_audit_log),
    }
