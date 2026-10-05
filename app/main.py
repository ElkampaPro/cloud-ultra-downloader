import asyncio
import base64
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .config import BASE_DIR, DOWNLOAD_DIR, SERVER_HOST, SERVER_PORT, get_storage_stats
from .aria2_manager import Aria2Client, start_aria2c_daemon
from .resolvers import hub

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cloud_ultra_downloader")

app = FastAPI(title="Cloud Ultra Downloader", version="1.0.0")

# Mount static folder
static_dir = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

aria2_client = Aria2Client()

# Request Models
class InspectRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    urls: List[str]
    folder: Optional[str] = None

class ControlRequest(BaseModel):
    action: str # pause, unpause, remove, remove_result, clear_stopped
    gid: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    # Attempt to start aria2c if it is installed locally/on colab
    alive = await aria2_client.is_alive()
    if not alive:
        logger.info("Aria2c RPC is not alive yet, attempting to start aria2c daemon...")
        start_aria2c_daemon(DOWNLOAD_DIR)
        await asyncio.sleep(1)

@app.get("/")
async def get_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Cloud Ultra Downloader Backend is Running."}

@app.get("/api/status")
async def get_status():
    alive = await aria2_client.is_alive()
    if not alive:
        return {
            "aria2_alive": False,
            "global_stat": {"downloadSpeed": "0 B/s", "uploadSpeed": "0 B/s", "numActive": 0, "numWaiting": 0, "numStopped": 0},
            "storage": get_storage_stats(),
            "active": [],
            "waiting": [],
            "stopped": []
        }

    try:
        raw_global = await aria2_client.get_global_stat()
        raw_active = await aria2_client.tell_active()
        raw_waiting = await aria2_client.tell_waiting(0, 50)
        raw_stopped = await aria2_client.tell_stopped(0, 50)

        active = [aria2_client.parse_task(t) for t in raw_active]
        waiting = [aria2_client.parse_task(t) for t in raw_waiting]
        stopped = [aria2_client.parse_task(t) for t in raw_stopped]

        down_speed = int(raw_global.get("downloadSpeed", 0))
        from .aria2_manager import format_bytes
        global_stat = {
            "downloadSpeed": f"{format_bytes(down_speed)}/s",
            "downloadSpeedRaw": down_speed,
            "uploadSpeed": f"{format_bytes(int(raw_global.get('uploadSpeed', 0)))}/s",
            "numActive": int(raw_global.get("numActive", 0)),
            "numWaiting": int(raw_global.get("numWaiting", 0)),
            "numStopped": int(raw_global.get("numStopped", 0)),
        }

        return {
            "aria2_alive": True,
            "global_stat": global_stat,
            "storage": get_storage_stats(),
            "active": active,
            "waiting": waiting,
            "stopped": stopped
        }
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return {
            "aria2_alive": False,
            "error": str(e),
            "storage": get_storage_stats(),
            "active": [],
            "waiting": [],
            "stopped": []
        }

@app.get("/api/catalog")
async def get_catalog():
    """Returns available anime series & collections for fast selection."""
    from .resolvers.kiyoshii import CATALOG_ITEMS
    return {"success": True, "catalog": CATALOG_ITEMS}

@app.post("/api/inspect")
async def inspect_url(req: InspectRequest):
    """Inspects a URL to check if it contains multiple files (e.g. Mugisubs, Kiyoshii) or a single download."""
    if not req.url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    try:
        result = await hub.resolve(req.url.strip())
        return {"success": True, **result}
    except Exception as e:
        logger.exception("Failed to inspect URL")
        return {"success": False, "error": str(e)}

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    """Queue one or multiple URLs into aria2c."""
    if not req.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    options = {}
    if req.folder:
        clean_sub = req.folder.strip().strip("/\\")
        dest_dir = os.path.join(DOWNLOAD_DIR, clean_sub)
        os.makedirs(dest_dir, exist_ok=True)
        options["dir"] = dest_dir

    gids = []
    errors = []
    for u in req.urls:
        try:
            # If URL is a web page or index, resolve first
            resolved = await hub.resolve(u)
            for item in resolved.get("items", []):
                item_url = item.get("url")
                if item_url:
                    gid = await aria2_client.add_uri([item_url], options=options)
                    gids.append(gid)
        except Exception as e:
            logger.error(f"Failed to add URL {u}: {e}")
            errors.append(f"{u}: {str(e)}")

    return {"success": len(gids) > 0, "added_count": len(gids), "gids": gids, "errors": errors}

@app.post("/api/upload-torrent")
async def upload_torrent(file: UploadFile = File(...), folder: Optional[str] = Form(None)):
    """Upload and start download from a .torrent file."""
    try:
        content = await file.read()
        b64_content = base64.b64encode(content).decode("utf-8")
        options = {}
        if folder:
            clean_sub = folder.strip().strip("/\\")
            dest_dir = os.path.join(DOWNLOAD_DIR, clean_sub)
            os.makedirs(dest_dir, exist_ok=True)
            options["dir"] = dest_dir

        gid = await aria2_client.add_torrent(b64_content, options=options)
        return {"success": True, "gid": gid, "filename": file.filename}
    except Exception as e:
        logger.error(f"Failed to upload torrent: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/control")
async def control_download(req: ControlRequest):
    """Pause, unpause, remove, or clear tasks."""
    try:
        action = req.action.lower()
        if action == "pause" and req.gid:
            res = await aria2_client.pause(req.gid)
        elif action == "unpause" and req.gid:
            res = await aria2_client.unpause(req.gid)
        elif action == "remove" and req.gid:
            try:
                res = await aria2_client.remove(req.gid)
            except Exception:
                res = await aria2_client.remove_download_result(req.gid)
        elif action == "remove_result" and req.gid:
            res = await aria2_client.remove_download_result(req.gid)
        elif action == "clear_stopped":
            res = await aria2_client.purge_download_result()
        else:
            raise HTTPException(status_code=400, detail="Invalid action or missing GID")
        return {"success": True, "result": res}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time live download statistics push every second."""
    await websocket.accept()
    try:
        while True:
            status_data = await get_status()
            await websocket.send_json(status_data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WebSocket client disconnected: {e}")
