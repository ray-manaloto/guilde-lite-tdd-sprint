"""PydanticAI web UI app factory for the assistant agent."""

from app.agents import AssistantAgent, Deps


def create_app():
    """Create the PydanticAI web UI ASGI app."""
    agent = AssistantAgent().agent
    return agent.to_web(deps=Deps())
