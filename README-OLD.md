# O'Reilly Live Trainining - Getting Started with LangGraph

## Setup

**Conda**

- Install [anaconda](https://www.anaconda.com/download)
- This repo was tested on a Mac with python=3.11.
- Create an environment: `conda create -n oreilly-langgraph python=3.11`
- Activate your environment with: `conda activate oreilly-langgraph`
- Install requirements with: `pip install -r requirements/requirements.txt`
- Setup your openai [API key](https://platform.openai.com/)

**Pip**


1. **Create a Virtual Environment:**
    Navigate to your project directory. Make sure you have python 3.11 installed! 
    If using Python 3's built-in `venv`:
    ```bash
    python -m venv oreilly-langgraph
    ```
    If you're using `virtualenv`:
    ```bash
    virtualenv oreilly-langgraph
    ```

2. **Activate the Virtual Environment:**
    - **On Windows:**
      ```bash
      .\oreilly-langgraph\Scripts\activate
      ```
    - **On macOS and Linux:**
      ```bash
      source oreilly-langgraph/bin/activate
      ```

3. **Install Dependencies from `requirements.txt`:**
    ```bash
    pip install python-dotenv
    pip install -r requirements.txt
    ```

4. Setup your openai [API key](https://platform.openai.com/)

Remember to deactivate the virtual environment once you're done by simply typing:
```bash
deactivate
```

## Setup your .env file

- Change the `.env.example` file to `.env` and add your OpenAI API key.

## To use this Environment with Jupyter Notebooks:

- ```pip install jupyter```
- ```python3 -m ipykernel install --user --name=oreilly-langgraph```


## Notebooks

Here are the notebooks available in the `notebooks/` folder:

1. [Simple Graph in LangGraph](notebooks/1.0-introduction-to-simple-graphs.ipynb)
   
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/EnkrateiaLucca/oreilly-langgraph/blob/main/notebooks/1.0-introduction-to-simple-graphs.ipynb)

2. [LLM Tool Call Assistant](notebooks/1.1-llm-tool-call-assistant.ipynb)
   
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/EnkrateiaLucca/oreilly-langgraph/blob/main/notebooks/1.1-llm-tool-call-assistant.ipynb)

3. [Basic Assistant with Memory](notebooks/1.2-basic-assistant-with-memory.ipynb)
   
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/EnkrateiaLucca/oreilly-langgraph/blob/main/notebooks/1.2-basic-assistant-with-memory.ipynb)

4. [LangGraph Studio](notebooks/2.0-langgraph-studio.ipynb)
   
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/EnkrateiaLucca/oreilly-langgraph/blob/main/notebooks/2.0-langgraph-studio.ipynb)

5. [Basic RAG Agent](notebooks/3.0-basic-rag-agent.ipynb)
   
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/EnkrateiaLucca/oreilly-langgraph/blob/main/notebooks/3.0-basic-rag-agent.ipynb)

6. [Local Agent with LLaMA3.2](notebooks/4.0-local-agent-llama32.ipynb)
   
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/EnkrateiaLucca/oreilly-langgraph/blob/main/notebooks/4.0-local-agent-llama32.ipynb)