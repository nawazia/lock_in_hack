# Installation Guide

## Prerequisites

- Python 3.10+
- AWS credentials (for Bedrock)
- API keys: Valyu, SerpApi

## Setup Steps

### 1. Install hallbayes library

The EDFL hallucination detection requires the hallbayes library:

```bash
pip install git+https://github.com/leochlon/hallbayes.git
```

Or if you have it locally:
```bash
cd ../hallbayes
pip install -e .
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

VALYU_API_KEY=your_valyu_key
SERPAPI_API_KEY=your_serpapi_key

ENABLE_EDFL_VALIDATION=true
```

### 4. Run

```bash
python run_agent.py
```

## Troubleshooting

**hallbayes not found**: Install with `pip install git+https://github.com/leochlon/hallbayes.git`

**Disable EDFL**: Set `ENABLE_EDFL_VALIDATION=false` in `.env`
