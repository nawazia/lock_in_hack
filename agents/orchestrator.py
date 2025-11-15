"""Orchestrator Agent - Coordinates all agents using LangGraph."""

import logging
from typing import Any, Dict, List, Optional, TypedDict

from langsmith import traceable
from langgraph.graph import END, StateGraph

from agents.analysis_agent import AnalysisAgent
from agents.news_search_agent import NewsSearchAgent
from agents.rag_agent import RAGAgent
from agents.summary_agent import SummaryAgent
from config.llm_setup import get_llm_openai

logger = logging.getLogger(__name__)


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
        self.llm = llm or get_llm_openai()

        # Initialize all agents
        self.news_search_agent = NewsSearchAgent(llm=self.llm)
        self.rag_agent = RAGAgent()
        self.analysis_agent = AnalysisAgent(llm=self.llm)
        self.summary_agent = SummaryAgent(llm=self.llm)

        # Build the orchestration graph
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow for agent orchestration."""

        # Define the workflow graph
        workflow = StateGraph(GraphState)

        # Add nodes for each agent
        workflow.add_node("search", self._search_node)
        workflow.add_node("rag", self._rag_node)
        workflow.add_node("analysis", self._analysis_node)
        workflow.add_node("summary", self._summary_node)

        # Define the workflow edges
        # Start with search
        workflow.set_entry_point("search")

        # Search -> RAG (store and retrieve)
        workflow.add_edge("search", "rag")

        # RAG -> Analysis (analyze all articles)
        workflow.add_edge("rag", "analysis")

        # Analysis -> Summary (generate final output)
        workflow.add_edge("analysis", "summary")

        # Summary -> END
        workflow.add_edge("summary", END)

        # Compile the graph
        app = workflow.compile()
        return app

    @traceable(name="search_node")
    def _search_node(self, state: Dict) -> Dict:
        """Node for news search agent."""
        logger.info("Running news search agent...")
        try:
            # Convert dict to AgentState for the agent
            from models.schemas import AgentState

            print("running agent state for search")
            agent_state = AgentState(**state)
            agent_state = self.news_search_agent.run(agent_state)

            # Convert back to dict
            state["search_results"] = agent_state.search_results
            state["completed_agents"] = agent_state.completed_agents
            logger.info(
                f"Search complete: {len(state['search_results'])} articles found"
            )
        except Exception as e:
            logger.error(f"Error in search node: {e}")
            state["metadata"]["search_error"] = str(e)
        return state

    @traceable(name="rag_node")
    def _rag_node(self, state: Dict) -> Dict:
        """Node for RAG agent."""
        logger.info("Running RAG agent...")
        try:
            from models.schemas import AgentState

            agent_state = AgentState(**state)
            agent_state = self.rag_agent.run(agent_state)

            state["rag_results"] = agent_state.rag_results
            state["completed_agents"] = agent_state.completed_agents
            logger.info(
                f"RAG complete: {len(state['rag_results'])} historical articles retrieved"
            )
        except Exception as e:
            logger.error(f"Error in RAG node: {e}")
            state["metadata"]["rag_error"] = str(e)
        return state

    @traceable(name="analysis_node")
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

    @traceable(name="summary_node")
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

    @traceable(name="process_query", run_type="chain")
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
            "metadata": {},
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
            with open(output_path, "wb") as f:
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
            logger.info(
                "Graph visualization requires graphviz. Install with: brew install graphviz (macOS) or apt-get install graphviz (Linux)"
            )


def build_agent(llm=None):
    """Factory function to build the orchestrator agent.

    Args:
        llm: Optional language model to use

    Returns:
        OrchestratorAgent instance
    """
    return OrchestratorAgent(llm=llm)
