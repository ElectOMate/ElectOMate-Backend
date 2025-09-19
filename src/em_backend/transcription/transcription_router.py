from fastapi import UploadFile, HTTPException, APIRouter
from fastapi.responses import JSONResponse

from em_backend.transcription.transcription import transcribe


router = APIRouter()


@router.post("/upload-audio-webm")
async def upload_audio_webm(file: UploadFile):
    if file.content_type not in ["audio/webm", "video/webm"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Must be 'audio/webm' or 'video/webm'.",
        )

    transcription = await transcribe(file)

    # 5) Return transcription text to the front-end
    return JSONResponse(
        content={
            "message": "Audio converted to MP3 and transcribed successfully!",
            "transcription": transcription,
        }
    )