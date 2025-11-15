# Quick Start Guide

Get up and running with the Multi-Agent News System in 5 minutes.

## Step 1: Automated Setup (Recommended)

```bash
# Run the setup script
./setup.sh
```

This will:
- Create virtual environment
- Install all dependencies
- Create .env from template

## Step 2: Configure API Keys

Edit `.env` and add your API keys:
```bash
OPENAI_API_KEY=sk-your-key-here
VALYU_API_KEY=your-key-here

# Optional: If using Bedrock instead of OpenAI
# TEAM_ID=your-team-id
# API_TOKEN=your-api-token
# LLM_PROVIDER=bedrock
```

## Step 3: Verify Setup

```bash
source venv/bin/activate  # Activate virtual environment
python verify_setup.py    # Check everything is configured
```

## Step 4: Run the System

```bash
# Interactive mode
python cli.py

# Or run example
python run_agent.py
```

## Step 4: Customize

Edit `run_agent.py` to change the query:

```python
queries = [
    "Your custom query here",
]
```

## What Happens When You Run It?

1. **Search Agent** finds latest news via Valyu API
2. **RAG Agent** stores articles and retrieves historical ones
3. **Analysis Agent** selects the most relevant articles
4. **Summary Agent** creates a comprehensive summary

## Example Output

```
================================================================================
Query: What are the latest developments in AI and machine learning?
================================================================================

📊 Results:
  - Search results: 5
  - Historical articles: 3
  - Completed agents: news_search, rag, analysis, summary

📝 Analysis:
Key Topics: AI, Machine Learning, GPT-4, Neural Networks
Sentiment: positive
Reasoning: Selected articles cover recent breakthroughs...

📰 Summary:
# AI Developments - November 2025

## Executive Summary
Recent developments in AI focus on...

[Full markdown summary]
================================================================================
```

## Troubleshooting

### Import Errors

Make sure you're in the project directory and virtual environment is activated:
```bash
cd lock_in_hack
source venv/bin/activate
```

### API Key Errors

Check that your `.env` file exists and contains valid API keys:
```bash
cat .env  # Should show OPENAI_API_KEY and VALYU_API_KEY
```

### ChromaDB Errors

ChromaDB requires SQLite. Install if missing:
```bash
# macOS
brew install sqlite3

# Ubuntu/Debian
sudo apt-get install sqlite3
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore individual agents in the `agents/` directory
- Customize prompts and behavior in each agent file
- Add more news sources beyond Valyu
