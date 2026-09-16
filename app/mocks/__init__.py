"""Mock backends for HR Agentic Solution (MVP 1) local execution and deterministic evaluation."""
from app.mocks.policy_rag import search_policy_documents
from app.mocks.workweek_db import WorkWeekMockDB, workweek_db
from app.mocks.service_db import ServiceImmediatelyMockDB, service_db

def reset_all_mocks() -> None:
    """Resets all mock databases to their clean initial state for deterministic evaluation runs."""
    workweek_db.reset()
    service_db.reset()
