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
import requests
import uuid

from utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(level=os.getenv("LOG_LEVEL", "INFO"))

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Session storage for conversation state
# session_id -> {"orchestrator": TravelOrchestrator, "state": dict, "history": list}
sessions = {}

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


@app.route("/api/grounding", methods=["POST"])
def calculate_grounding():
    """
    Calculate grounding scores for LLM nodes based on their tool node predecessors.

    Request:
    {
        "nodes": [array of node data from runMap]
    }

    Response:
    {
        "success": true,
        "scores": {
            "node_id": score (1-10),
            ...
        }
    }
    """
    try:
        data = request.json
        nodes = data.get("nodes", [])

        if not nodes:
            return jsonify({"success": False, "error": "No nodes provided"}), 400

        # Get OpenRouter API key from environment
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "OPENROUTER_API_KEY not configured in .env",
                    }
                ),
                503,
            )

        # Build a map of node_id -> node for quick lookup
        node_map = {node["id"]: node for node in nodes}

        # Build parent-child relationships to find siblings
        children_by_parent = {}
        for node in nodes:
            parent_id = node.get("parentRunId")
            if parent_id:
                if parent_id not in children_by_parent:
                    children_by_parent[parent_id] = []
                children_by_parent[parent_id].append(node)

        # Sort children by start_time to get proper sibling order
        for parent_id in children_by_parent:
            children_by_parent[parent_id].sort(
                key=lambda n: n.get("startTime", "")
            )

        scores = {}

        # Find LLM nodes whose immediate preceding sibling is a tool node
        for node in nodes:
            if node.get("runType") != "llm":
                continue

            parent_id = node.get("parentRunId")
            if not parent_id:
                continue

            # Get siblings (nodes with same parent)
            siblings = children_by_parent.get(parent_id, [])
            if len(siblings) < 2:
                continue

            # Find this node's position among siblings
            try:
                node_index = siblings.index(node)
            except ValueError:
                continue

            # Check if there's a preceding sibling and if it's a tool
            if node_index > 0:
                prev_sibling = siblings[node_index - 1]
                if prev_sibling.get("runType") == "tool":
                    # We have a tool -> llm pair, calculate grounding score
                    tool_output = prev_sibling.get("outputs", {})
                    llm_output = node.get("outputs", {})

                    # Extract text content from outputs
                    tool_content = str(tool_output)
                    llm_content = str(llm_output)

                    # Call OpenRouter to score grounding
                    try:
                        prompt = f"""You are evaluating how well an LLM's response is grounded in factual information from a tool output.

Tool Output:
{tool_content}

LLM Response:
{llm_content}

Rate on a scale from 1-10 how well the LLM's response is grounded in the tool output:
- 10: Perfectly grounded, all claims directly supported by tool output
- 7-9: Mostly grounded, minor extrapolations
- 4-6: Partially grounded, some unsupported claims
- 1-3: Poorly grounded, mostly unsupported or contradictory

Respond with a JSON object containing:
1. "score": a number from 1-10
2. "reasoning": a brief explanation (2-3 sentences) of why you gave this score

Example format:
{{"score": 8, "reasoning": "The LLM response accurately reflects the key facts from the tool output. Minor details were omitted but no unsupported claims were made."}}

Respond with ONLY valid JSON, nothing else."""

                        response = requests.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {openrouter_api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": "openai/gpt-4o-mini",
                                "messages": [
                                    {"role": "user", "content": prompt}
                                ],
                            },
                            timeout=30,
                        )

                        if response.status_code == 200:
                            response_data = response.json()
                            result_text = response_data["choices"][0]["message"]["content"].strip()

                            # Parse JSON response
                            try:
                                import json
                                result = json.loads(result_text)
                                score = result.get("score")
                                reasoning = result.get("reasoning", "No reasoning provided")

                                if score and 1 <= score <= 10:
                                    scores[node["id"]] = {
                                        "score": score,
                                        "reasoning": reasoning
                                    }
                                    logger.info(f"Grounding score for {node['name']}: {score}")
                                else:
                                    logger.warning(f"Score out of range for {node['name']}: {score}")
                            except json.JSONDecodeError:
                                logger.warning(f"Could not parse JSON response for {node['name']}: {result_text}")
                        else:
                            logger.error(f"OpenRouter API error for {node['name']}: {response.status_code}")

                    except Exception as e:
                        logger.error(f"Error scoring node {node['name']}: {e}")
                        continue

        logger.info(f"Calculated {len(scores)} grounding scores")
        return jsonify({"success": True, "scores": scores}), 200

    except Exception as e:
        logger.error(f"Error in grounding endpoint: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Chat endpoint backed by OpenRouter GPT-4o-mini.
    Accepts messages with conversation history.
    """
    try:
        data = request.json
        user_message = data.get("message", "")
        history = data.get("history", [])

        if not user_message:
            return jsonify({"success": False, "error": "Message is required"}), 400

        # Get OpenRouter API key from environment
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "OPENROUTER_API_KEY not configured in .env",
                    }
                ),
                503,
            )

        # Build messages array for OpenRouter
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that helps users understand LangSmith traces. You have access to trace node information including inputs, outputs, latency, tokens, and errors. Provide clear, concise explanations about the trace execution.",
            }
        ]

        # Add conversation history
        messages.extend(history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Call OpenRouter API
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": messages,
            },
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.text}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"OpenRouter API error: {response.status_code}",
                    }
                ),
                500,
            )

        response_data = response.json()
        assistant_message = response_data["choices"][0]["message"]["content"]

        return jsonify({"success": True, "response": assistant_message}), 200

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def travel_query():
    """
    Travel planning endpoint using TravelOrchestrator.
    Accepts a travel query and returns itinerary or clarifying questions.
    Maintains conversation state across requests using session_id.
    """
    try:
        from agents.travel_orchestrator import TravelOrchestrator

        data = request.json
        query = data.get("query", "")
        session_id = data.get("session_id")
        optimization_preference = data.get("optimization_preference", "default")

        if not query:
            return jsonify({"success": False, "error": "Query is required"}), 400

        # Get or create session
        if session_id and session_id in sessions:
            # Reuse existing session
            session = sessions[session_id]
            orchestrator = session["orchestrator"]
            previous_state = session["state"]
            conversation_history = session.get("history", [])

            logger.info(f"Resuming session {session_id} with {len(conversation_history)} messages")
        else:
            # Create new session
            session_id = str(uuid.uuid4())
            orchestrator = TravelOrchestrator()
            previous_state = None
            conversation_history = []

            logger.info(f"Created new session {session_id}")

        # Add user message to history
        conversation_history.append({"role": "user", "content": query})

        # Process the query with previous state context
        if previous_state:
            # Continue from previous state
            # Override optimization preference from slider if it changed
            if optimization_preference:
                previous_state["optimization_preference"] = optimization_preference
            state = orchestrator.process_query(query.strip(), existing_state=previous_state)
        else:
            # First message - set optimization preference from slider
            state = orchestrator.process_query(query.strip())
            # Override optimization preference if provided
            if optimization_preference:
                state["optimization_preference"] = optimization_preference

        # Check if waiting for more input
        needs_input = orchestrator.is_waiting_for_input(state)

        # Add assistant response to history
        if needs_input and state.get("clarifying_questions"):
            assistant_content = "\n".join(state["clarifying_questions"])
        elif state.get("final_itinerary"):
            itinerary = state['final_itinerary']
            if isinstance(itinerary, dict):
                assistant_content = f"Created itinerary: {itinerary.get('title', 'Your Trip')}"
            else:
                assistant_content = f"Created itinerary: {itinerary.title}"
        else:
            assistant_content = "Processing your request..."

        conversation_history.append({"role": "assistant", "content": assistant_content})

        # Store updated session
        sessions[session_id] = {
            "orchestrator": orchestrator,
            "state": state,
            "history": conversation_history
        }

        # Get metadata and remove non-serializable objects
        metadata = state.get("metadata", {})
        if "observability_collector" in metadata:
            # Get observability report instead of the collector object
            collector = metadata.pop("observability_collector")
            try:
                metadata["observability_report"] = collector.generate_report()
            except:
                pass  # If report generation fails, just skip it

        # Build response
        response = {
            "success": True,
            "session_id": session_id,
            "needs_user_input": needs_input,
            "clarifying_questions": state.get("clarifying_questions", []),
            "travel_intent": state.get("travel_intent"),
            "final_itinerary": state.get("final_itinerary"),
            "summary": state.get("summary"),
            "metadata": metadata,
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in travel query endpoint: {e}", exc_info=True)
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
                    "POST /api/query": "Travel planning query",
                    "GET /api/traces": "List available traces",
                    "GET /api/traces/latest": "Get latest trace",
                    "GET /api/traces/<run_id>": "Get trace details",
                    "POST /api/grounding": "Calculate grounding scores for LLM nodes",
                    "POST /api/chat": "Chat with trace assistant",
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
