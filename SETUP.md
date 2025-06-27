# 🚀 LangGraph Project Setup Guide

This project uses **uv** exclusively for Python package and environment management. Follow this guide for a smooth setup experience.

## 📋 Prerequisites

1. **Python 3.13+** - Required for this project
2. **uv** - Modern Python package manager ([installation guide](https://docs.astral.sh/uv/))

## ⚡ Quick Start

```bash
# 1. Clone and navigate to the project
cd oreilly-langgraph

# 2. Install all dependencies (creates virtual environment automatically)
uv sync

# 3. Activate the environment
uv shell

# 4. Set up your API keys (copy template and add your keys)
cp .env.example .env
# Edit .env file with your actual API keys
```

## 🔧 Development Workflow

### Installing New Dependencies

```bash
# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Add a specific version
uv add "package-name>=1.0.0"
```

### Running the Project

```bash
# Activate environment and run Python scripts
uv run python script.py

# Run the main CLI tool
uv run oreilly-langgraph

# Or activate shell and run commands directly
uv shell
python script.py
oreilly-langgraph
```

### Working with Marimo Notebooks

```bash
# Run a Marimo notebook
uv run marimo run marimo-notebooks/1.0-introduction-to-simple-graphs.py

# Edit a Marimo notebook
uv run marimo edit marimo-notebooks/1.0-introduction-to-simple-graphs.py
```

### Development Tools

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Run tests
uv run pytest

# Type checking
uv run mypy src/
```

## 🔑 Environment Variables

Create a `.env` file in the project root with your API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here  # Optional, for web search
LANGSMITH_API_KEY=your_langsmith_key_here  # Optional, for tracing
```

## 📁 Project Structure

```text
oreilly-langgraph/
├── src/oreilly_langgraph/    # Source code package
├── marimo-notebooks/         # Interactive Marimo notebooks
├── notebook/                 # Legacy Jupyter notebooks (reference only)
├── docs/                     # Documentation
├── pyproject.toml           # Project configuration and dependencies
├── uv.lock                  # Locked dependency versions
├── .env                     # Your API keys (not in git)
└── README.md               # Project overview
```

## ❌ What NOT to Use

This project has been fully migrated to uv. **Do not use:**

- `pip install` - Use `uv add` instead
- `conda` - Use `uv` for all package management
- `requirements.txt` - Dependencies are in `pyproject.toml`
- Jupyter notebooks - Use Marimo notebooks instead

## 🔄 Migration Notes

If you're coming from pip/conda:

1. **Dependencies**: All managed in `pyproject.toml`
2. **Virtual environments**: Automatically handled by uv
3. **Package installation**: Use `uv add` instead of `pip install`
4. **Environment activation**: Use `uv shell` or `uv run`
5. **Notebooks**: Migrated to Marimo for better developer experience

## 🆘 Troubleshooting

### Environment Issues

```bash
# Remove and recreate environment
uv sync --reinstall

# Check uv status
uv --version

# List installed packages
uv pip list
```

### Import Errors

```bash
# Ensure you're in the uv environment
uv shell

# Verify package installation
uv pip show package-name

# Sync dependencies
uv sync
```

### API Key Issues

```bash
# Check if .env file exists and has correct format
cat .env

# Test environment loading in Python
uv run python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OPENAI_API_KEY' in os.environ)"
```

## 📚 Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [Marimo Documentation](https://docs.marimo.io/)
- [LangGraph Documentation](https://langraph-ai.github.io/langgraph/)
- [Project README](README.md)
