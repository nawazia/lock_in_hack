#!/usr/bin/env python3
"""
Simple script to generate and save the workflow graph visualization.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.orchestrator import build_agent

if __name__ == "__main__":
    print("🎨 Generating workflow graph...")

    # Build orchestrator
    orchestrator = build_agent()

    # Save graph visualization
    output_path = "output/workflow_graph.png"
    orchestrator.visualize_graph(output_path)

    print(f"\n✅ Done! Graph saved to: {output_path}")
