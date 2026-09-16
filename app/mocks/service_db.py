"""Deterministic In-Memory Mock DB for ServiceImmediately (ITSM/HRSD) with FR-4.1, FR-4.3 & NFR-4.3 Fault Injection."""
from copy import deepcopy
from datetime import datetime
from typing import Any

INITIAL_INCIDENTS: dict[str, dict[str, Any]] = {
    "INC123456": {
        "ticket_id": "INC123456",
        "caller_employee_id": "EMP-9021",
        "category": "Network / VPN",
        "short_description": "VPN connection keeps dropping intermittently",
        "detailed_description": "Employee reports corporate VPN disconnects every 20 minutes while working from home.",
        "priority": "3 - Moderate",
        "state": "In Progress",
        "assignee": "IT-NetOps-Support",
        "automation_origin": "Manual-Portal-Entry",
        "created_at": "2026-09-15T14:20:00Z",
        "comments_timeline": [
            {"timestamp": "2026-09-15T14:25:00Z", "author": "IT-NetOps-Support", "comment": "Assigned to VPN gateway team for packet inspection."},
            {"timestamp": "2026-09-16T09:10:00Z", "author": "IT-NetOps-Support", "comment": "Recommended updating AnyConnect client to v5.1."},
        ],
    },
    "INC999000": {
        "ticket_id": "INC999000",
        "caller_employee_id": "EMP-0001",
        "category": "Executive_Security",
        "short_description": "Confidential Executive Laptop Replacement",
        "detailed_description": "Private executive hardware refresh for CEO.",
        "priority": "1 - Critical",
        "state": "In Progress",
        "assignee": "VIP-Exec-Support",
        "automation_origin": "Manual-Portal-Entry",
        "created_at": "2026-09-16T08:00:00Z",
        "comments_timeline": [],
    },
}

# Valid lifecycle state transition matrix (FR-4.3 Transition Constraints)
VALID_TRANSITIONS: dict[str, list[str]] = {
    "New": ["In Progress", "Cancelled"],  # Direct New -> Closed or New -> Resolved is strictly blocked!
    "In Progress": ["Resolved", "Cancelled", "On Hold"],
    "On Hold": ["In Progress", "Resolved", "Cancelled"],
    "Resolved": ["Closed", "In Progress"],
    "Closed": [],
    "Cancelled": [],
}


class ServiceImmediatelyMockDB:
    """In-memory mock for ServiceImmediately ITSM API supporting fault injection and lifecycle guardrails."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.incidents: dict[str, dict[str, Any]] = deepcopy(INITIAL_INCIDENTS)
        self._ticket_counter: int = 123457
        self.simulate_outage: bool = False
        self.pubsub_compensation_queue: list[dict[str, Any]] = []
        self.audit_headers_log: list[dict[str, str]] = []

    def get_ticket_details(self, authenticated_emp_id: str, ticket_id: str) -> dict[str, Any]:
        """Retrieves ticket details enforcing RBAC data isolation (FR-1.5, FR-4.2)."""
        t_clean = ticket_id.strip().upper()
        ticket = self.incidents.get(t_clean)
        if not ticket:
            return {"status": "ERROR", "code": "TICKET_NOT_FOUND", "message": f"Incident ticket {t_clean} was not found."}

        # FR-1.5 Strict RBAC: Employee can only view their own tickets
        if ticket["caller_employee_id"] != authenticated_emp_id:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "RBAC_ACCESS_DENIED",
                "message": (
                    f"Security Guardrail Violation (FR-1.5 RBAC): You are authenticated as {authenticated_emp_id} "
                    f"and are not authorized to view ticket {t_clean} belonging to another employee."
                ),
            }
        return {"status": "SUCCESS", "ticket": deepcopy(ticket)}

    def create_incident_ticket(
        self,
        authenticated_emp_id: str,
        category: str,
        short_description: str,
        detailed_description: str,
        priority: str = "3 - Moderate",
        automation_origin_header: str = "Google-Cloud-ADK-HR-Agent-MVP1",
    ) -> dict[str, Any]:
        """Creates a new incident ticket with FR-4.1 origin auditing, FR-4.3 deduplication & priority checks, and NFR-4.2/4.3 outage simulation."""
        # Check Fault Injection trigger for NFR-4.2 / NFR-4.3 Saga Testing
        if (
            self.simulate_outage
            or "[SIMULATE_SI_OUTAGE]" in short_description
            or "[SIMULATE_SI_OUTAGE]" in detailed_description
        ):
            raise ConnectionError("HTTP 503 Service Unavailable: ServiceImmediately ITSM Backend Endpoint is down.")

        # FR-4.1 Verify Automation Origin Header
        if not automation_origin_header or "HR-Agent" not in automation_origin_header:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "MISSING_AUTOMATION_ORIGIN",
                "message": "Guardrail Violation (FR-1.2 / FR-4.1): Request rejected due to missing verified X-Automation-Origin header.",
            }

        # FR-4.3 Guardrail 1: Deduplication Mitigation
        for existing in self.incidents.values():
            if (
                existing["caller_employee_id"] == authenticated_emp_id
                and existing["category"].lower() == category.lower()
                and existing["short_description"].strip().lower() == short_description.strip().lower()
                and existing["state"] not in ["Closed", "Cancelled"]
            ):
                return {
                    "status": "GUARDRAIL_BLOCKED",
                    "code": "DUPLICATE_TICKET_DETECTED",
                    "message": (
                        f"Guardrail Violation (FR-4.3 Deduplication): An identical active ticket ({existing['ticket_id']}) "
                        f"already exists for category '{category}'. Duplicate creation prevented."
                    ),
                    "existing_ticket_id": existing["ticket_id"],
                }

        # FR-4.3 Guardrail 2: Priority Verification
        verified_priority = priority
        priority_warning = None
        if "1 - Critical" in priority:
            # Verify critical criteria (e.g. production outage, security breach)
            crit_keywords = ["outage", "breach", "all employees", "production down", "emergency"]
            if not any(kw in detailed_description.lower() or kw in short_description.lower() for kw in crit_keywords):
                verified_priority = "3 - Moderate"
                priority_warning = (
                    "FR-4.3 Priority Verification Guardrail: Requested '1 - Critical' priority was automatically adjusted "
                    "to '3 - Moderate' because description does not match enterprise critical outage criteria."
                )

        self._ticket_counter += 1
        new_id = f"INC{self._ticket_counter}"
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        work_note = (
            f"[AUTOMATED ACTION - AUDIT STAMP] Created via {automation_origin_header} "
            f"acting on behalf of verified Employee {authenticated_emp_id}."
        )

        record = {
            "ticket_id": new_id,
            "caller_employee_id": authenticated_emp_id,
            "category": category,
            "short_description": short_description,
            "detailed_description": detailed_description,
            "priority": verified_priority,
            "state": "New",
            "assignee": "IT-Tier1-Triage",
            "automation_origin": automation_origin_header,
            "created_at": now_str,
            "comments_timeline": [
                {"timestamp": now_str, "author": "SYSTEM_AUDIT", "comment": work_note}
            ],
        }
        self.incidents[new_id] = record
        self.audit_headers_log.append({
            "ticket_id": new_id,
            "X-Automation-Origin": automation_origin_header,
            "X-Acted-On-Behalf-Of": authenticated_emp_id,
        })

        resp: dict[str, Any] = {
            "status": "SUCCESS",
            "ticket_id": new_id,
            "state": "New",
            "priority": verified_priority,
            "audit_origin_verified": True,
            "ticket_details": record,
        }
        if priority_warning:
            resp["guardrail_notice"] = priority_warning
        return resp

    def add_ticket_comment(self, authenticated_emp_id: str, ticket_id: str, comment_text: str) -> dict[str, Any]:
        """Appends a comment to an existing ticket (FR-4.2)."""
        t_clean = ticket_id.strip().upper()
        ticket = self.incidents.get(t_clean)
        if not ticket:
            return {"status": "ERROR", "code": "TICKET_NOT_FOUND", "message": f"Ticket {t_clean} not found."}
        if ticket["caller_employee_id"] != authenticated_emp_id:
            return {"status": "GUARDRAIL_BLOCKED", "code": "RBAC_ACCESS_DENIED", "message": "Cannot comment on another user's ticket."}

        entry = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author": f"{authenticated_emp_id} (via HR-Agent-MVP1)",
            "comment": comment_text,
        }
        ticket["comments_timeline"].append(entry)
        return {"status": "SUCCESS", "ticket_id": t_clean, "comment_added": entry}

    def update_ticket_status(
        self, authenticated_emp_id: str, ticket_id: str, new_state: str, resolution_notes: str = ""
    ) -> dict[str, Any]:
        """Updates ticket status enforcing FR-4.3 Lifecycle Transition Matrix."""
        t_clean = ticket_id.strip().upper()
        ticket = self.incidents.get(t_clean)
        if not ticket:
            return {"status": "ERROR", "code": "TICKET_NOT_FOUND", "message": f"Ticket {t_clean} not found."}
        if ticket["caller_employee_id"] != authenticated_emp_id:
            return {"status": "GUARDRAIL_BLOCKED", "code": "RBAC_ACCESS_DENIED", "message": "Cannot modify another user's ticket."}

        current_state = ticket["state"]
        allowed_next = VALID_TRANSITIONS.get(current_state, [])

        if new_state not in allowed_next:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "INVALID_STATE_TRANSITION",
                "message": (
                    f"Guardrail Violation (FR-4.3 Lifecycle Constraint): Invalid state transition from '{current_state}' "
                    f"to '{new_state}'. Allowed transitions from '{current_state}' are: {allowed_next}. "
                    "(Direct transition from New to Closed is prohibited)."
                ),
                "current_state": current_state,
                "attempted_state": new_state,
            }

        if new_state in ["Resolved", "Closed"] and len(resolution_notes.strip()) < 5:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "MISSING_RESOLUTION_NOTES",
                "message": f"Guardrail Violation (FR-4.3): Transitioning to '{new_state}' requires resolution notes (min 5 chars).",
            }

        prev_state = ticket["state"]
        ticket["state"] = new_state
        ticket["comments_timeline"].append({
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author": f"{authenticated_emp_id} (via HR-Agent-MVP1)",
            "comment": f"State changed from {prev_state} to {new_state}. Notes: {resolution_notes}",
        })
        return {
            "status": "SUCCESS",
            "ticket_id": t_clean,
            "previous_state": prev_state,
            "current_state": new_state,
        }

    def enqueue_compensating_ticket(self, emp_id: str, leave_req_id: str, ticket_payload: dict[str, Any]) -> dict[str, Any]:
        """Enqueues a failed cross-system ticket request to Cloud Pub/Sub fallback queue (NFR-4.3 Saga Compensation)."""
        esc_id = f"ESC-{len(self.pubsub_compensation_queue) + 5521}"
        event = {
            "escalation_id": esc_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "employee_id": emp_id,
            "associated_workweek_leave_id": leave_req_id,
            "failed_service": "ServiceImmediately_API",
            "pending_ticket_payload": ticket_payload,
            "status": "QUEUED_IN_PUBSUB_FOR_AUTO_RETRY",
        }
        self.pubsub_compensation_queue.append(event)
        return event


service_db = ServiceImmediatelyMockDB()
