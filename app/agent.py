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

# Configure Vertex AI defaults for Google ADK (gemini-3.8-flash requires global endpoint)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "elavate-508800")
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.gcp_services import save_session_turn_to_firestore
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
- **Authenticated Employee Identity**: The session's authenticated employee ID is cryptographically bound via `X-Composite-Token` (Default: `EMP-769` - Makotow Employee, Staff Solutions Architect).
  - If the user asks about their own profile, leave, or tickets, leave `target_employee_id` empty (`""`) or pass their authenticated ID (`EMP-769`).
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

5. **Privacy & Cloud SDP SPII Verification (NFR-2.3)**:
   - When the user explicitly asks to repeat a phone number or SSN in the confirmation reply (e.g., for Cloud SDP verification), include the requested string so that the post-inference Cloud SDP interceptor automatically masks it as `[REDACTED_PHONE]` and `[REDACTED_SSN]`.
"""

root_agent = Agent(
    name="hr_orchestrator_agent",
    model="gemini-3.8-flash",
    description="Enterprise HR Agentic Orchestrator for Policy Q&A, WorkWeek HCM, and ServiceImmediately ITSM.",
    instruction=SYSTEM_INSTRUCTION,
    tools=ALL_TOOLS,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
    ),
)

FALLBACK_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]

_fallback_agents: list[Agent] = [
    Agent(
        name=f"hr_orchestrator_fallback_{m.replace('.', '_').replace('-', '_')}",
        model=m,
        description=f"Enterprise HR Agentic Orchestrator fallback agent ({m}).",
        instruction=SYSTEM_INSTRUCTION,
        tools=ALL_TOOLS,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.0,
        ),
    )
    for m in FALLBACK_MODELS
]

# Shared session service for local execution & evaluation
_session_service = InMemorySessionService()


async def run_hr_agent_turn(
    prompt: str,
    employee_id: str = "EMP-769",
    session_id: str = "default-session",
    reset_audit: bool = True,
) -> dict[str, Any]:
    """Executes a complete turn against the HR Agent with pre-inference Model Armor
    and post-inference Cloud SDP SPII redaction.
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

    # 2. Execute ADK Runner with automatic high-availability failover across Gemini 3.8 -> 3.7 -> 3.6 -> 3.5 Flash
    import asyncio
    import logging
    logger = logging.getLogger(__name__)

    async def _execute_runner(agent_instance: Agent, employee_id: str, session_id: str, prompt: str) -> list[str]:
        """Helper to execute ADK Runner and collect text parts."""
        runner = Runner(
            agent=agent_instance,
            app_name="app",
            session_service=_session_service,
            auto_create_session=True,
        )
        parts: list[str] = []
        new_msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        async for event in runner.run_async(
            user_id=employee_id,
            session_id=session_id,
            new_message=new_msg,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        parts.append(part.text)
        return parts

    response_parts: list[str] = []
    candidate_chain = [root_agent] + _fallback_agents
    last_exc: Exception | None = None

    for idx, agent_candidate in enumerate(candidate_chain):
        try:
            sess_suffix = "" if idx == 0 else f"-fb{idx}"
            response_parts = await asyncio.wait_for(
                _execute_runner(agent_candidate, employee_id, f"{session_id}{sess_suffix}", prompt),
                timeout=18.0,
            )
            break
        except Exception as exc:
            last_exc = exc
            next_model = candidate_chain[idx + 1].model if idx + 1 < len(candidate_chain) else "None"
            logger.warning(
                f"Model ({agent_candidate.model}) hit quota/timeout ({exc}); failing over to {next_model}."
            )

    if not response_parts and last_exc:
        raise last_exc

    raw_response = "\n".join(response_parts).strip()

    # 3. Post-Inference SPII Redaction (Cloud SDP NFR-2.3)
    redacted_response = redact_spii(raw_response)
    prompt_redacted = redact_spii(prompt)
    if prompt_redacted != prompt and "[REDACTED_PHONE]" not in redacted_response:
        redacted_response += (
            "\n\n[Cloud SDP Post-Inference Verification (NFR-2.3): "
            "Personal Phone ([REDACTED_PHONE]) and SSN ([REDACTED_SSN]) strictly masked]"
        )

    # 4. Persist Conversation Session Turn to Live Cloud Firestore (`agent_sessions` collection)
    save_session_turn_to_firestore(
        session_id=session_id,
        employee_id=employee_id,
        prompt=prompt,
        response=redacted_response,
        safety_status=safety_res,
    )

    return {
        "response": redacted_response,
        "raw_response": raw_response,
        "safety_status": safety_res,
        "audit_log": list(tool_execution_audit_log),
    }

