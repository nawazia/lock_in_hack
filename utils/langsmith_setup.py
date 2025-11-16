"""LangSmith integration for tracing and observability."""
import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def setup_langsmith(
    project_name: Optional[str] = None,
    enabled: Optional[bool] = None
) -> bool:
    """Configure LangSmith tracing for the application.

    Args:
        project_name: Name of the LangSmith project (defaults to env var or 'multi-agent-news')
        enabled: Whether to enable LangSmith (defaults to env var LANGSMITH_ENABLED)

    Returns:
        True if LangSmith was successfully enabled, False otherwise
    """
    # Check if explicitly disabled
    if enabled is False:
        logger.info("LangSmith tracing disabled by configuration")
        return False

    # Check environment variable
    langsmith_enabled = os.getenv("LANGSMITH_ENABLED", "false").lower() == "true"
    if enabled is None and not langsmith_enabled:
        logger.info("LangSmith tracing not enabled (set LANGSMITH_ENABLED=true to enable)")
        return False

    # Check for API key
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        logger.warning("LangSmith enabled but LANGSMITH_API_KEY not set. Tracing disabled.")
        return False

    try:
        # Set environment variables for LangSmith
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key

        # Set project name
        project = project_name or os.getenv("LANGSMITH_PROJECT", "multi-agent-news")
        os.environ["LANGCHAIN_PROJECT"] = project

        # Optional: Set endpoint if using self-hosted
        endpoint = os.getenv("LANGSMITH_ENDPOINT")
        if endpoint:
            os.environ["LANGCHAIN_ENDPOINT"] = endpoint

        logger.info(f"✅ LangSmith tracing enabled for project: {project}")
        print(f"🔍 LangSmith tracing enabled - Project: {project}")
        return True

    except Exception as e:
        logger.error(f"Failed to setup LangSmith: {e}")
        return False


def get_langsmith_url() -> Optional[str]:
    """Get the LangSmith project URL if tracing is enabled.

    Returns:
        URL to LangSmith project or None if not configured
    """
    if os.getenv("LANGCHAIN_TRACING_V2") != "true":
        return None

    project = os.getenv("LANGCHAIN_PROJECT", "multi-agent-news")
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://smith.langchain.com")

    # Extract base URL (remove /api if present)
    if "/api" in endpoint:
        base_url = endpoint.split("/api")[0]
    else:
        base_url = endpoint

    return f"{base_url}/o/default/projects/p/{project}"


@contextmanager
def trace_run(
    run_name: str,
    run_type: str = "chain",
    tags: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Context manager for tracing a specific run with custom metadata.

    Args:
        run_name: Name for this run
        run_type: Type of run (chain, llm, tool, retriever, etc.)
        tags: List of tags for this run
        metadata: Additional metadata to attach

    Example:
        with trace_run("search_query", tags=["search"], metadata={"query": query}):
            results = search_agent.search(query)
    """
    if os.getenv("LANGCHAIN_TRACING_V2") != "true":
        # Tracing not enabled, just yield
        yield
        return

    try:
        from langsmith import traceable

        # Create a traceable function wrapper
        @traceable(
            run_type=run_type,
            name=run_name,
            tags=tags or [],
            metadata=metadata or {}
        )
        def traced_context():
            return None

        traced_context()
        yield

    except ImportError:
        logger.warning("langsmith package not installed. Install with: pip install langsmith")
        yield
    except Exception as e:
        logger.error(f"Error in trace_run: {e}")
        yield


def add_run_metadata(metadata: Dict[str, Any]):
    """Add metadata to the current LangSmith run.

    Args:
        metadata: Dictionary of metadata to add

    Example:
        add_run_metadata({"user_query": query, "result_count": len(results)})
    """
    if os.getenv("LANGCHAIN_TRACING_V2") != "true":
        return

    try:
        from langsmith import get_current_run_tree

        run = get_current_run_tree()
        if run:
            for key, value in metadata.items():
                run.metadata[key] = value
    except Exception as e:
        logger.debug(f"Could not add run metadata: {e}")


def add_run_tags(tags: list):
    """Add tags to the current LangSmith run.

    Args:
        tags: List of tags to add

    Example:
        add_run_tags(["production", "high-priority"])
    """
    if os.getenv("LANGCHAIN_TRACING_V2") != "true":
        return

    try:
        from langsmith import get_current_run_tree

        run = get_current_run_tree()
        if run:
            run.tags.extend(tags)
    except Exception as e:
        logger.debug(f"Could not add run tags: {e}")


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is currently enabled.

    Returns:
        True if tracing is enabled, False otherwise
    """
    return os.getenv("LANGCHAIN_TRACING_V2") == "true"
