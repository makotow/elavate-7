"""Google ADK App Package Initialization for HR Agentic Solution."""
from google.adk.apps import App
from app.agent import root_agent

# Mandatory: name must match the directory name 'app' for ADK session lookup
app = App(root_agent=root_agent, name="app")

__all__ = ["app", "root_agent"]
