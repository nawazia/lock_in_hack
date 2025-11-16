"""Orchestrator Agent - Coordinates all agents using LangGraph."""
import logging
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from agents.news_search_agent import NewsSearchAgent
from agents.rag_agent import RAGAgent
from agents.analysis_agent import AnalysisAgent
from agents.summary_agent import SummaryAgent
from config.llm_setup import get_llm
import functools

def setup_logging(log_file: str = "agent_orchestrator.log", level=logging.INFO):
    """Configures logging to output to both console and a file."""
    
    # 1. Root Logger Setup
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Prevent duplicate handlers if called multiple times
    if root_logger.hasHandlers():
        return

    # 2. Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 3. Console Handler (for prints)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 4. File Handler (for log file)
    file_handler = logging.FileHandler(log_file, mode='w') # mode='w' clears file on start
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Print a confirmation message to the console
    print(f"✅ Logging initialized. Outputting to console and file: {log_file}")

# Initialize logging immediately
setup_logging()

logger = logging.getLogger(__name__)

def middleware_wrapper(func):
    """A decorator to add 'middleware' functionality (e.g., logging) to a node function."""

    @functools.wraps(func)
    def wrapper(self, state: Dict) -> Dict:
        node_name = func.__name__.strip('_') # Get the clean node name (e.g., "search")
        
        # --- Pre-execution Logic (Middleware Start) ---
        logger.info(f"--- [MIDDLWARE] Starting node: {node_name} ---")
        
        # --- Execute the original node function ---
        try:
            new_state = func(self, state)
        except Exception as e:
            # --- Error Handling Logic (Middleware Error) ---
            logger.error(f"!!! [MIDDLWARE] Error in {node_name}: {e}")
            # You could modify the state here to handle the error gracefully,
            # e.g., setting a dedicated error flag or logging the traceback.
            state["metadata"][f"{node_name}_middleware_error"] = str(e)
            # Re-raise the exception so LangGraph can still log it or handle retries
            raise e
        
        # --- Post-execution Logic (Middleware End) ---
        logger.info(f"--- [MIDDLWARE] Completed node: {node_name} ---")
        return new_state

    return wrapper


# Define the state schema for LangGraph
class GraphState(TypedDict):
    """State for the LangGraph workflow."""
    user_query: str
    search_results: List[Any]
    rag_results: List[Any]
    analysis: Optional[str]
    summary: Optional[str]
    next_agent: Optional[str]
    completed_agents: List[str]
    metadata: Dict[str, Any]


class OrchestratorAgent:
    """Orchestrator that coordinates multiple agents to process news queries intelligently."""

    def __init__(self, llm=None):
        """Initialize the orchestrator.

        Args:
            llm: Language model to use for all agents
        """
        self.llm = llm or get_llm("openrouter")

        # Initialize all agents
        self.news_search_agent = NewsSearchAgent(llm=self.llm)
        self.rag_agent = RAGAgent()
        self.analysis_agent = AnalysisAgent(llm=self.llm)
        self.summary_agent = SummaryAgent(llm=self.llm)

        # Build the orchestration graph
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow for agent orchestration with conditional routing."""

        workflow = StateGraph(GraphState)

        # Add nodes (Only agent nodes that update the state)
        workflow.add_node("search", self._search_node)
        workflow.add_node("rag", self._rag_node)
        workflow.add_node("analysis", self._analysis_node)
        workflow.add_node("summary", self._summary_node)

        # 1. Start with search
        workflow.set_entry_point("search")

        # 2. Search -> RAG (Fixed edge)
        workflow.add_edge("search", "rag")

        # 3. RAG -> Conditional Routing
        # Use add_conditional_edges directly from "rag" to the downstream nodes.
        workflow.add_conditional_edges(
            "rag",        # Source node is "rag"
            self._determine_next_step, # Router function that returns the next node name
            {
                "analysis": "analysis",
                "summary": "summary",
            }
        )

        # 4. Analysis -> Summary (Fixed edge)
        workflow.add_edge("analysis", "summary")

        # 5. Summary -> END (Fixed edge)
        workflow.add_edge("summary", END)

        # Compile the graph
        app = workflow.compile()
        return app

    @middleware_wrapper
    def _search_node(self, state: Dict) -> Dict:
        """Node for news search agent."""
        logger.info("Running news search agent...")
        try:
            # Convert dict to AgentState for the agent
            from models.schemas import AgentState
            agent_state = AgentState(**state)
            agent_state = self.news_search_agent.run(agent_state)

            # Convert back to dict
            state["search_results"] = agent_state.search_results
            state["completed_agents"] = agent_state.completed_agents
            logger.info(f"Search complete: {len(state['search_results'])} articles found")
        except Exception as e:
            logger.error(f"Error in search node: {e}")
            state["metadata"]["search_error"] = str(e)
        return state
    
    def _determine_next_step(self, state: Dict) -> str:
        """
        Conditional router function to decide the next step (Analysis or Summary).
        Returns the name of the next node (e.g., "analysis", "summary").
        """
        logger.info("Running router logic...")
        # ... (Your existing logic) ...
        # Example logic: Only run analysis if both current and historical data are found.
        search_count = len(state.get("search_results", []))
        rag_count = len(state.get("rag_results", []))

        if search_count > 0 and rag_count > 0:
            logger.info("Both search and RAG data available. Routing to Analysis.")
            return "analysis"
        else:
            logger.info("Insufficient data for full analysis. Routing directly to Summary.")
            return "summary"

    @middleware_wrapper
    def _rag_node(self, state: Dict) -> Dict:
        """Node for RAG agent."""
        logger.info("Running RAG agent...")
        try:
            from models.schemas import AgentState
            agent_state = AgentState(**state)
            agent_state = self.rag_agent.run(agent_state)

            state["rag_results"] = agent_state.rag_results
            state["completed_agents"] = agent_state.completed_agents
            logger.info(f"RAG complete: {len(state['rag_results'])} historical articles retrieved")
        except Exception as e:
            logger.error(f"Error in RAG node: {e}")
            state["metadata"]["rag_error"] = str(e)
        return state

    @middleware_wrapper
    def _analysis_node(self, state: Dict) -> Dict:
        """Node for analysis agent."""
        logger.info("Running analysis agent...")
        try:
            from models.schemas import AgentState
            agent_state = AgentState(**state)
            agent_state = self.analysis_agent.run(agent_state)

            state["analysis"] = agent_state.analysis
            state["completed_agents"] = agent_state.completed_agents
            state["metadata"] = agent_state.metadata
            logger.info("Analysis complete")
        except Exception as e:
            logger.error(f"Error in analysis node: {e}")
            state["metadata"]["analysis_error"] = str(e)
        return state

    @middleware_wrapper
    def _summary_node(self, state: Dict) -> Dict:
        """Node for summary agent."""
        logger.info("Running summary agent...")
        try:
            from models.schemas import AgentState
            agent_state = AgentState(**state)
            agent_state = self.summary_agent.run(agent_state)

            state["summary"] = agent_state.summary
            state["completed_agents"] = agent_state.completed_agents
            logger.info("Summary complete")
        except Exception as e:
            logger.error(f"Error in summary node: {e}")
            state["metadata"]["summary_error"] = str(e)
        return state

    def process_query(self, query: str) -> dict:
        """Process a user query through the multi-agent system.

        Args:
            query: User's news query

        Returns:
            Dictionary containing the final results
        """
        logger.info(f"Processing query: {query}")

        # Create initial state as a dict (LangGraph works with dicts)
        initial_state = {
            "user_query": query,
            "search_results": [],
            "rag_results": [],
            "analysis": None,
            "summary": None,
            "next_agent": None,
            "completed_agents": [],
            "metadata": {}
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Format the output (final_state is a dict)
        result = {
            "query": query,
            "summary": final_state.get("summary", ""),
            "analysis": final_state.get("analysis", ""),
            "search_results_count": len(final_state.get("search_results", [])),
            "rag_results_count": len(final_state.get("rag_results", [])),
            "completed_agents": final_state.get("completed_agents", []),
            "metadata": final_state.get("metadata", {}),
        }

        # Add any errors that occurred
        metadata = final_state.get("metadata", {})
        errors = {}
        for key in ["search_error", "rag_error", "analysis_error", "summary_error"]:
            if key in metadata:
                errors[key] = metadata[key]
        if errors:
            result["errors"] = errors

        logger.info("Query processing complete")
        return result

    def get_rag_stats(self) -> dict:
        """Get statistics about the RAG storage."""
        return self.rag_agent.get_stats()

    def visualize_graph(self, output_path: str = "output/workflow_graph.png"):
        """Visualize the workflow graph and save to file.

        Args:
            output_path: Path to save the graph visualization (default: output/workflow_graph.png)
        """
        try:
            import os
            from pathlib import Path

            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Get the graph as PNG
            png_data = self.graph.get_graph().draw_mermaid_png()

            # Save to file
            with open(output_path, 'wb') as f:
                f.write(png_data)

            logger.info(f"Graph visualization saved to: {output_path}")
            print(f"✅ Workflow graph saved to: {output_path}")

            # Also try to display if in Jupyter
            try:
                from IPython.display import Image, display
                display(Image(png_data))
            except:
                pass

        except Exception as e:
            logger.warning(f"Could not visualize graph: {e}")
            logger.info("Graph visualization requires graphviz. Install with: brew install graphviz (macOS) or apt-get install graphviz (Linux)")


def build_agent(llm=None):
    """Factory function to build the orchestrator agent.

    Args:
        llm: Optional language model to use

    Returns:
        OrchestratorAgent instance
    """
    return OrchestratorAgent(llm=llm)
