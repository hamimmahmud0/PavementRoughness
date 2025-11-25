from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import tempfile
import time
import requests
import json

app = FastAPI()

# Temp local directory
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_AGE = 2 * 60 * 60  # 2 hours

# Dropbox token stored in Render environment variables
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")


def upload_to_dropbox(local_path: str, dropbox_path: str):
    """Upload file from local storage to Dropbox."""
    if DROPBOX_TOKEN is None:
        raise HTTPException(status_code=500, detail="DROPBOX_TOKEN not configured")

    headers = {
        "Authorization": f"Bearer {DROPBOX_TOKEN}",
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": json.dumps({
            "path": dropbox_path,
            "mode": "overwrite",
            "autorename": False,
            "mute": False
        })
    }

    with open(local_path, "rb") as f:
        data = f.read()

    res = requests.post(
        "https://content.dropboxapi.com/2/files/upload",
        headers=headers,
        data=data
    )

    if res.status_code != 200:
        print(res.json())
        raise HTTPException(status_code=500, detail=f"Dropbox error: {res.text}")

    
    return res.json()


def cleanup_old_files():
    now = time.time()
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            if now - os.path.getmtime(file_path) > MAX_FILE_AGE:
                os.remove(file_path)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    cleanup_old_files()

    # Save locally
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Upload automatically to Dropbox
    dropbox_result = upload_to_dropbox(
        local_path=file_path,
        dropbox_path=f"/{file.filename}"
    )

    return {
        "filename": file.filename,
        "status": "uploaded and saved to Dropbox",
        "dropbox_info": dropbox_result
    }


@app.get("/download/{filename}")
def download_file(filename: str):
    cleanup_old_files()

    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="text/csv", filename=filename)


@app.get("/files")
def list_files():
    cleanup_old_files()

    files = [
        f for f in os.listdir(UPLOAD_DIR)
        if os.path.isfile(os.path.join(UPLOAD_DIR, f)) and f.endswith(".csv")
    ]
    return {"files": files}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}
