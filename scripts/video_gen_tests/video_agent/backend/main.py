"""FastAPI backend for the Video Production Agent — port 5322."""

import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Add parent to path so we can import agent
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.producer import VideoAgentConfig, VideoProducerAgent, ProductionResult

OUTPUT_DIR = Path(__file__).parent.parent / "output"

app = FastAPI(title="Video Production Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5321", "http://127.0.0.1:5321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking (hydrated from disk on startup)
jobs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Persistence — load completed jobs from output/ on startup
# ---------------------------------------------------------------------------

def _load_persisted_jobs() -> None:
    """Scan output/ for production_metadata.json files and hydrate the jobs dict."""
    if not OUTPUT_DIR.exists():
        return

    for meta_file in OUTPUT_DIR.glob("*/production_metadata.json"):
        try:
            with open(meta_file) as f:
                meta = json.load(f)

            job_id = meta.get("config", {}).get("project_name", meta_file.parent.name)
            if job_id in jobs:
                continue  # Already loaded (running job)

            # Reconstruct job entry from persisted metadata
            final_outputs = meta.get("final_outputs", [])
            final_video = ""
            final_captioned = ""
            final_music = ""
            for out in final_outputs:
                if "_captioned" in out:
                    final_captioned = out
                elif "_music" in out:
                    final_music = out
                elif "_FINAL" in out:
                    final_video = out

            # Load agent log if available
            log_file = meta_file.parent / "agent_log.jsonl"
            progress_log = []
            if log_file.exists():
                with open(log_file) as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            progress_log.append({
                                "step": entry.get("step", ""),
                                "message": entry.get("message", ""),
                                "level": entry.get("level", ""),
                            })
                        except json.JSONDecodeError:
                            continue

            jobs[job_id] = {
                "job_id": job_id,
                "status": "completed" if not meta.get("error") else "failed",
                "step": "done",
                "message": meta.get("error", "Loaded from disk"),
                "result": {
                    "final_video": final_video,
                    "final_video_captioned": final_captioned,
                    "final_video_music": final_music,
                    "metadata_path": str(meta_file),
                    "sources": meta.get("sources", []),
                    "duration_seconds": meta.get("final_duration_s", 0)
                        or _probe_duration(final_video),
                },
                "progress_log": progress_log,
                "agent": None,
                "config": meta.get("config", {}),
                "persisted": True,
            }
        except Exception as e:
            print(f"  Warning: could not load {meta_file}: {e}")


def _probe_duration(video_path: str) -> float:
    """Get video duration via ffprobe."""
    if not video_path or not Path(video_path).exists():
        return 0.0
    import subprocess
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", video_path],
            capture_output=True, text=True,
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def _persist_job(job_id: str) -> None:
    """Save job state to a job_status.json alongside the production metadata."""
    if job_id not in jobs:
        return
    j = jobs[job_id]
    result = j.get("result")
    if not result or not result.get("metadata_path"):
        return

    status_file = Path(result["metadata_path"]).parent / "job_status.json"
    try:
        with open(status_file, "w") as f:
            json.dump({
                "job_id": j["job_id"],
                "status": j["status"],
                "config": j.get("config", {}),
            }, f, indent=2)
    except Exception:
        pass


@app.on_event("startup")
async def startup():
    print("  Loading previous productions from disk...")
    _load_persisted_jobs()
    print(f"  Loaded {len(jobs)} previous production(s)")


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
        output = self.output_dir or str(OUTPUT_DIR)
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
    status: str
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
    jobs[job_id]["agent"] = agent
    result = await agent.produce()

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
        _persist_job(job_id)
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
            "step": j.get("step", ""),
            "message": j.get("message", ""),
            "topic": j.get("config", {}).get("topic", ""),
        }
        for j in sorted(jobs.values(), key=lambda x: x["job_id"], reverse=True)
    ]


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    # Try in-memory first, then scan disk
    if job_id not in jobs:
        _try_load_single_job(job_id)
    if job_id not in jobs:
        return JobStatus(job_id=job_id, status="not_found", message="Job not found")

    j = jobs[job_id]
    return JobStatus(
        job_id=j["job_id"],
        status=j["status"],
        step=j.get("step", ""),
        message=j.get("message", ""),
        result=j.get("result"),
    )


@app.get("/jobs/{job_id}/metadata")
async def get_metadata(job_id: str):
    if job_id not in jobs:
        _try_load_single_job(job_id)

    j = jobs.get(job_id)
    if not j or not j.get("result"):
        return {"error": "Job not found or not completed"}

    metadata_path = j["result"].get("metadata_path", "")
    if metadata_path and Path(metadata_path).exists():
        with open(metadata_path) as f:
            return json.load(f)
    return {"error": "Metadata file not found"}


@app.get("/jobs/{job_id}/video")
async def get_video(job_id: str, captioned: bool = False):
    if job_id not in jobs:
        _try_load_single_job(job_id)

    j = jobs.get(job_id)
    if not j or not j.get("result"):
        return {"error": "Job not found or not completed"}

    result = j["result"]
    video_path = result.get("final_video_captioned") if captioned else result.get("final_video")

    if video_path and Path(video_path).exists():
        return FileResponse(video_path, media_type="video/mp4")
    return {"error": "Video not found"}


@app.get("/jobs/{job_id}/progress")
async def get_progress(job_id: str):
    if job_id not in jobs:
        _try_load_single_job(job_id)
    if job_id not in jobs:
        return {"error": "Job not found"}

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
    """Return full agent log entries."""
    if job_id not in jobs:
        _try_load_single_job(job_id)
    if job_id not in jobs:
        return {"error": "Job not found"}

    agent = jobs[job_id].get("agent")
    if agent:
        return {"job_id": job_id, "entries": agent.log.entries}

    # Fall back to JSONL file on disk
    j = jobs[job_id]
    result = j.get("result", {})
    meta_path = result.get("metadata_path", "")
    if meta_path:
        log_file = Path(meta_path).parent / "agent_log.jsonl"
        if log_file.exists():
            entries = []
            with open(log_file) as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
            return {"job_id": job_id, "entries": entries}

    return {"job_id": job_id, "entries": j.get("progress_log", [])}


def _try_load_single_job(job_id: str) -> None:
    """Try to load a specific job from disk by job_id (directory name)."""
    meta_file = OUTPUT_DIR / job_id / "production_metadata.json"
    if meta_file.exists():
        _load_persisted_jobs()  # Reload all


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5322)
