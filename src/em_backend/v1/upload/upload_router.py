import logging

from fastapi import APIRouter, HTTPException, UploadFile

from em_backend.config import langchain_async_clients
from em_backend.upload.upload import upload_documents

router = APIRouter()


@router.post("/uploadfiles")
async def uploadfiles(files: list[UploadFile]) -> None:
    logging.debug("POST request received at /uploadfiles...")

    if not await weaviate_async_client.is_ready():
        raise HTTPException(status_code=503, detail="Weaviate is not ready.")

    errored_files = await upload_documents(
        files, langchain_async_clients, weaviate_async_client
    )

    if len(errored_files) != 0:
        raise HTTPException(
            status_code=500,
            detail=f"File Upload failed for files: {', '.join(errored_files)}",
        )
