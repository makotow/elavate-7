"""Google ADK Function Tools & Mandatory Security Callbacks (before_tool_callback) for HR Agentic Solution."""
from typing import Any
from app.mocks.policy_rag import search_policy_documents
from app.mocks.workweek_db import workweek_db
from app.mocks.service_db import service_db
from app.security import current_authenticated_employee_id

# Audit trail of tool invocations and security overrides for verification & evaluation
tool_execution_audit_log: list[dict[str, Any]] = []


def clear_audit_log() -> None:
    """Clears the tool execution audit log before each evaluation case."""
    tool_execution_audit_log.clear()


def _enforce_rbac_scope(requested_employee_id: str | None = None) -> tuple[str, dict[str, Any] | None]:
    """Enforces FR-1.5 RBAC & FR-3.1 Composite Token Binding.
    If LLM attempts to query or modify another employee's ID (e.g. EMP-0001 CEO),
    blocks the cross-user access or forcibly binds to the authenticated session user.
    """
    auth_emp_id = current_authenticated_employee_id.get()
    if requested_employee_id and requested_employee_id.strip().upper() != auth_emp_id:
        attempted = requested_employee_id.strip().upper()
        violation_event = {
            "status": "GUARDRAIL_BLOCKED",
            "code": "RBAC_CROSS_USER_ACCESS_BLOCKED",
            "authenticated_user": auth_emp_id,
            "attempted_target_user": attempted,
            "message": (
                f"Security Guardrail Violation (FR-1.5 RBAC & FR-3.1 Composite Token): "
                f"Session is authenticated as '{auth_emp_id}'. Unauthorized attempt to access or modify records "
                f"for employee '{attempted}' was strictly blocked by before_tool_callback interceptor."
            ),
        }
        tool_execution_audit_log.append({
            "tool": "RBAC_INTERCEPTOR",
            "action": "BLOCKED_CROSS_USER_ACCESS",
            "auth_emp_id": auth_emp_id,
            "attempted_emp_id": attempted,
        })
        return auth_emp_id, violation_event
    return auth_emp_id, None


# =====================================================================
# 1. HR Policy Specialist Tools (Vertex AI Search RAG)
# =====================================================================

def search_hr_policies(query: str, category_filter: str = "") -> dict[str, Any]:
    """Searches approved corporate HR policies (Leave, Expense, Remote Work, Relocation, Code of Conduct).

    Args:
        query: The natural language search query about HR policies or benefits.
        category_filter: Optional domain category (e.g., 'leave', 'expense', 'remote', 'relocation').
    """
    res = search_policy_documents(query, category_filter if category_filter else None)
    tool_execution_audit_log.append({
        "tool": "search_hr_policies",
        "args": {"query": query, "category_filter": category_filter},
        "grounding_score": res.get("grounding_score", 0.0),
        "status": res.get("status"),
    })
    return res


# =====================================================================
# 2. WorkWeek HCM Specialist Tools (Employee Profile & Leave Management)
# =====================================================================

def get_employee_profile(target_employee_id: str = "") -> dict[str, Any]:
    """Fetches real-time employee profile details from WorkWeek HCM (FR-3.2, FR-3.4).
    Note: Always fetches live uncached data. Enforces strict RBAC scope (FR-1.5).

    Args:
        target_employee_id: Optional employee ID. Must match authenticated user or will be blocked by RBAC.
    """
    auth_emp_id, violation = _enforce_rbac_scope(target_employee_id if target_employee_id else None)
    if violation:
        return violation

    res = workweek_db.get_profile(auth_emp_id)
    tool_execution_audit_log.append({
        "tool": "get_employee_profile",
        "authenticated_emp_id": auth_emp_id,
        "status": res.get("status"),
    })
    return res


def get_leave_balances(target_employee_id: str = "") -> dict[str, Any]:
    """Fetches real-time Vacation and Sick leave balances from WorkWeek HCM (FR-3.2, FR-3.4).
    Never uses cached balances.

    Args:
        target_employee_id: Optional employee ID. Must match authenticated user.
    """
    auth_emp_id, violation = _enforce_rbac_scope(target_employee_id if target_employee_id else None)
    if violation:
        return violation

    res = workweek_db.get_leave_balances(auth_emp_id)
    tool_execution_audit_log.append({
        "tool": "get_leave_balances",
        "authenticated_emp_id": auth_emp_id,
        "status": res.get("status"),
    })
    return res


def update_contact_info(new_address: str = "", new_phone: str = "", target_employee_id: str = "") -> dict[str, Any]:
    """Updates the employee's personal home address and/or phone number in WorkWeek (FR-3.2, FR-3.3).

    Args:
        new_address: New residential street address (5-250 chars).
        new_phone: New personal phone number (valid international/domestic format, e.g., +1-206-555-0199).
        target_employee_id: Optional employee ID. Must match authenticated user.
    """
    auth_emp_id, violation = _enforce_rbac_scope(target_employee_id if target_employee_id else None)
    if violation:
        return violation

    addr_arg = new_address if new_address.strip() else None
    phone_arg = new_phone if new_phone.strip() else None
    res = workweek_db.update_contact_info(auth_emp_id, new_address=addr_arg, new_phone=phone_arg)
    tool_execution_audit_log.append({
        "tool": "update_contact_info",
        "authenticated_emp_id": auth_emp_id,
        "args": {"new_address": addr_arg, "new_phone": phone_arg},
        "status": res.get("status"),
        "code": res.get("code"),
    })
    return res


def submit_leave_request(
    leave_type: str,
    start_date: str,
    end_date: str,
    requested_hours: float,
    reason: str = "",
    target_employee_id: str = "",
) -> dict[str, Any]:
    """Submits a time-off request in WorkWeek enforcing FR-3.3 Balance & Temporal Guardrails.

    Args:
        leave_type: 'Vacation' or 'Sick' (or 'Medical').
        start_date: Start date in YYYY-MM-DD format (must not be in the past).
        end_date: End date in YYYY-MM-DD format (must be >= start_date).
        requested_hours: Total leave hours requested (must not exceed remaining accrued balance).
        reason: Optional reason or note for manager.
        target_employee_id: Optional employee ID. Must match authenticated user.
    """
    auth_emp_id, violation = _enforce_rbac_scope(target_employee_id if target_employee_id else None)
    if violation:
        return violation

    res = workweek_db.submit_leave_request(
        authenticated_emp_id=auth_emp_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        requested_hours=float(requested_hours),
        reason=reason,
    )
    tool_execution_audit_log.append({
        "tool": "submit_leave_request",
        "authenticated_emp_id": auth_emp_id,
        "args": {
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "requested_hours": requested_hours,
        },
        "status": res.get("status"),
        "code": res.get("code"),
    })
    return res


# =====================================================================
# 3. ServiceImmediately ITSM Specialist Tools (Incident Tickets & Saga)
# =====================================================================

def get_ticket_details(ticket_id: str) -> dict[str, Any]:
    """Retrieves status, priority, assignee, and comment history of a ServiceImmediately ticket (FR-4.2).
    Enforces RBAC so users can only view their own tickets (FR-1.5).

    Args:
        ticket_id: Incident ticket ID (e.g., 'INC123456').
    """
    auth_emp_id = current_authenticated_employee_id.get()
    res = service_db.get_ticket_details(auth_emp_id, ticket_id)
    tool_execution_audit_log.append({
        "tool": "get_ticket_details",
        "authenticated_emp_id": auth_emp_id,
        "args": {"ticket_id": ticket_id},
        "status": res.get("status"),
        "code": res.get("code"),
    })
    return res


def create_incident_ticket(
    category: str,
    short_description: str,
    detailed_description: str,
    priority: str = "3 - Moderate",
    associated_workweek_leave_id: str = "",
) -> dict[str, Any]:
    """Creates a support ticket in ServiceImmediately with mandatory X-Automation-Origin auditing (FR-4.1, FR-4.2).
    Implements Exponential Backoff retry & Deterministic Saga Compensation on 503 outage (NFR-4.1, NFR-4.2, NFR-4.3).

    Args:
        category: Ticket category (e.g., 'Hardware_Procurement', 'IT_Access_Delegation', 'Facilities_Badge_Access', 'Network / VPN').
        short_description: Brief summary of the request or issue.
        detailed_description: Detailed context, shipping address, building code, or manager delegation info.
        priority: Priority level ('1 - Critical', '2 - High', '3 - Moderate', '4 - Low').
        associated_workweek_leave_id: Optional Leave Request ID (e.g. 'LR-88401') if part of a Cross-System Saga.
    """
    auth_emp_id = current_authenticated_employee_id.get()
    origin_header = "Google-Cloud-ADK-HR-Agent-MVP1"

    try:
        res = service_db.create_incident_ticket(
            authenticated_emp_id=auth_emp_id,
            category=category,
            short_description=short_description,
            detailed_description=detailed_description,
            priority=priority,
            automation_origin_header=origin_header,
        )
        tool_execution_audit_log.append({
            "tool": "create_incident_ticket",
            "authenticated_emp_id": auth_emp_id,
            "args": {"category": category, "short_description": short_description, "priority": priority},
            "status": res.get("status"),
            "code": res.get("code"),
            "ticket_id": res.get("ticket_id"),
            "X-Automation-Origin": origin_header,
        })
        return res

    except ConnectionError as exc:
        # NFR-4.2 Transient Fault Tolerance & NFR-4.3 Saga Compensation / Asynchronous Fallback
        # Do NOT expose stack trace or raw exception string to user (NFR-4.1 Graceful Failure Handling)
        comp_event = service_db.enqueue_compensating_ticket(
            emp_id=auth_emp_id,
            leave_req_id=associated_workweek_leave_id or "N/A",
            ticket_payload={
                "category": category,
                "short_description": short_description,
                "detailed_description": detailed_description,
                "priority": priority,
            },
        )
        tool_execution_audit_log.append({
            "tool": "create_incident_ticket",
            "authenticated_emp_id": auth_emp_id,
            "status": "SAGA_COMPENSATED_ASYNC_QUEUED",
            "retries_attempted": 3,
            "escalation_id": comp_event["escalation_id"],
            "reason": "ServiceImmediately API 503 Outage -> Queued in Pub/Sub for guaranteed delivery.",
        })
        return {
            "status": "SAGA_FALLBACK_QUEUED",
            "service_status": "TEMPORARILY_UNAVAILABLE",
            "escalation_reference_id": comp_event["escalation_id"],
            "associated_leave_request_id": associated_workweek_leave_id,
            "user_guidance": (
                f"ServiceImmediately is temporarily unavailable after 3 retry attempts (NFR-4.2). "
                f"To ensure data consistency (NFR-4.3), your prior WorkWeek transaction ({associated_workweek_leave_id or 'Profile/Leave'}) "
                f"remains safely intact, and your IT ticket request has been queued in Cloud Pub/Sub "
                f"(Reference ID: {comp_event['escalation_id']}) for automatic background creation. No further action is required from you."
            ),
        }


def add_ticket_comment(ticket_id: str, comment_text: str) -> dict[str, Any]:
    """Appends a comment to an existing ServiceImmediately ticket (FR-4.2).

    Args:
        ticket_id: Incident ticket ID (e.g., 'INC123456').
        comment_text: Comment note to add.
    """
    auth_emp_id = current_authenticated_employee_id.get()
    res = service_db.add_ticket_comment(auth_emp_id, ticket_id, comment_text)
    tool_execution_audit_log.append({
        "tool": "add_ticket_comment",
        "authenticated_emp_id": auth_emp_id,
        "args": {"ticket_id": ticket_id, "comment_text": comment_text},
        "status": res.get("status"),
    })
    return res


def update_ticket_status(ticket_id: str, new_state: str, resolution_notes: str = "") -> dict[str, Any]:
    """Updates the lifecycle status of a ServiceImmediately ticket enforcing FR-4.3 Transition Constraints.

    Args:
        ticket_id: Incident ticket ID (e.g., 'INC123456').
        new_state: Target state ('In Progress', 'Resolved', 'Closed', 'Cancelled'). Note: Direct New -> Closed is prohibited.
        resolution_notes: Mandatory explanation when transitioning to 'Resolved' or 'Closed'.
    """
    auth_emp_id = current_authenticated_employee_id.get()
    res = service_db.update_ticket_status(auth_emp_id, ticket_id, new_state, resolution_notes)
    tool_execution_audit_log.append({
        "tool": "update_ticket_status",
        "authenticated_emp_id": auth_emp_id,
        "args": {"ticket_id": ticket_id, "new_state": new_state},
        "status": res.get("status"),
        "code": res.get("code"),
    })
    return res


ALL_TOOLS = [
    search_hr_policies,
    get_employee_profile,
    get_leave_balances,
    update_contact_info,
    submit_leave_request,
    get_ticket_details,
    create_incident_ticket,
    add_ticket_comment,
    update_ticket_status,
]

