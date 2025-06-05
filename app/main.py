from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging, traceback
from dotenv import load_dotenv; load_dotenv()
import os
from pathlib import Path    # <-- Add this import
from fastapi.staticfiles import StaticFiles

# Load configuration from .env file
INCOMING = Path(os.getenv("INCOMING_DIR", "incoming"))
CONVERTED = Path(os.getenv("CONVERTED_DIR", "converted"))
N8N_TARGET = os.getenv("N8N_TARGET")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

# Initialize FastAPI app before mounting static files
app = FastAPI(title="Audio Gateway")

# Mount the /audio path to serve files from the converted directory (make sure this comes before app instantiation)
app.mount("/audio", StaticFiles(directory=CONVERTED), name="audio")

from .utils import save_raw_file, convert_to_wav, forward_to_n8n
from .cleanup import start_cleanup

# kick off the daily deletion job when the server starts
start_cleanup(os.getenv("CLEANUP_CRON", "0 2 * * *"))

@app.post("/upload", status_code=202)
async def upload_endpoint(
    request: Request,
    file: UploadFile = File(...),               # raw .bin
):
    try:
        # 1) grab ALL other form fields dynamically
        form = await request.form()
        form_fields: Dict[str, Any] = {k: v for k, v in form.items() if k != "file"}

        # 2) save & convert
        raw_path = save_raw_file(file)
        wav_path = convert_to_wav(raw_path)

        # 3) forward
        code, body = forward_to_n8n(form_fields, wav_path)

        return JSONResponse(
            {"status": "forwarded", "n8n_status": code, "n8n_body": body},
            status_code=202 if 200 <= code < 300 else 502,
        )

    except Exception as e:
        logging.error(traceback.format_exc())
        return JSONResponse({"error": str(e)}, status_code=500)
