import re
import logging
import base64  # 🛠️ NEW: Built-in library to safely handle image math
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ollama

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [AI STREAM] - %(message)s")

app = FastAPI(title="METAfactory Core Engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])


class ChatRequest(BaseModel):
    agent_name: str
    message: str
    image_base64: Optional[str] = None
    history: List[Dict[str, Any]] = []


@app.post("/v1/agent/chat")
def chat_with_agent(req: ChatRequest):
    try:
        system_instruction = (
            f"You are {req.agent_name}, an elite expert AI. "
            "Provide clear, concise, and highly structured answers using Markdown. "
            "Keep responses brief and direct unless explicitly asked for deep detail."
        )
        flow = [{"role": "system", "content": system_instruction}]

        for msg in req.history:
            flow.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        user_msg = {"role": "user", "content": req.message if req.message else "Analyze the provided visual data."}

        # Default to the ultra-fast text model
        target_model = 'llama3.2:1b'

        if req.image_base64:
            logging.info(f"Visual payload detected. Switching engine to 'moondream'...")
            target_model = 'moondream'

            # 🛠️ THE FIX: Safely parse, pad, and decode the image
            b64_data = re.sub(r'^data:image/.+;base64,', '', req.image_base64)

            # 1. Add missing mathematical padding (browsers often strip this)
            b64_data += "=" * ((4 - len(b64_data) % 4) % 4)

            # 2. Decode to raw bytes so Ollama never mistakes it for a broken file path
            image_bytes = base64.b64decode(b64_data)

            user_msg["images"] = [image_bytes]
        else:
            logging.info(f"Text-only payload. Using fast engine '{target_model}' for agent: {req.agent_name}")

        flow.append(user_msg)

        def token_generator():
            response_stream = ollama.chat(model=target_model, messages=flow, stream=True)
            for chunk in response_stream:
                text_chunk = chunk['message']['content']
                yield text_chunk

        return StreamingResponse(token_generator(), media_type="text/plain")

    except Exception as e:
        logging.error(f"Streaming Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, timeout_keep_alive=300)
