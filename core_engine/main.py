import os
import uuid
import shutil
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="VeriAgent Core Engine", version="0.1.0")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str
    saved_path: str

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "core_engine"}

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    [CORE-004] Uploads a file (PDF/Image) to the ingestion queue.
    Returns a unique file ID for processing.
    """
    try:
        # Generate unique ID
        file_id = str(uuid.uuid4())
        extension = os.path.splitext(file.filename)[1]
        safe_filename = f"{file_id}{extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            saved_path=file_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
