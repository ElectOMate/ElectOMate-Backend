
import os
import subprocess
from fastapi import File, UploadFile, HTTPException, APIRouter
from fastapi.responses import JSONResponse

# Whisper / OpenAI imports
from dotenv import load_dotenv
from openai import OpenAI

router = APIRouter()

# 1) Load environment variables (OPENAI_API_KEY, etc.)
load_dotenv()  
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/upload-audio-webm")
async def upload_audio_webm(file: UploadFile = File(...)):
    """
    1) Accept an uploaded .webm file
    2) Convert it to .mp3 with system-installed ffmpeg
    3) Send the .mp3 to OpenAI's Whisper for transcription
    4) Return the transcription text
    """

    if file.content_type not in ["audio/webm", "video/webm"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Must be 'audio/webm' or 'video/webm'."
        )

    # Temporary filenames
    input_filename = "temp_input.webm"
    output_filename = "temp_output.mp3"

    # 1) Write the incoming .webm file to disk
    with open(input_filename, "wb") as f:
        f.write(await file.read())

    try:
        # 2) Convert .webm → .mp3 using ffmpeg
        subprocess.run(
            [
                "ffmpeg", 
                "-y", 
                "-i", input_filename,  # input
                "-b:a", "128k",        # audio bitrate
                output_filename        # output
            ],
            check=True,
        )

        # 3) (Optional) remove the .webm if not needed
        os.remove(input_filename)

        # 4) Transcribe the .mp3 with Whisper via OpenAI
        with open(output_filename, "rb") as mp3_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=mp3_file
            )
        print(transcription)
        transcribed_text = transcription.text

        # (Optional) remove the .mp3 after transcription if you like
        # os.remove(output_filename)

        # 5) Return transcription text to the front-end
        return JSONResponse(content={
            "message": "Audio converted to MP3 and transcribed successfully!",
            "transcription": transcribed_text
        })

    except subprocess.CalledProcessError as e:
        # ffmpeg command failed
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e}")
    except Exception as e:
        # Whisper or other errors
        raise HTTPException(status_code=500, detail=str(e))