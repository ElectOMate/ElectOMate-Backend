from fastapi import APIRouter, UploadFile, HTTPException

from em_backend.config import weaviate_async_client, cohere_async_clients
from em_backend.upload.upload import upload_documents

import logging

router = APIRouter()

@router.post("/uploadfiles")
async def uploadfiles(files: list[UploadFile]):
    logging.debug("POST request received at /uploadfiles...")

    if not await weaviate_async_client.is_ready():
        raise HTTPException(status_code=503, detail="Weaviate is not ready.")

    errored_files = await upload_documents(
        files, cohere_async_clients, weaviate_async_client
    )

    if len(errored_files) != 0:
        return HTTPException(
            status_code=500,
            detail=f"File Upload failed for files: {", ".join(errored_files)}",
        )