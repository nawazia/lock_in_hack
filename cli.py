#!/usr/bin/env python3
"""
Interactive CLI for the Multi-Agent News System

Provides a user-friendly command-line interface for querying news.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.orchestrator import build_agent
from utils.logger import setup_logger
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(level=os.getenv("LOG_LEVEL", "WARNING"))


def print_banner():
    """Print CLI banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║          Multi-Agent News Processing System                   ║
║                                                                ║
║  Intelligent news analysis powered by LangChain & LangGraph   ║
╚═══════════════════════════════════════════════════════════════╝
""")


def print_result(result: dict, verbose: bool = False):
    """Print query results in a formatted way."""
    print("\n" + "=" * 70)
    print(f"📊 Results Summary")
    print("=" * 70)
    print(f"  New articles found: {result['search_results_count']}")
    print(f"  Historical articles: {result['rag_results_count']}")
    print(f"  Pipeline: {' → '.join(result['completed_agents'])}")

    if "errors" in result:
        print(f"\n⚠️  Warnings:")
        for error_type, error_msg in result["errors"].items():
            print(f"  - {error_type}: {error_msg}")

    if verbose and result.get("analysis"):
        print(f"\n" + "=" * 70)
        print(f"📝 Analysis")
        print("=" * 70)
        print(result["analysis"])

    print(f"\n" + "=" * 70)
    print(f"📰 Summary")
    print("=" * 70)
    print(result["summary"])
    print("\n" + "=" * 70 + "\n")


def interactive_mode(orchestrator):
    """Run interactive query mode."""
    print("Interactive mode - Type your queries (or 'quit' to exit)")
    print("Commands: 'stats' - show RAG stats, 'quit' - exit\n")

    while True:
        try:
            query = input("\n🔍 Query: ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            if query.lower() == 'stats':
                stats = orchestrator.get_rag_stats()
                print(f"\n📚 RAG Statistics:")
                print(f"  Total documents: {stats.get('total_documents', 0)}")
                print(f"  Collection: {stats.get('collection_name', 'N/A')}")
                print(f"  Storage: {stats.get('persist_directory', 'N/A')}")
                continue

            # Process query
            print("\n⏳ Processing query through multi-agent pipeline...")
            result = orchestrator.process_query(query)
            print_result(result, verbose=True)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.error(f"Error processing query: {e}", exc_info=True)


def single_query_mode(orchestrator, query: str, verbose: bool = False):
    """Process a single query and exit."""
    print(f"\n🔍 Query: {query}\n")
    print("⏳ Processing through multi-agent pipeline...")

    result = orchestrator.process_query(query)
    print_result(result, verbose=verbose)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent News Processing System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python cli.py

  # Single query
  python cli.py -q "What's happening with AI?"

  # Verbose output
  python cli.py -q "Climate change news" -v

  # Show statistics
  python cli.py --stats
        """
    )

    parser.add_argument(
        '-q', '--query',
        type=str,
        help='Single query to process (non-interactive)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed analysis output'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show RAG storage statistics'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='WARNING',
        help='Set logging level'
    )

    args = parser.parse_args()

    # Update log level if specified
    if args.log_level:
        logger.setLevel(args.log_level)

    print_banner()

    # Initialize orchestrator
    print("🚀 Initializing multi-agent system...")
    try:
        orchestrator = build_agent()
        print("✅ System ready!\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        logger.error(f"Initialization error: {e}", exc_info=True)
        sys.exit(1)

    # Show stats if requested
    if args.stats:
        stats = orchestrator.get_rag_stats()
        print(f"\n📚 RAG Storage Statistics:")
        print(f"  Total documents: {stats.get('total_documents', 0)}")
        print(f"  Collection: {stats.get('collection_name', 'N/A')}")
        print(f"  Storage path: {stats.get('persist_directory', 'N/A')}")
        return

    # Single query mode
    if args.query:
        single_query_mode(orchestrator, args.query, args.verbose)
    else:
        # Interactive mode
        interactive_mode(orchestrator)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
