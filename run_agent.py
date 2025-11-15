#!/usr/bin/env python3
"""
Multi-Agent News System - Main Runner

This orchestrates multiple agents to intelligently process news queries:
1. News Search Agent - Searches for news using Valyu
2. RAG Agent - Stores and retrieves historical articles
3. Analysis Agent - Analyzes and selects relevant articles
4. Summary Agent - Generates comprehensive summaries
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

from agents.orchestrator import build_agent
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(level=os.getenv("LOG_LEVEL", "INFO"))

# Initialize LangSmith tracing
if os.getenv("LANGCHAIN_TRACING_V2") == "true":
    logger.info(f"LangSmith tracing enabled - Project: {os.getenv('LANGCHAIN_PROJECT', 'lock-in-hack-multi-agent')}")
    logger.info("View traces at: https://smith.langchain.com")
else:
    logger.info("LangSmith tracing is disabled. Set LANGCHAIN_TRACING_V2=true in .env to enable")


def main():
    """Main execution function."""
    print("=" * 80)
    print("Multi-Agent News Processing System")
    print("=" * 80)

    # Build the orchestrator
    logger.info("Initializing multi-agent system...")
    orchestrator = build_agent()

    # Show RAG statistics
    rag_stats = orchestrator.get_rag_stats()
    logger.info(f"RAG Storage: {rag_stats}")

    # Example queries - you can modify these or add user input
    queries = [
        "What are the latest developments in AI and machine learning?",
        # "Tell me about recent climate change news",
        # "What's happening with cryptocurrency markets?",
    ]

    for query in queries:
        print("\n" + "=" * 80)
        print(f"Query: {query}")
        print("=" * 80)

        # Process the query through the multi-agent system
        result = orchestrator.process_query(query)

        # Display results
        print(f"\n📊 Results:")
        print(f"  - Search results: {result['search_results_count']}")
        print(f"  - Historical articles: {result['rag_results_count']}")
        print(f"  - Completed agents: {', '.join(result['completed_agents'])}")

        if "errors" in result:
            print(f"\n⚠️  Errors occurred:")
            for error_type, error_msg in result["errors"].items():
                print(f"  - {error_type}: {error_msg}")

        print(f"\n📝 Analysis:")
        print(result["analysis"])

        print(f"\n📰 Summary:")
        print(result["summary"])

        print("\n" + "=" * 80)

    # Final statistics
    final_stats = orchestrator.get_rag_stats()
    print(f"\n📚 Final RAG Statistics:")
    print(f"  - Total documents stored: {final_stats.get('total_documents', 0)}")
    print(f"  - Collection: {final_stats.get('collection_name', 'N/A')}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
