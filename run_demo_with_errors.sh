#!/bin/bash

# Script to run the travel example with error injection enabled
# This will inject errors within the LangGraph workflow so they appear in LangSmith traces

echo "================================================================================"
echo "  Running Travel Planning Demo with ERROR INJECTION"
echo "================================================================================"
echo ""
echo "This will:"
echo "  ✓ Enable error injection within the LangGraph workflow"
echo "  ✓ Show all errors in LangSmith traces"
echo "  ✓ Demonstrate audit detection and auto-fixing"
echo "  ✓ Show feedback loop routing decisions"
echo ""
echo "================================================================================"
echo ""

# Enable demo error injection
export DEMO_ERRORS=true

# Run the travel example
python travel_example.py

echo ""
echo "================================================================================"
echo "  Demo complete! Check LangSmith for the full trace with error injection"
echo "================================================================================"
