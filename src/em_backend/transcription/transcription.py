from fastapi import UploadFile

from em_backend.config import openai_async_client

async def transcribe(file: UploadFile):
    transcription = await openai_async_client.audio.transcriptions.create(
        model="whisper-1", file=(file.filename, file.file.read())
    )
    return transcription.text