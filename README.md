# blog-agentic-ai

## Overview

This repository provides a multi-agent, **LangGraph** observability application that integrates with **Memgraph**
for data ingestion, semantic search, and signal observability. 
A Panel-based UI (`app/app.py`) is included for interacting with the agents.

## Prerequisites

1. **Python** >= 3.10
2. **Memgraph**

## Environment Setup

1. **Clone** this repository.
2. **Install** dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set** environment variables or a `.env` file with:
   ```bash
   export MEMGRAPH_URI="bolt://localhost:7687"
   export MEMGRAPH_USER="memgraphUser"
   export MEMGRAPH_PASSWORD="MemgraphPassword1233"
   export OPENAI_API_KEY=""
   export MODEL_PROVIDER="local || openai"
   ```
4. Run Llama 3.1 8B locally (Optional):
   - Setup Llama 3.1 using ollama
   ```bash
   brew install ollama
   ollama pull llama3.1:8b-instruct-fp16
   ollama pull nomic-embed-text
   ```

## Data Ingestion

1. Run the **graph_ingest** script to load them into Memgraph, including vector indexing and embeddings:
   ```bash
   python -m scripts.graph_ingest
   ```
2. Verify the data is loaded. You can open Memgraph in the browser or run queries to check the nodes and edges.

## Starting the App

1. **Launch** the UI by running:
   ```bash
   python -m copilot.app
   ```
   This starts a Panel server in `app.py`.
2. **Interact** with the agents:
   - Provide your user prompt
   - The system automatically references `org_id`, `role_id`, `user_id`, `conversation_id` from the application or session
   - The multi-agent system chooses which agent/tool to call
   - The application displays the final response

## Architecture

- **LangGraph** orchestrates multi-agent workflows with **ReAct**-style agents.
- Each agent forcibly reads guard rails (`org_id`, etc.) from a `config["configurable"]`.
- **Memgraph** provides adjacency-based queries and local vector indexes for semantic search.
- The UI is powered by **Panel** (`pn.template.*`) and **Holoviews**.

---
