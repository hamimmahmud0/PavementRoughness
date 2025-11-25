from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import FileResponse
import os
import tempfile
import time

app = FastAPI()

# Temporary upload directory
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Max file age in seconds (7 days)
MAX_FILE_AGE = 7 * 24 * 60 * 60

# Load token from environment variables
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")


def verify_token(token: str):
    if ACCESS_TOKEN is None:
        raise HTTPException(status_code=500, detail="Access token not configured")
    if token != f"Bearer {ACCESS_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def cleanup_old_files():
    """Delete files older than 7 days."""
    now = time.time()
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            age = now - os.path.getmtime(file_path)
            if age > MAX_FILE_AGE:
                os.remove(file_path)


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    authorization: str = Header(default=None)
):
    verify_token(authorization)
    cleanup_old_files()

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"filename": file.filename, "status": "uploaded"}


@app.get("/download/{filename}")
def download_file(
    filename: str,
    authorization: str = Header(default=None)
):
    verify_token(authorization)
    cleanup_old_files()

    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename
    )


@app.get("/files")
def list_files(authorization: str = Header(default=None)):
    verify_token(authorization)
    cleanup_old_files()

    files = [
        f for f in os.listdir(UPLOAD_DIR)
        if os.path.isfile(os.path.join(UPLOAD_DIR, f)) and f.endswith(".csv")
    ]
    return {"files": files}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}
