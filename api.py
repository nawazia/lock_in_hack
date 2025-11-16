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


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "multi-agent-news-system"}), 200


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

        # Fetch runs from LangSmith (ordered by most recent first by default)
        runs = list(
            langsmith_client.list_runs(
                project_name=project_name,
                limit=100,  # Get more to ensure we find enough root runs
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


def _fetch_trace_tree(run_id):
    """
    Helper function to fetch a complete trace tree with all descendants.
    Uses batch fetching to avoid rate limiting (1-2 API calls instead of N calls).
    """
    project_name = os.getenv("LANGCHAIN_PROJECT", "lock-in-hack-multi-agent")

    try:
        # First, fetch the root run to get trace_id
        root_run = langsmith_client.read_run(run_id)
        trace_id = getattr(root_run, "trace_id", run_id)

        logger.info(f"Batch fetching all runs for trace {trace_id}")

        # Batch fetch ALL runs in this trace (single API call!)
        all_runs = list(
            langsmith_client.list_runs(
                project_name=project_name,
                trace_id=trace_id,
                limit=1000,  # Should be enough for most traces
            )
        )

        logger.info(f"Fetched {len(all_runs)} runs in single batch call")

        # Convert all runs to dict format
        runs_data = []
        for run in all_runs:
            # Calculate latency if we have start and end times
            latency = None
            if run.start_time and run.end_time:
                latency = (run.end_time - run.start_time).total_seconds()

            # Convert run to dict with all necessary fields
            run_dict = {
                "id": str(run.id),
                "name": run.name,
                "run_type": run.run_type,
                "start_time": run.start_time.isoformat() if run.start_time else None,
                "end_time": run.end_time.isoformat() if run.end_time else None,
                "latency": latency,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "error": run.error,
                "tags": run.tags or [],
                "metadata": run.extra.get("metadata", {}) if run.extra else {},
                "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
                "child_run_ids": [str(cid) for cid in (run.child_run_ids or [])],
                "feedback_stats": run.feedback_stats or {},
                "total_tokens": getattr(run, "total_tokens", None),
                "prompt_tokens": getattr(run, "prompt_tokens", None),
                "completion_tokens": getattr(run, "completion_tokens", None),
                "status": "error" if run.error else "success",
            }
            print(run_dict["name"], run_dict["run_type"])
            runs_data.append(run_dict)

        return list(reversed(runs_data))

    except Exception as e:
        logger.error(f"Error batch fetching trace tree: {e}", exc_info=True)
        return []


@app.route("/api/traces/latest", methods=["GET"])
def get_latest_trace():
    """Get the most recent trace with full tree expanded."""
    if not langsmith_client:
        return (
            jsonify({"success": False, "error": "LangSmith client not initialized"}),
            503,
        )

    try:
        project_name = os.getenv("LANGCHAIN_PROJECT", "lock-in-hack-multi-agent")

        print("getting latest trace")

        # Get recent runs - default order is descending by start_time (most recent first)
        all_runs = list(
            langsmith_client.list_runs(
                project_name=project_name,
                limit=100,  # Fetch enough to find a root run
                # Don't use order parameter - defaults to desc by start_time
            )
        )

        if not all_runs:
            logger.warning("No runs found in project")
            return jsonify({"success": False, "error": "No traces found"}), 404

        # Find the first run that has no parent (root run)
        root_run = None
        for run in all_runs:
            if run.parent_run_id is None:
                root_run = run
                break

        if not root_run:
            logger.warning("No root runs found among fetched runs")
            return jsonify({"success": False, "error": "No root traces found"}), 404

        latest_run_id = str(root_run.id)
        logger.info(f"Found latest root run: {root_run.name} (ID: {latest_run_id})")

        # Fetch the complete trace tree
        runs_data = _fetch_trace_tree(latest_run_id)
        logger.info(f"Fetched {len(runs_data)} runs in trace tree")

        # Build hierarchical structure for easier visualization
        trace_response = {
            "run_id": latest_run_id,
            "runs": runs_data,
            "total_runs": len(runs_data),
        }

        return jsonify({"success": True, "trace": trace_response}), 200

    except Exception as e:
        logger.error(f"Error fetching latest trace: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/traces/<run_id>", methods=["GET"])
def get_trace_details(run_id):
    """Get detailed trace data for a specific run with full tree expanded."""
    if not langsmith_client:
        return (
            jsonify({"success": False, "error": "LangSmith client not initialized"}),
            503,
        )

    try:
        logger.info(f"Fetching trace details for run: {run_id}")
        print("getting trace details for run id:", run_id)
        # Fetch the complete trace tree
        runs_data = _fetch_trace_tree(run_id)

        logger.info(f"Successfully fetched {len(runs_data)} runs in trace tree")

        trace_response = {
            "run_id": run_id,
            "runs": runs_data,
            "total_runs": len(runs_data),
        }

        return jsonify({"success": True, "trace": trace_response}), 200

    except Exception as e:
        logger.error(f"Error fetching trace details: {e}", exc_info=True)
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
                    "GET /api/traces": "List available traces",
                    "GET /api/traces/latest": "Get latest trace",
                    "GET /api/traces/<run_id>": "Get trace details",
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
    port = int(os.getenv("FLASK_PORT", 8000))
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
