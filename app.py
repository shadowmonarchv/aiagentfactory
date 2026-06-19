import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI Application
app = FastAPI(
    title="META Agent Factory - AI Core Engine",
    description="Microservice handling direct LLM generation and orchestration via Groq.",
    version="1.0.0"
)

# Configure CORS Middleware to allow cross-origin communication from frontends/backends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Groq SDK Client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None

if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        print("[ENGINE] Groq Client successfully initialized.")
    except Exception as e:
        print(print(f"[ERROR] Failed to initialize Groq Client: {e}"))
else:
    print("[WARNING] GROQ_API_KEY missing from environment configuration. Chat endpoints will remain offline.")


# Data Validation Schema matching the frontend payload
class ChatRequest(BaseModel):
    agent_name: str
    message: str


@app.get("/")
def health_check():
    """
    Basic service health check verification endpoint.
    """
    return {
        "status": "online",
        "service": "META Agent Factory Engine",
        "llm_provider": "Groq (Llama-3.1-8b-instant)"
    }


@app.post("/v1/agent/chat")
def chat_with_agent(req: ChatRequest):
    """
    Core execution endpoint. Accepts an agent identity and a prompt message,
    then evaluates the response directly against the LLM architecture.
    """
    if not client:
        return {
            "response": "[SYSTEM OFFLINE] Python execution context cannot detect a valid GROQ_API_KEY in the environment."
        }

    try:
        # Execute context injection directly to the target inference model
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": f"You are {req.agent_name}, an expert specialized AI assistant. Provide highly accurate, clean, structured, and direct technical answers fit for an elite agent workflow."
                },
                {
                    "role": "user",
                    "content": req.message
                }
            ],
            temperature=0.6,
            max_tokens=1024
        )

        # Return cleanly parsed inference text back to the platform layer
        return {"response": completion.choices[0].message.content}

    except Exception as e:
        return {
            "response": f"[CRITICAL EXCEPTION] Downstream Groq API Handshake Error: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn

    # Automatically boots up the Uvicorn ASGI server when running the file directly
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)