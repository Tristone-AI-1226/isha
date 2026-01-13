from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
import asyncio
import subprocess
from typing import Optional

# Add root directory to sys.path to import trainer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from trainer import ScraperTrainer
except ImportError:
    # Fallback if running from root or different context
    sys.path.append(os.getcwd())
    from trainer import ScraperTrainer

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StartRequest(BaseModel):
    url: str

class CommandRequest(BaseModel):
    command: str
    args: Optional[str] = ""

trainer_instance: Optional[ScraperTrainer] = None

@app.post("/trainer/start")
async def start_trainer(req: StartRequest):
    global trainer_instance
    if trainer_instance:
        # Ideally close the previous one, but strictly speaking we might want to keep it simple
        pass
    
    trainer_instance = ScraperTrainer(req.url)
    await trainer_instance.initialize_session()
    return {"status": "started", "url": req.url}

@app.post("/trainer/command")
async def run_command(req: CommandRequest):
    global trainer_instance
    if not trainer_instance:
        raise HTTPException(status_code=400, detail="Trainer not started")
    
    try:
        result = await trainer_instance.execute_command(req.command, req.args)
        return {"status": "executed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run/generated_scraper")
async def run_generated_scraper():
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../generated_scraper.py'))
    
    if not os.path.exists(script_path):
         raise HTTPException(status_code=404, detail="generated_scraper.py not found")

    try:
        # Run sync for now to return output
        proc = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        return {
            "status": "finished", 
            "returncode": proc.returncode,
            "stdout": proc.stdout, 
            "stderr": proc.stderr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Allow running directly for testing
    uvicorn.run(app, host="0.0.0.0", port=8000)
