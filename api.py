#!/usr/bin/env python3
"""
Flask API for Multi-Agent News System

This provides a REST API endpoint to query the multi-agent system.
All LLM calls and tool executions will be traced in LangSmith.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from langsmith import Client as LangSmithClient
from pydantic import BaseModel
from pydantic.json import pydantic_encoder

from agents.orchestrator import build_agent
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(level=os.getenv("LOG_LEVEL", "INFO"))

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize the orchestrator (singleton)
orchestrator = None

# Initialize LangSmith client if tracing is enabled
langsmith_client = None
if os.getenv("LANGCHAIN_TRACING_V2") == "true":
    try:
        langsmith_client = LangSmithClient()
        logger.info("LangSmith client initialized")
    except Exception as e:
        logger.warning(f"Could not initialize LangSmith client: {e}")


class PydanticJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        return super().default(obj)


app.json = PydanticJSONProvider(app)


def get_orchestrator():
    """Get or create the orchestrator instance."""
    global orchestrator
    if orchestrator is None:
        logger.info("Initializing multi-agent orchestrator...")
        orchestrator = build_agent()
        logger.info("Orchestrator initialized successfully")
    return orchestrator


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "multi-agent-news-system"}), 200


@app.route("/api/query", methods=["POST"])
def process_query():
    """
    Process a news query through the multi-agent system.

    Request body:
    {
        "query": "Your news query here"
    }

    Response:
    {
        "success": true,
        "data": {
            "query": "...",
            "summary": "...",
            "analysis": "...",
            "search_results_count": 5,
            "rag_results_count": 3,
            "completed_agents": [...],
            "metadata": {...}
        },
        "langsmith_url": "https://smith.langchain.com/..."
    }
    """
    try:
        # Get query from request body
        data = request.get_json()

        if not data or "query" not in data:
            return (
                jsonify(
                    {"success": False, "error": "Missing 'query' field in request body"}
                ),
                400,
            )

        query = data["query"]

        if not query or not isinstance(query, str) or len(query.strip()) == 0:
            return (
                jsonify(
                    {"success": False, "error": "Query must be a non-empty string"}
                ),
                400,
            )

        logger.info(f"Received query: {query}")

        # Get orchestrator and process query
        orch = get_orchestrator()
        result = orch.process_query(query)

        # Build response
        response = {"success": True, "data": result}

        # Add LangSmith trace URL if tracing is enabled
        if os.getenv("LANGCHAIN_TRACING_V2") == "true":
            project_name = os.getenv("LANGCHAIN_PROJECT", "lock-in-hack-multi-agent")
            response["langsmith_info"] = {
                "tracing_enabled": True,
                "project": project_name,
                "dashboard_url": f"https://smith.langchain.com/o/default/projects/p/{project_name}",
            }

        logger.info("Query processed successfully")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    Get RAG storage statistics.

    Response:
    {
        "success": true,
        "stats": {
            "total_documents": 100,
            "collection_name": "news_articles",
            "persist_directory": "..."
        }
    }
    """
    try:
        orch = get_orchestrator()
        stats = orch.get_rag_stats()

        return jsonify({"success": True, "stats": stats}), 200

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/traces", methods=["GET"])
def get_traces():
    """
    Get list of available trace runs from LangSmith.

    Response:
    {
        "success": true,
        "traces": [...]
    }
    """
    if not langsmith_client:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "LangSmith client not initialized. Check LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY",
                }
            ),
            503,
        )

    try:
        project_name = os.getenv("LANGCHAIN_PROJECT", "lock-in-hack-multi-agent")

        # Fetch runs from LangSmith
        runs = list(
            langsmith_client.list_runs(
                project_name=project_name,
                limit=50,
            )
        )

        # Format trace summaries
        traces = []
        for run in runs:
            if not run.parent_run_id:  # Only root runs
                traces.append(
                    {
                        "id": str(run.id),
                        "name": run.name,
                        "start_time": (
                            run.start_time.isoformat() if run.start_time else None
                        ),
                        "end_time": run.end_time.isoformat() if run.end_time else None,
                        "run_type": run.run_type,
                        "status": "error" if run.error else "success",
                    }
                )

        return jsonify({"success": True, "traces": traces}), 200

    except Exception as e:
        logger.error(f"Error fetching traces: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/traces/<run_id>", methods=["GET"])
def get_trace_details(run_id):
    """
    Get detailed trace data for a specific run.

    Response:
    {
        "success": true,
        "trace": {
            "run_id": "...",
            "runs": [...]
        }
    }
    """
    if not langsmith_client:
        return (
            jsonify({"success": False, "error": "LangSmith client not initialized"}),
            503,
        )

    try:
        # Get the root run and all its descendants
        runs_data = []

        def fetch_run_tree(run_id):
            run = langsmith_client.read_run(run_id)

            # Convert run to dict with all necessary fields
            run_dict = {
                "id": str(run.id),
                "name": run.name,
                "run_type": run.run_type,
                "start_time": run.start_time.isoformat() if run.start_time else None,
                "end_time": run.end_time.isoformat() if run.end_time else None,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "error": run.error,
                "tags": run.tags,
                "extra": run.extra,
                "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
                "child_run_ids": [str(cid) for cid in (run.child_run_ids or [])],
                "feedback_stats": run.feedback_stats,
                "total_tokens": getattr(run, "total_tokens", None),
                "prompt_tokens": getattr(run, "prompt_tokens", None),
                "completion_tokens": getattr(run, "completion_tokens", None),
                "events": getattr(run, "events", []),
            }

            runs_data.append(run_dict)

            # Recursively fetch children
            if run.child_run_ids:
                for child_id in run.child_run_ids:
                    fetch_run_tree(child_id)

        fetch_run_tree(run_id)

        return (
            jsonify({"success": True, "trace": {"run_id": run_id, "runs": runs_data}}),
            200,
        )

    except Exception as e:
        logger.error(f"Error fetching trace details: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/traces/latest", methods=["GET"])
def get_latest_trace():
    """
    Get the most recent trace.

    Response:
    {
        "success": true,
        "trace": {...}
    }
    """
    if not langsmith_client:
        return (
            jsonify({"success": False, "error": "LangSmith client not initialized"}),
            503,
        )

    try:
        project_name = os.getenv("LANGCHAIN_PROJECT", "lock-in-hack-multi-agent")

        # Get most recent root run
        runs = list(
            langsmith_client.list_runs(
                project_name=project_name, limit=1, filter="eq(parent_run_id, null)"
            )
        )

        if not runs:
            return jsonify({"success": False, "error": "No traces found"}), 404

        latest_run_id = str(runs[0].id)

        # Reuse the trace details endpoint logic
        return get_trace_details(latest_run_id)

    except Exception as e:
        logger.error(f"Error fetching latest trace: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/", methods=["GET"])
def index():
    """Root endpoint with API information."""
    return (
        jsonify(
            {
                "service": "Multi-Agent News Processing System",
                "version": "1.0.0",
                "endpoints": {
                    "POST /api/query": "Process a news query",
                    "GET /api/stats": "Get RAG storage statistics",
                    "GET /api/traces": "List available traces",
                    "GET /api/traces/<run_id>": "Get trace details",
                    "GET /api/traces/latest": "Get latest trace",
                    "GET /health": "Health check",
                },
                "langsmith": {
                    "tracing_enabled": os.getenv("LANGCHAIN_TRACING_V2") == "true",
                    "project": os.getenv(
                        "LANGCHAIN_PROJECT", "lock-in-hack-multi-agent"
                    ),
                },
            }
        ),
        200,
    )


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    logger.info("=" * 80)
    logger.info("Multi-Agent News Processing System - API Server")
    logger.info("=" * 80)
    logger.info(f"Starting Flask server on port {port}...")

    if os.getenv("LANGCHAIN_TRACING_V2") == "true":
        project = os.getenv("LANGCHAIN_PROJECT", "lock-in-hack-multi-agent")
        logger.info(f"LangSmith tracing enabled - Project: {project}")
        logger.info(f"View traces at: https://smith.langchain.com")
    else:
        logger.warning(
            "LangSmith tracing is disabled. Set LANGCHAIN_TRACING_V2=true in .env to enable"
        )

    logger.info("=" * 80)

    app.run(host="0.0.0.0", port=port, debug=debug)
