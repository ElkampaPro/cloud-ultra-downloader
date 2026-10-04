import os
import shutil
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent

# Detect if running in Google Colab
IS_COLAB = os.path.exists("/content") and os.path.exists("/content/drive")

# Download directory (Google Drive if available, else local downloads folder)
DEFAULT_DOWNLOAD_DIR = "/content/drive/MyDrive/Downloads" if os.path.exists("/content/drive") else str(BASE_DIR / "downloads")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR)

# Ensure download directory exists
try:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
except Exception:
    pass

# Aria2 RPC Configuration
ARIA2_RPC_HOST = os.getenv("ARIA2_RPC_HOST", "http://127.0.0.1:6800/jsonrpc")
ARIA2_RPC_SECRET = os.getenv("ARIA2_RPC_SECRET", "")
ARIA2_PORT = int(os.getenv("ARIA2_PORT", "6800"))

# Server Configuration
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "8000"))

def get_storage_stats():
    """Returns total and free disk space in human-readable format for the download directory."""
    check_path = DOWNLOAD_DIR
    if not os.path.exists(check_path):
        check_path = "/"
    try:
        total, used, free = shutil.disk_usage(check_path)
        def format_size(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_val < 1024.0:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024.0
            return f"{bytes_val:.1f} PB"

        return {
            "total": format_size(total),
            "free": format_size(free),
            "used": format_size(used),
            "percent_used": round((used / total) * 100, 1),
            "path": DOWNLOAD_DIR,
            "is_drive": "/content/drive" in DOWNLOAD_DIR
        }
    except Exception:
        return {
            "total": "Unknown",
            "free": "Unknown",
            "used": "Unknown",
            "percent_used": 0,
            "path": DOWNLOAD_DIR,
            "is_drive": False
        }
