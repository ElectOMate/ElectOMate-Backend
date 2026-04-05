"""FastAPI backend for the Video Production Agent — port 5322."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Add parent to path so we can import agent
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.producer import VideoAgentConfig, VideoProducerAgent, ProductionResult

app = FastAPI(title="Video Production Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5321", "http://127.0.0.1:5321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking
jobs: dict[str, dict] = {}


# --- Schemas ---

class ProductionRequest(BaseModel):
    topic: str = "Democracy in Hungary"
    language: str = "English"
    tone: str = "serious"
    duration_seconds: int = 60
    num_perspectives: int = 3
    orientation: str = "landscape"
    resolution: str = "720p"
    character_description: str = ""
    character_gender: str = "male"
    character_age: str = "40"
    search_sources: list[str] = Field(default=["web"])
    manifesto_dir: str = ""
    background_music_path: str = ""
    music_volume: float = 0.12
    generate_captions: bool = True
    output_dir: str = Field(default="")

    def to_config(self) -> VideoAgentConfig:
        output = self.output_dir or str(
            Path(__file__).parent.parent / "output"
        )
        return VideoAgentConfig(
            topic=self.topic,
            language=self.language,
            tone=self.tone,
            duration_seconds=self.duration_seconds,
            num_perspectives=self.num_perspectives,
            orientation=self.orientation,
            resolution=self.resolution,
            character_description=self.character_description,
            character_gender=self.character_gender,
            character_age=self.character_age,
            search_sources=self.search_sources,
            manifesto_dir=self.manifesto_dir,
            background_music_path=self.background_music_path,
            music_volume=self.music_volume,
            generate_captions=self.generate_captions,
            output_dir=output,
        )


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending | running | completed | failed
    step: str = ""
    message: str = ""
    result: Optional[dict] = None


# --- Background production task ---

async def run_production_job(job_id: str, config: VideoAgentConfig):
    def progress_cb(step: str, msg: str):
        jobs[job_id]["status"] = "running"
        jobs[job_id]["step"] = step
        jobs[job_id]["message"] = msg

    agent = VideoProducerAgent(config, progress_callback=progress_cb)
    jobs[job_id]["agent"] = agent  # Keep reference for log access
    result = await agent.produce()

    # Store the full agent log in the job
    jobs[job_id]["progress_log"] = agent.log.get_progress_list()

    if result.success:
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "final_video": result.final_video,
            "final_video_captioned": result.final_video_captioned,
            "final_video_music": result.final_video_music,
            "metadata_path": result.metadata_path,
            "sources": result.sources,
            "duration_seconds": result.duration_seconds,
        }
    else:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = result.error


# --- Routes ---

@app.get("/")
async def root():
    return {"service": "Video Production Agent", "version": "1.0.0"}


@app.post("/produce", response_model=JobStatus)
async def start_production(req: ProductionRequest, background_tasks: BackgroundTasks):
    config = req.to_config()
    job_id = config.project_name

    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "step": "",
        "message": "Queued",
        "result": None,
        "progress_log": [],
        "agent": None,
        "config": req.model_dump(),
    }

    background_tasks.add_task(run_production_job, job_id, config)

    return JobStatus(job_id=job_id, status="pending", message="Production queued")


@app.get("/jobs")
async def list_jobs():
    return [
        {
            "job_id": j["job_id"],
            "status": j["status"],
            "step": j["step"],
            "message": j["message"],
        }
        for j in jobs.values()
    ]


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    if job_id not in jobs:
        return JobStatus(job_id=job_id, status="not_found", message="Job not found")
    j = jobs[job_id]
    return JobStatus(
        job_id=j["job_id"],
        status=j["status"],
        step=j["step"],
        message=j["message"],
        result=j.get("result"),
    )


@app.get("/jobs/{job_id}/metadata")
async def get_metadata(job_id: str):
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        return {"error": "Job not found or not completed"}

    metadata_path = jobs[job_id]["result"]["metadata_path"]
    if Path(metadata_path).exists():
        with open(metadata_path) as f:
            return json.load(f)
    return {"error": "Metadata file not found"}


@app.get("/jobs/{job_id}/video")
async def get_video(job_id: str, captioned: bool = False):
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        return {"error": "Job not found or not completed"}

    result = jobs[job_id]["result"]
    video_path = result.get("final_video_captioned") if captioned else result.get("final_video")

    if video_path and Path(video_path).exists():
        return FileResponse(video_path, media_type="video/mp4")
    return {"error": "Video not found"}


@app.get("/jobs/{job_id}/progress")
async def get_progress(job_id: str):
    if job_id not in jobs:
        return {"error": "Job not found"}

    # Pull live log from agent if still running
    agent = jobs[job_id].get("agent")
    if agent:
        progress = agent.log.get_progress_list()
    else:
        progress = jobs[job_id].get("progress_log", [])

    return {
        "job_id": job_id,
        "status": jobs[job_id]["status"],
        "progress_log": progress,
    }


@app.get("/jobs/{job_id}/log")
async def get_full_log(job_id: str):
    """Return the full agent log (all entries including tool calls and data)."""
    if job_id not in jobs:
        return {"error": "Job not found"}

    agent = jobs[job_id].get("agent")
    if agent:
        return {"job_id": job_id, "entries": agent.log.entries}
    return {"job_id": job_id, "entries": jobs[job_id].get("progress_log", [])}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5322)
