# O'Reilly Live Training - Getting Started with LangGraph

## Modern Setup with UV (Recommended)

This project uses **UV** for fast, reliable Python package management. UV is a modern replacement for pip/conda that provides:
- ⚡ Extremely fast dependency resolution and installation
- 🔒 Reliable dependency locking with `uv.lock`
- 🐍 Automatic Python version management
- 📦 Modern packaging with `pyproject.toml`

### Prerequisites
- Install [UV](https://docs.astral.sh/uv/getting-started/installation/)
- Python 3.13+ (UV will manage this automatically)

### Quick Start

1. **Clone and Navigate to Project:**
   ```bash
   cd oreilly-langgraph
   ```

2. **Install Dependencies (UV handles everything):**
   ```bash
   uv sync
   ```
   This will:
   - Create a virtual environment in `.venv/`
   - Install Python 3.13 if needed
   - Install all dependencies from `pyproject.toml`

3. **Activate Environment:**
   - **Windows:** `.venv\Scripts\activate`
   - **macOS/Linux:** `source .venv/bin/activate`

4. **Run the Project:**
   ```bash
   uv run oreilly-langgraph
   ```

5. **Start Jupyter Notebooks:**
   ```bash
   uv run jupyter notebook
   ```

### Development Tools Included
- **Ruff** - Fast linting and formatting
- **Black** - Code formatting
- **Pytest** - Testing framework
- **MyPy** - Type checking
- **Jupyter** - Interactive notebooks

### Useful UV Commands
```bash
# Add new dependencies
uv add package-name

# Add development dependencies
uv add --dev package-name

# Run any command in the environment
uv run python script.py
uv run pytest
uv run black .
uv run ruff check .

# Update dependencies
uv sync --upgrade
```

## Environment Variables

- Create a `.env` file in the project root
- Add your API keys:
  ```env
  OPENAI_API_KEY=your_openai_api_key_here
  ANTHROPIC_API_KEY=your_anthropic_api_key_here
  ```
- Get API keys from:
  - [OpenAI Platform](https://platform.openai.com/)
  - [Anthropic Console](https://console.anthropic.com/)

## Project Structure

```
oreilly-langgraph/
├── src/oreilly_langgraph/     # Main Python package
├── notebook/                   # Jupyter notebooks
├── marimo-notebooks/          # Marimo interactive notebooks
├── presentation/              # Course presentation materials
├── pyproject.toml            # Modern Python project configuration
├── uv.lock                   # Dependency lock file
└── README.md                 # This file
```

## Notebooks

Here are the notebooks available in the `notebook/` folder:

1. [Introduction to Simple Graphs](notebook/1.0-introduction-to-simple-graphs.ipynb)
2. [LangGraph State as Messages](notebook/1.1-langgraph-state-as-messages.ipynb)
3. [LangGraph LLM Patterns](notebook/1.2-langgraph-llm-patterns.ipynb)
4. [LangGraph Using Tools](notebook/1.3-langgraph-using-tools.ipynb)
5. [Basic React Agent](notebook/2.0-basic-react-agent.ipynb)
6. [Basic React Agent with Memory](notebook/2.1-basic-react-agent-with-memory.ipynb)
7. [Basic RAG Agent](notebook/3.0-basic-rag-agent.ipynb)
8. [Local Agent with LLaMA3.2](notebook/4.0-local-agent-llama32.ipynb)
9. [LangGraph Studio](notebook/5.0-langgraph-studio.ipynb)

## Legacy Setup Methods

<details>
<summary>Click to expand legacy setup instructions (Conda/Pip)</summary>

**Conda**

- Install [anaconda](https://www.anaconda.com/download)
- Create an environment: `conda create -n oreilly-langgraph python=3.11`
- Activate your environment with: `conda activate oreilly-langgraph`
- Install requirements with: `pip install -r requirements/requirements.txt`

**Pip**

1. **Create a Virtual Environment:**
    ```bash
    python -m venv oreilly-langgraph
    ```

2. **Activate the Virtual Environment:**
    - **On Windows:** `.\oreilly-langgraph\Scripts\activate`
    - **On macOS and Linux:** `source oreilly-langgraph/bin/activate`

3. **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

</details>

---

## Dependencies

### Core Dependencies
- **LangGraph** >= 0.4.10 - Graph-based LLM applications
- **LangChain** >= 0.3.0 - LLM application framework
- **OpenAI** >= 1.0.0 - OpenAI API client
- **Anthropic** >= 0.35.0 - Anthropic API client
- **Jupyter** >= 1.0.0 - Interactive notebooks
- **Marimo** >= 0.14.7 - Modern reactive notebooks
- **Quarto** >= 0.1.0 - Publishing system

### Development Dependencies
- **Ruff** - Fast Python linter and formatter
- **Black** - Python code formatter
- **Pytest** - Testing framework
- **MyPy** - Static type checker
- **isort** - Import sorter

Ready to build AI agents with LangGraph! 🚀
