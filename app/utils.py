import subprocess, uuid, shutil
from pathlib import Path
import requests, os, datetime as dt
from dotenv import load_dotenv
load_dotenv()

# Load directories and config from environment
INCOMING = Path(os.getenv("INCOMING_DIR", "incoming"))
CONVERTED = Path(os.getenv("CONVERTED_DIR", "converted"))
N8N_TARGET = os.getenv("N8N_TARGET")
KEEP_DAYS = int(os.getenv("KEEP_DAYS", 30))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

INCOMING.mkdir(exist_ok=True)
CONVERTED.mkdir(exist_ok=True)

def save_raw_file(upload_file) -> Path:
    """Save UploadFile to disk with a random name, return Path."""
    suffix = Path(upload_file.filename or ".bin").suffix or ".bin"
    fname = f"{uuid.uuid4().hex}{suffix}"
    dest = INCOMING / fname
    with dest.open("wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    return dest

def convert_to_wav(src: Path) -> Path:
    """Use ffmpeg to convert arbitrary input → .wav (16-bit PCM)."""
    wav_path = CONVERTED / (src.stem + ".wav")
    cmd = [
        "ffmpeg",
        "-y",            # overwrite
        "-i", str(src),
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_path

def forward_to_n8n(form_fields: dict[str, str], wav_path: Path) -> tuple[int, str]:
    """POST every field + *file_url* to n8n (no file upload)."""
    file_url = f"{PUBLIC_BASE_URL}/audio/{wav_path.name}"

    payload = form_fields.copy()
    payload["file_url"] = file_url  # add the new field 'file_url'

    # No files argument as we are sending the URL instead of the file
    r = requests.post(N8N_TARGET, data=payload, timeout=30)
    return r.status_code, r.text

def cleanup_old_files(folder: Path):
    """Delete files older than KEEP_DAYS in folder."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=KEEP_DAYS)
    for p in folder.iterdir():
        if p.is_file() and dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc) < cutoff:
            try:
                p.unlink()
            except Exception:
                pass
