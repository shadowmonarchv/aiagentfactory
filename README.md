Meta-Agent Factory
A production-ready FastAPI and Pydantic-AI framework powered by Groq to compile, deploy, and chat with customized AI agents. The system builds hyper-targeted agents on the fly, provides them with live web-browsing capabilities, maintains stateful conversational history, and utilizes a robust backend sanitization layer to enforce clean UI rendering.

Features
⚡ Ultra-Fast Agent Compilation: Leverages Groq's hardware acceleration via llama-3.1-8b-instant to generate specialized agent architectures within seconds.

🧠 Stateful Chat Memory: Tracks and feeds multi-turn conversation histories (all_messages()) dynamically back into runner runtimes to solve agent statelessness.

🌐 Live Web Search Integration: Outfits compiled agents with an integrated, zero-token DuckDuckGo live search mechanism (duckduckgo-search) for up-to-the-minute web grounding.

🛡️ Anti-Leak Sanitization Layer: Employs advanced backend regex processing to strip raw model internal query strings or rogue pseudo-XML tags before JSON delivery.

🔄 Resilient Failover Pipeline: Includes a crash-proof local fallback mechanism that automatically shifts operations into an isolated simulation run-state if upstream APIs encounter structural faults.

Tech Stack
Core Runtime: Python 3.10+

AI Framework: Pydantic-AI

LLM Provider: Groq Cloud SDK

API Engine: FastAPI & Uvicorn

Search Utility: DuckDuckGo Search API

Installation & Setup
1. Prerequisites
Ensure you have Python installed on your system. Verify your setup in your terminal:

Bash
python --version
2. Install Dependencies
Run the command below to install the core routing, validation, web scraping, and asynchronous server packages:

Bash
pip install fastapi uvicorn groq duckduckgo-search pydantic-ai pydantic
3. File Structure
Set up your workspace directory to align with the routing endpoints:

Plaintext
The META Agent Builder/
├── app.py          # Backend FastAPI & Agent Architecture
└── index.html      # Frontend Dashboard Interface
4. API Configuration
Open app.py and ensure your live Groq API key is assigned correctly to the credential variable on line 26:

Python
YOUR_API_KEY=
Running the Application
Open your terminal or PowerShell instance inside the project root folder.

Initialize the asynchronous server using the following execution command:

Bash
python app.py
Once the terminal displays INFO: Uvicorn running on http://0.0.0.0:8081, minimize your terminal.

Launch your browser and navigate to:

Plaintext
http://localhost:8081
If re-running after code alterations, execute a hard cache flush using CTRL + F5 to re-sync structural components.

Backend Architecture & API Specs
Agent Compilation
Endpoint: POST /api/v1/factory/compile

Payload: Contains the raw user instructions detailing the target persona.

Mechanism: The compiler_agent evaluates requirements, formats an immutable system structure constraint object, assigns tools (web_search, document_writer), and spins up a dedicated DynamicAgentRunner instance.

Stateful Chat Route
Endpoint: POST /api/v1/agent/chat

Payload: Contains the target active agent name and the latest conversational prompt message.

Mechanism: Loads the runner instance, extracts the past message indices, issues contextually aware tools execution requests, runs text strings through regex scrubbing filters, and records the subsequent message transaction back to memory.
