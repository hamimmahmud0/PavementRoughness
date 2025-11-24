from fastapi import FastAPI, UploadFile, File
import os
from datetime import datetime

app = FastAPI()

UPLOAD_DIR = "/data/uploads"   # persistent disk
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def home():
    return {"message": "CSV Upload API Running"}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        return {"error": "Only CSV files allowed"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(await file.read())

    return {"status": "saved", "filename": filename}

