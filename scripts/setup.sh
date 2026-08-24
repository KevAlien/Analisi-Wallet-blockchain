#!/bin/bash
# Setup script for SentryCage with AI Reasoning

set -e  # Exit on error

echo "🚀 SentryCage AI Setup Script"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys before running!"
    echo ""
    echo "Required configuration:"
    echo "  - ETHERSCAN_API_KEY"
    echo "  - ARBISCAN_API_KEY"
    echo "  - INFURA_API_KEY"
    echo "  - TELEGRAM_BOT_TOKEN"
    echo "  - TELEGRAM_CHAT_ID"
    echo ""
    echo "Optional (for cloud LLM providers):"
    echo "  - CLAUDE_API_KEY"
    echo "  - OPENAI_API_KEY"
    echo ""
    read -p "Press Enter after configuring .env file..."
fi

echo "🔧 Configuration options:"
echo ""
echo "Which LLM provider do you want to use?"
echo "  1) Ollama (Local - Docker, recommended for getting started)"
echo "  2) LMStudio (Local - requires LMStudio running on host)"
echo "  3) Claude (Cloud - requires API key)"
echo "  4) OpenAI (Cloud - requires API key)"
echo ""
read -p "Enter choice [1-4]: " llm_choice

case $llm_choice in
    1)
        echo "📦 Selected: Ollama (local Docker)"
        sed -i.bak 's/LLM_PROVIDER=.*/LLM_PROVIDER=ollama/' .env
        echo ""
        echo "Which model do you want to use?"
        echo "  1) llama3.1:8b (Recommended, ~8GB VRAM)"
        echo "  2) mistral:7b (Fast, ~6GB VRAM)"
        echo "  3) qwen2.5:14b (High quality, ~14GB VRAM)"
        read -p "Enter choice [1-3]: " model_choice
        case $model_choice in
            1) model="llama3.1:8b" ;;
            2) model="mistral:7b" ;;
            3) model="qwen2.5:14b" ;;
            *) model="llama3.1:8b" ;;
        esac
        sed -i.bak "s/OLLAMA_MODEL=.*/OLLAMA_MODEL=$model/" .env
        echo "✅ Will download $model on first run"
        ;;
    2)
        echo "📦 Selected: LMStudio"
        sed -i.bak 's/LLM_PROVIDER=.*/LLM_PROVIDER=lmstudio/' .env
        echo "⚠️  Make sure LMStudio is running on http://localhost:1234"
        ;;
    3)
        echo "📦 Selected: Claude"
        sed -i.bak 's/LLM_PROVIDER=.*/LLM_PROVIDER=claude/' .env
        echo "⚠️  Make sure you've set CLAUDE_API_KEY in .env"
        ;;
    4)
        echo "📦 Selected: OpenAI"
        sed -i.bak 's/LLM_PROVIDER=.*/LLM_PROVIDER=openai/' .env
        echo "⚠️  Make sure you've set OPENAI_API_KEY in .env"
        ;;
    *)
        echo "Invalid choice, using Ollama as default"
        sed -i.bak 's/LLM_PROVIDER=.*/LLM_PROVIDER=ollama/' .env
        ;;
esac

echo ""
echo "🔨 Building Docker containers..."
docker-compose build

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the SentryCage:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f whale-tracker"
echo ""
echo "To stop:"
echo "  docker-compose down"
echo ""
echo "To test LLM providers:"
echo "  docker-compose run --rm whale-tracker python scripts/test_llm.py"
echo ""
