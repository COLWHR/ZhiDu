from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
from datetime import datetime
import shutil

router = APIRouter()

# Define upload directory
UPLOAD_DIR = "uploads"

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload/image")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Generate file URL
        file_url = f"/uploads/{filename}"
        
        return JSONResponse(content={"url": file_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail="File upload failed")
