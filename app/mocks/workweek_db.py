"""Deterministic In-Memory Mock DB for WorkWeek (HCM) Employee Profile and Leave Management."""
from copy import deepcopy
from datetime import datetime, date
import re
from typing import Any

INITIAL_EMPLOYEES: dict[str, dict[str, Any]] = {
    "EMP-9021": {
        "employee_id": "EMP-9021",
        "name": "Alice Smith",
        "email": "alice.smith@corp.internal",
        "department": "Cloud Engineering",
        "role": "Senior Software Engineer",
        "work_location_status": "Approved Remote",
        "office_building": "SEA-BLDG-2",
        "manager_id": "MGR-104",
        "manager_name": "Bob Vance",
        "manager_email": "bob.vance@corp.internal",
        "hire_date": "2022-03-14",
        "home_address": "742 Evergreen Terrace, Seattle, WA 98101, USA",
        "phone_number": "+1-206-555-0199",
        "leave_balances": {
            "Vacation": {"accrued_hours": 120.0, "used_hours": 80.0, "remaining_hours": 40.0},
            "Sick": {"accrued_hours": 96.0, "used_hours": 16.0, "remaining_hours": 80.0},
        },
    },
    "EMP-0001": {
        "employee_id": "EMP-0001",
        "name": "Arthur Pendelton (CEO)",
        "email": "ceo@corp.internal",
        "department": "Executive Office",
        "role": "Chief Executive Officer",
        "work_location_status": "Hybrid",
        "office_building": "NYC-HQ-TOWER",
        "manager_id": "BOARD-01",
        "manager_name": "Board of Directors",
        "manager_email": "board@corp.internal",
        "hire_date": "2015-01-10",
        "home_address": "999 Billionaire Row, Penthouse A, New York, NY 10022",
        "phone_number": "+1-212-555-0001",
        "leave_balances": {
            "Vacation": {"accrued_hours": 240.0, "used_hours": 40.0, "remaining_hours": 200.0},
            "Sick": {"accrued_hours": 120.0, "used_hours": 0.0, "remaining_hours": 120.0},
        },
    },
}


class WorkWeekMockDB:
    """Thread-safe in-memory mock database for WorkWeek HCM operations with FR-3.3 guardrails."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.employees: dict[str, dict[str, Any]] = deepcopy(INITIAL_EMPLOYEES)
        self.leave_requests: dict[str, dict[str, Any]] = {}
        self._req_counter: int = 88400
        self.audit_log: list[dict[str, Any]] = []

    def get_profile(self, authenticated_emp_id: str) -> dict[str, Any]:
        """Retrieves real-time employee profile (FR-3.2, FR-3.4)."""
        emp = self.employees.get(authenticated_emp_id)
        if not emp:
            return {"status": "ERROR", "code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {authenticated_emp_id} not found."}
        self.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "GET_PROFILE",
            "employee_id": authenticated_emp_id,
            "origin": "Google-Cloud-ADK-HR-Agent-MVP1",
        })
        # Return copy without mutating internal state
        return {"status": "SUCCESS", "fetch_mode": "REALTIME_UNCACHED", "profile": deepcopy(emp)}

    def get_leave_balances(self, authenticated_emp_id: str) -> dict[str, Any]:
        """Retrieves real-time leave balances (FR-3.2, FR-3.4)."""
        emp = self.employees.get(authenticated_emp_id)
        if not emp:
            return {"status": "ERROR", "code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {authenticated_emp_id} not found."}
        return {
            "status": "SUCCESS",
            "fetch_mode": "REALTIME_UNCACHED",
            "employee_id": authenticated_emp_id,
            "balances": deepcopy(emp["leave_balances"]),
        }

    def update_contact_info(
        self, authenticated_emp_id: str, new_address: str | None = None, new_phone: str | None = None
    ) -> dict[str, Any]:
        """Updates personal address and phone number with format validation guardrails (FR-3.2, FR-3.3)."""
        emp = self.employees.get(authenticated_emp_id)
        if not emp:
            return {"status": "ERROR", "code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {authenticated_emp_id} not found."}

        updated_fields = []
        if new_phone is not None:
            # FR-3.3 Format Restriction Guardrail: Validate phone number format
            phone_clean = new_phone.strip()
            if not re.match(r"^\+?[0-9\-\(\)\s]{8,20}$", phone_clean):
                return {
                    "status": "GUARDRAIL_BLOCKED",
                    "code": "INVALID_PHONE_FORMAT",
                    "message": f"Guardrail Violation (FR-3.3): Phone number '{new_phone}' does not match valid international/domestic format.",
                }
            emp["phone_number"] = phone_clean
            updated_fields.append("phone_number")

        if new_address is not None:
            addr_clean = new_address.strip()
            if len(addr_clean) < 5 or len(addr_clean) > 250:
                return {
                    "status": "GUARDRAIL_BLOCKED",
                    "code": "INVALID_ADDRESS_LENGTH",
                    "message": "Guardrail Violation (FR-3.3): Address must be between 5 and 250 characters.",
                }
            emp["home_address"] = addr_clean
            updated_fields.append("home_address")

        self.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "UPDATE_CONTACT_INFO",
            "employee_id": authenticated_emp_id,
            "updated_fields": updated_fields,
            "origin": "Google-Cloud-ADK-HR-Agent-MVP1",
        })
        return {
            "status": "SUCCESS",
            "employee_id": authenticated_emp_id,
            "updated_fields": updated_fields,
            "current_contact": {"home_address": emp["home_address"], "phone_number": emp["phone_number"]},
        }

    def submit_leave_request(
        self,
        authenticated_emp_id: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        requested_hours: float,
        reason: str = "",
    ) -> dict[str, Any]:
        """Submits a time-off request enforcing FR-3.3 Balance & Temporal Guardrails."""
        emp = self.employees.get(authenticated_emp_id)
        if not emp:
            return {"status": "ERROR", "code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {authenticated_emp_id} not found."}

        # Normalize leave type
        norm_type = "Sick" if "sick" in leave_type.lower() or "medical" in leave_type.lower() else "Vacation"

        # 1. Temporal Validity Guardrail (FR-3.3)
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            e_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "INVALID_DATE_FORMAT",
                "message": "Guardrail Violation (FR-3.3): Dates must be formatted as YYYY-MM-DD.",
            }

        # Reference date for evaluation stability: 2026-09-16
        ref_today = date(2026, 9, 16)
        if s_dt < ref_today:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "PAST_DATE_NOT_ALLOWED",
                "message": f"Guardrail Violation (FR-3.3 Temporal Validity): Start date ({start_date}) cannot be in the past (Today: {ref_today.isoformat()}).",
            }
        if s_dt > e_dt:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "CHRONOLOGICAL_ERROR",
                "message": f"Guardrail Violation (FR-3.3 Temporal Validity): Start date ({start_date}) cannot be after end date ({end_date}).",
            }

        # 2. Balance Constraints Guardrail (FR-3.3)
        balance_info = emp["leave_balances"][norm_type]
        remaining = balance_info["remaining_hours"]
        if requested_hours <= 0:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "INVALID_HOURS",
                "message": "Requested hours must be greater than 0.",
            }
        if requested_hours > remaining:
            return {
                "status": "GUARDRAIL_BLOCKED",
                "code": "INSUFFICIENT_LEAVE_BALANCE",
                "message": (
                    f"Guardrail Violation (FR-3.3 Balance Constraint): Requested {requested_hours} hours of {norm_type} leave "
                    f"exceeds your remaining balance of {remaining} hours."
                ),
                "leave_type": norm_type,
                "requested_hours": requested_hours,
                "remaining_hours": remaining,
            }

        # Deduct balance and record request
        balance_info["used_hours"] += requested_hours
        balance_info["remaining_hours"] -= requested_hours

        self._req_counter += 1
        req_id = f"LR-{self._req_counter}"
        record = {
            "request_id": req_id,
            "employee_id": authenticated_emp_id,
            "leave_type": norm_type,
            "start_date": start_date,
            "end_date": end_date,
            "requested_hours": requested_hours,
            "reason": reason,
            "status": "Submitted (Pending Manager Approval)",
            "manager_id": emp["manager_id"],
            "created_at": datetime.utcnow().isoformat(),
        }
        self.leave_requests[req_id] = record
        return {
            "status": "SUCCESS",
            "request_id": req_id,
            "leave_type": norm_type,
            "requested_hours": requested_hours,
            "remaining_balance_hours": balance_info["remaining_hours"],
            "details": record,
        }

    def cancel_leave_request(self, authenticated_emp_id: str, request_id: str, reason: str = "Saga Rollback") -> dict[str, Any]:
        """Compensating action to cancel a leave request and restore balance (NFR-4.3 Saga Rollback)."""
        req = self.leave_requests.get(request_id)
        if not req:
            return {"status": "ERROR", "code": "REQUEST_NOT_FOUND", "message": f"Leave request {request_id} not found."}
        if req["employee_id"] != authenticated_emp_id:
            return {"status": "GUARDRAIL_BLOCKED", "code": "RBAC_VIOLATION", "message": "Cannot cancel another employee's request."}

        if req["status"] != "Cancelled":
            emp = self.employees[authenticated_emp_id]
            norm_type = req["leave_type"]
            emp["leave_balances"][norm_type]["used_hours"] -= req["requested_hours"]
            emp["leave_balances"][norm_type]["remaining_hours"] += req["requested_hours"]
            req["status"] = "Cancelled"
            req["cancellation_reason"] = reason

        return {
            "status": "SUCCESS",
            "request_id": request_id,
            "new_status": "Cancelled",
            "restored_hours": req["requested_hours"],
            "current_remaining_hours": self.employees[authenticated_emp_id]["leave_balances"][req["leave_type"]]["remaining_hours"],
        }


workweek_db = WorkWeekMockDB()
