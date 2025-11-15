#!/bin/bash
# Setup script for Multi-Agent News System

set -e  # Exit on error

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Multi-Agent News System - Setup Script                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if conda is available
if command -v conda &> /dev/null; then
    echo "🐍 Using Conda environment"
    ENV_TYPE="conda"
else
    echo "🐍 Using Python venv"
    ENV_TYPE="venv"
fi

if [ "$ENV_TYPE" = "conda" ]; then
    # Conda setup
    echo ""
    echo "🔨 Setting up Conda environment..."
    if conda env list | grep -q "multi_agent_news"; then
        echo "   Conda environment 'multi_agent_news' already exists. Skipping creation..."
    else
        conda create -n multi_agent_news python=3.10 -y
        echo "   ✅ Conda environment created"
    fi

    echo ""
    echo "📦 Installing dependencies in conda environment..."
    eval "$(conda shell.bash hook)"
    conda activate multi_agent_news
    pip install -r requirements.txt -q
    echo "   ✅ Dependencies installed"
else
    # venv setup
    echo ""
    echo "🔨 Creating virtual environment..."
    if [ -d "venv" ]; then
        echo "   Virtual environment already exists. Skipping..."
    else
        python3 -m venv venv
        echo "   ✅ Virtual environment created"
    fi

    echo ""
    echo "🔌 Activating virtual environment..."
    source venv/bin/activate
    echo "   ✅ Virtual environment activated"

    echo ""
    echo "⬆️  Upgrading pip..."
    pip install --upgrade pip -q
    echo "   ✅ pip upgraded"

    echo ""
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt -q
    echo "   ✅ Dependencies installed"
fi

# Setup environment file
echo ""
echo "⚙️  Setting up environment configuration..."
if [ -f ".env" ]; then
    echo "   .env file already exists. Skipping..."
else
    cp .env.example .env
    echo "   ✅ .env file created from template"
    echo ""
    echo "   ⚠️  IMPORTANT: Please edit .env and add your API keys:"
    echo "      - OPENAI_API_KEY"
    echo "      - VALYU_API_KEY"
fi

# Create storage directory
echo ""
echo "📁 Creating storage directories..."
mkdir -p storage/chroma_db
mkdir -p logs
echo "   ✅ Directories created"

# Make scripts executable
echo ""
echo "🔧 Making scripts executable..."
chmod +x run_agent.py cli.py
echo "   ✅ Scripts are executable"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete! 🎉                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your API keys"
echo "  2. Activate virtual environment: source venv/bin/activate"
echo "  3. Run the system:"
echo "     - Interactive mode: python cli.py"
echo "     - Single query: python cli.py -q 'Your query here'"
echo "     - Example: python run_agent.py"
echo ""
echo "For more information, see README.md and QUICKSTART.md"
echo ""
