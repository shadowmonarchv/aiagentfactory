import os
import sys
import subprocess
import re
from typing import List

# ==========================================
# 0. AUTO-INSTALLER
# ==========================================
try:
    import groq
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "groq", "-q"])

try:
    from duckduckgo_search import DDGS
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "duckduckgo-search", "-q"])

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import uvicorn
import os
from dotenv import load_dotenv

# ==========================================
# 1. CREDENTIALS
# ==========================================
load_dotenv()

YOUR_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI(title="Meta-Agent Factory", version="1.0")


# ==========================================
# 2. SCHEMA & TOOLS
# ==========================================
class AgentBlueprint(BaseModel):
    agent_name: str = Field(description="A distinct, single-word name for the Agent.")
    description: str = Field(description="A short summary of what the agent does.")
    system_prompt: str = Field(description="Detailed instructions written in the second person.")
    required_tools: List[str] = Field(description="List of required tools chosen ONLY from the available registry.")


def web_search(query: str) -> str:
    """Searches the live internet for up-to-date information."""
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No web results found."

        compiled_results = "\n\n".join([f"Source: {res['title']}\nSnippet: {res['body']}" for res in results])
        return f"[LIVE WEB RESULTS FOR '{query}']:\n{compiled_results}"
    except Exception as e:
        return f"Web search failed: {str(e)}"


def document_writer(content: str, filename: str) -> str:
    return f"[MOCK FILE SYSTEM] Successfully saved document to '{filename}.md'."


TOOL_REGISTRY = {
    "web_search": web_search,
    "document_writer": document_writer
}

# ==========================================
# 3. AGENT DEFINITIONS & MEMORY
# ==========================================
compiler_agent = Agent(
    "groq:llama-3.1-8b-instant",
    output_type=AgentBlueprint,
    system_prompt="""
    Analyze the user's request. 
    Extract the user's requirements and output a structured AgentBlueprint. 
    You must instruct the generated agent to act like a 20-year veteran in its field. It must speak with absolute authority, use professional jargon correctly, and synthesize information clearly without sounding like a robotic AI.
    Select applicable tools from this list ONLY: [web_search, document_writer]. If the agent needs to answer questions, ALWAYS give it the web_search tool.
    """
)


class DynamicAgentRunner:
    def __init__(self, blueprint: AgentBlueprint):
        self.blueprint = blueprint

        # --- NEW: INITIALIZE THE MEMORY BANK ---
        self.chat_history = []

        veteran_prompt = (
                self.blueprint.system_prompt +
                "\n\nCRITICAL DIRECTIVE: You are a veteran expert. If asked a question, use the web_search tool "
                "to gather facts, then synthesize those facts into a masterclass explanation. "
                "DO NOT under any circumstances output raw XML tags, bracketed tool names, text-based search queries, "
                "or characters like '<' and '>' to show your thought process. Only output your final, beautifully "
                "formatted paragraph responses."
        )

        self.agent = Agent(
            "groq:llama-3.1-8b-instant",
            system_prompt=veteran_prompt
        )
        for tool_name in self.blueprint.required_tools:
            if tool_name in TOOL_REGISTRY:
                self.agent.tool_plain(TOOL_REGISTRY[tool_name])

    def run(self, prompt: str) -> str:
        # --- NEW: PASS HISTORY IN AND SAVE UPDATED HISTORY OUT ---
        result = self.agent.run_sync(prompt, message_history=self.chat_history)

        if hasattr(result, 'all_messages'):
            self.chat_history = result.all_messages()

        # Safely extract text depending on the pydantic-ai version
        return getattr(result, 'data', getattr(result, 'output', str(result)))


class MockRunner:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.chat_history = []

    def run(self, prompt: str) -> str:
        return f"[LOCAL SIMULATION] Directive received: '{prompt}'. (Invalid API key or network block)."


# ==========================================
# 4. FASTAPI ROUTES
# ==========================================
DEPLOYED_AGENTS = {}


class CompileRequest(BaseModel):
    transcript: str


class ChatRequest(BaseModel):
    agent_name: str
    message: str


@app.post("/api/v1/factory/compile")
def compile_agent(request: CompileRequest):
    try:
        result = compiler_agent.run_sync(request.transcript)

        # Safely extract blueprint depending on the pydantic-ai version
        blueprint = getattr(result, 'data', getattr(result, 'output', None))

        runner = DynamicAgentRunner(blueprint)
        DEPLOYED_AGENTS[blueprint.agent_name] = runner
        return {"status": "success", "blueprint": blueprint.model_dump()}
    except Exception as e:
        print(f"\n[WARNING] API connection failed: {str(e)}")
        fallback_blueprint = AgentBlueprint(
            agent_name="Sim_Agent_01",
            description="Operating in Local Simulation Mode.",
            system_prompt="You are a simulated offline agent.",
            required_tools=["document_writer"]
        )
        DEPLOYED_AGENTS[fallback_blueprint.agent_name] = MockRunner(fallback_blueprint.agent_name)
        return {"status": "success", "blueprint": fallback_blueprint.model_dump()}


@app.post("/api/v1/agent/chat")
def chat_with_agent(request: ChatRequest):
    if request.agent_name not in DEPLOYED_AGENTS:
        raise HTTPException(status_code=404, detail="Agent not found in memory.")
    try:
        runner = DEPLOYED_AGENTS[request.agent_name]
        response_text = runner.run(request.message)

        # ANTI-LEAK SANITIZATION LAYER
        sanitized_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', response_text, flags=re.DOTALL)
        sanitized_text = re.sub(r'<[^>]+>', '', sanitized_text)

        return {"response": sanitized_text.strip()}

    except Exception as e:
        return {"response": f"[LOCAL OVERRIDE] Agent encountered an upstream error: {str(e)}"}


# ==========================================
# 5. SERVE FRONTEND
# ==========================================
@app.get("/")
def serve_ui():
    return FileResponse("index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
