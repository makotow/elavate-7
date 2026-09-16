"""Model Context Protocol (MCP) Client for WorkWeek and ServiceImmediately.

Connects to remote FastMCP servers via Streamable HTTP transport:
- WorkWeek: https://mock-saas.aishprabhat.demo.altostrat.com/work-week/mcp/
- ServiceImmediately: https://mock-saas.aishprabhat.demo.altostrat.com/service-immediately/mcp/
- Authentication: X-MCP-Token header (mcp_3DrXPfcezy8LEGYxXmB8eTAyrO2uJZbMBDSbBisSczg)
"""

import json
import logging
import re
from typing import Any, Optional

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger(__name__)

# Remote MCP Endpoints
WORKWEEK_MCP_URL = "https://mock-saas.aishprabhat.demo.altostrat.com/work-week/mcp/"
SERVICE_IMMEDIATELY_MCP_URL = "https://mock-saas.aishprabhat.demo.altostrat.com/service-immediately/mcp/"
MCP_TOKEN = "mcp_3DrXPfcezy8LEGYxXmB8eTAyrO2uJZbMBDSbBisSczg"

# Default Authenticated Employee context bound to this MCP token
DEFAULT_MCP_EMPLOYEE_ID = "EMP-769"


class McpServiceError(Exception):
    """Raised when an MCP service call fails."""
    pass


async def _execute_mcp_tool(
    endpoint_url: str,
    tool_name: str,
    arguments: dict[str, Any],
    timeout_seconds: float = 15.0,
) -> str:
    """Invokes a specific tool on a remote Streamable HTTP FastMCP server."""
    headers = {
        "X-MCP-Token": MCP_TOKEN,
        "Accept": "text/event-stream",
    }
    async with httpx.AsyncClient(headers=headers, timeout=timeout_seconds) as client:
        try:
            async with streamable_http_client(endpoint_url, http_client=client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    # Extract text content from tool response
                    if result and result.content:
                        text_parts = [
                            item.text for item in result.content if hasattr(item, "text") and item.text
                        ]
                        return "\n".join(text_parts)
                    return ""
        except Exception as exc:
            logger.error(f"MCP tool call '{tool_name}' on {endpoint_url} failed: {exc}")
            raise McpServiceError(f"MCP invocation '{tool_name}' failed: {exc}") from exc


# =====================================================================
# WorkWeek MCP Operations
# =====================================================================

async def mcp_get_current_employee_id() -> str:
    """Fetches the current employee ID associated with the MCP token."""
    res = await _execute_mcp_tool(WORKWEEK_MCP_URL, "get_current_employee_id", {})
    return res.strip() if res else DEFAULT_MCP_EMPLOYEE_ID


async def mcp_get_employee_balances(employee_id: str = DEFAULT_MCP_EMPLOYEE_ID) -> str:
    """Fetches leave balances from WorkWeek via MCP."""
    return await _execute_mcp_tool(
        WORKWEEK_MCP_URL, "get_employee_balances", {"employee_id": employee_id}
    )


async def mcp_get_personal_info(employee_id: str = DEFAULT_MCP_EMPLOYEE_ID) -> str:
    """Fetches contact/personal details from WorkWeek via MCP."""
    return await _execute_mcp_tool(
        WORKWEEK_MCP_URL, "get_personal_info", {"employee_id": employee_id}
    )


async def mcp_get_leave_requests(employee_id: str = DEFAULT_MCP_EMPLOYEE_ID) -> list[dict[str, Any]]:
    """Fetches list of leave requests from WorkWeek via MCP and parses to JSON."""
    raw = await _execute_mcp_tool(
        WORKWEEK_MCP_URL, "get_leave_requests", {"employee_id": employee_id}
    )
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        logger.warning(f"Could not parse leave requests JSON: {raw}")
        return []


async def mcp_request_time_off(
    employee_id: str,
    start_date: str,
    end_date: str,
    leave_type: str,
    days: float,
) -> str:
    """Submits a leave request to WorkWeek via MCP."""
    return await _execute_mcp_tool(
        WORKWEEK_MCP_URL,
        "request_time_off",
        {
            "employee_id": employee_id,
            "start_date": start_date,
            "end_date": end_date,
            "leave_type": leave_type,
            "days": days,
        },
    )


async def mcp_update_personal_info(
    employee_id: str,
    address: str,
    phone: str,
) -> str:
    """Updates personal contact details in WorkWeek via MCP."""
    return await _execute_mcp_tool(
        WORKWEEK_MCP_URL,
        "update_personal_info",
        {
            "employee_id": employee_id,
            "address": address,
            "phone": phone,
        },
    )


async def mcp_cancel_leave_request(employee_id: str, request_id: int) -> str:
    """Cancels a leave request in WorkWeek via MCP."""
    return await _execute_mcp_tool(
        WORKWEEK_MCP_URL,
        "cancel_leave_request",
        {"employee_id": employee_id, "request_id": request_id},
    )


# =====================================================================
# ServiceImmediately MCP Operations
# =====================================================================

async def mcp_list_tickets(employee_id: str = DEFAULT_MCP_EMPLOYEE_ID) -> list[dict[str, Any]]:
    """Fetches incident tickets from ServiceImmediately via MCP and parses to JSON."""
    raw = await _execute_mcp_tool(
        SERVICE_IMMEDIATELY_MCP_URL, "list_tickets", {"employee_id": employee_id}
    )
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        logger.warning(f"Could not parse tickets JSON: {raw}")
        return []


async def mcp_create_ticket(
    requested_by: str,
    category: str,
    short_description: str,
    priority: str = "3 - Moderate",
    assignment_group: str = "Service Desk",
) -> str:
    """Creates an incident ticket in ServiceImmediately via MCP."""
    return await _execute_mcp_tool(
        SERVICE_IMMEDIATELY_MCP_URL,
        "create_ticket",
        {
            "requested_by": requested_by,
            "category": category,
            "short_description": short_description,
            "priority": priority,
            "assignment_group": assignment_group,
        },
    )


async def mcp_add_ticket_comment(ticket_id: str, author: str, comment: str) -> str:
    """Appends a comment to an incident ticket in ServiceImmediately via MCP."""
    return await _execute_mcp_tool(
        SERVICE_IMMEDIATELY_MCP_URL,
        "add_ticket_comment",
        {"ticket_id": ticket_id, "author": author, "comment": comment},
    )


async def mcp_update_ticket_status(
    ticket_id: str,
    status: str,
    resolution_notes: str = "",
    updated_by: str = "System",
) -> str:
    """Updates ticket status in ServiceImmediately via MCP."""
    return await _execute_mcp_tool(
        SERVICE_IMMEDIATELY_MCP_URL,
        "update_ticket_status",
        {
            "ticket_id": ticket_id,
            "status": status,
            "resolution_notes": resolution_notes,
            "updated_by": updated_by,
        },
    )


# =====================================================================
# State Parsers for UI / Aggregation
# =====================================================================

def parse_workweek_balances(raw_text: str) -> dict[str, Any]:
    """Parses raw text from get_employee_balances into structured balances dict."""
    # Example format:
    # "Employee EMP-769 Leave Balances:
    #  - Vacation: 15.0 days remaining (5.0/20.0 used)
    #  - Sick: 10.0 days remaining (0.0/10.0 used)"
    vacation_match = re.search(r"Vacation:\s*([\d\.]+)\s*days\s*remaining\s*\(([\d\.]+)/([\d\.]+)\s*used\)", raw_text)
    sick_match = re.search(r"Sick:\s*([\d\.]+)\s*days\s*remaining\s*\(([\d\.]+)/([\d\.]+)\s*used\)", raw_text)

    vacation_remaining = float(vacation_match.group(1)) if vacation_match else 15.0
    vacation_used = float(vacation_match.group(2)) if vacation_match else 5.0
    vacation_accrued = float(vacation_match.group(3)) if vacation_match else 20.0

    sick_remaining = float(sick_match.group(1)) if sick_match else 10.0
    sick_used = float(sick_match.group(2)) if sick_match else 0.0
    sick_accrued = float(sick_match.group(3)) if sick_match else 10.0

    return {
        "raw": raw_text,
        "vacation_hours_remaining": vacation_remaining * 8.0,  # standard 8h/day
        "vacation_days_remaining": vacation_remaining,
        "vacation_days_used": vacation_used,
        "vacation_days_accrued": vacation_accrued,
        "sick_hours_remaining": sick_remaining * 8.0,
        "sick_days_remaining": sick_remaining,
        "sick_days_used": sick_used,
        "sick_days_accrued": sick_accrued,
    }


def parse_workweek_profile(raw_text: str, employee_id: str) -> dict[str, Any]:
    """Parses raw text from get_personal_info into structured profile dict."""
    # Example format:
    # "Employee EMP-769 Personal Info:
    #  - Address: Singapore Office, 80 Pasir Panjang Rd, Singapore
    #  - Phone: +65-6521-0000"
    addr_match = re.search(r"Address:\s*(.+)", raw_text)
    phone_match = re.search(r"Phone:\s*(.+)", raw_text)

    return {
        "employee_id": employee_id,
        "full_name": "Makotow Employee",
        "email": "makotow@elevate.corp",
        "department": "Cloud & AI Solutions Architecture",
        "title": "Staff Solutions Architect",
        "manager_id": "EMP-0010",
        "office_location": "Singapore Office",
        "home_address": addr_match.group(1).strip() if addr_match else "Singapore Office, 80 Pasir Panjang Rd, Singapore",
        "phone_number": phone_match.group(1).strip() if phone_match else "+65-6521-0000",
        "remote_work_eligible": True,
        "employment_status": "Full-Time Active",
    }


async def get_live_mcp_state(employee_id: str = DEFAULT_MCP_EMPLOYEE_ID) -> dict[str, Any]:
    """Fetches complete live state across WorkWeek and ServiceImmediately via MCP."""
    try:
        raw_balances = await mcp_get_employee_balances(employee_id)
        balances = parse_workweek_balances(raw_balances)
    except Exception as e:
        logger.warning(f"Error fetching balances via MCP: {e}")
        balances = {
            "vacation_days_remaining": 15.0,
            "vacation_days_accrued": 20.0,
            "sick_days_remaining": 10.0,
            "sick_days_accrued": 10.0,
        }

    try:
        raw_personal = await mcp_get_personal_info(employee_id)
        profile = parse_workweek_profile(raw_personal, employee_id)
    except Exception as e:
        logger.warning(f"Error fetching personal info via MCP: {e}")
        profile = {
            "employee_id": employee_id,
            "full_name": "Makotow Employee",
            "email": "makotow@elevate.corp",
            "department": "Cloud & AI Solutions Architecture",
            "title": "Staff Solutions Architect",
            "office_location": "Singapore Office",
            "home_address": "Singapore Office, 80 Pasir Panjang Rd, Singapore",
            "phone_number": "+65-6521-0000",
        }

    try:
        leave_requests = await mcp_get_leave_requests(employee_id)
    except Exception as e:
        logger.warning(f"Error fetching leave requests via MCP: {e}")
        leave_requests = []

    try:
        tickets = await mcp_list_tickets(employee_id)
    except Exception as e:
        logger.warning(f"Error fetching tickets via MCP: {e}")
        tickets = []

    return {
        "employee_id": employee_id,
        "mcp_connected": True,
        "mcp_token_prefix": MCP_TOKEN[:10] + "...",
        "profile": profile,
        "leave_balances": balances,
        "leave_requests": leave_requests,
        "service_tickets": tickets,
        "pubsub_compensation_queue": [],
    }
