import asyncio
import aiohttp
import json
import logging
import os
import subprocess
import shutil
from typing import List, Dict, Any, Optional
from .config import ARIA2_RPC_HOST, ARIA2_RPC_SECRET, ARIA2_PORT, DOWNLOAD_DIR

logger = logging.getLogger("aria2_manager")

def format_bytes(bytes_val: int) -> str:
    """Format bytes into human-readable size."""
    if not bytes_val or bytes_val < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def format_eta(seconds: int) -> str:
    """Format ETA in seconds into human-readable string."""
    if not seconds or seconds <= 0:
        return "--"
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m = seconds // 60
        s = seconds % 60
        return f"{m}m {s}s"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"

class Aria2Client:
    def __init__(self, rpc_url: str = ARIA2_RPC_HOST, secret: str = ARIA2_RPC_SECRET):
        self.rpc_url = rpc_url
        self.secret = secret

    async def _call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        if params is None:
            params = []
        if self.secret:
            params.insert(0, f"token:{self.secret}")

        payload = {
            "jsonrpc": "2.0",
            "id": "cloud-downloader",
            "method": method,
            "params": params
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    data = await resp.json()
                    if "error" in data:
                        raise RuntimeError(f"Aria2 RPC Error: {data['error'].get('message', 'Unknown error')}")
                    return data.get("result")
        except aiohttp.ClientConnectorError:
            raise RuntimeError("Cannot connect to aria2c RPC. Is aria2c running?")
        except asyncio.TimeoutError:
            raise RuntimeError("Aria2 RPC request timed out.")

    async def is_alive(self) -> bool:
        try:
            res = await self._call("aria2.getVersion")
            return res is not None
        except Exception:
            return False

    async def add_uri(self, uris: List[str], options: Optional[Dict[str, Any]] = None) -> str:
        """Add one or more URIs to aria2."""
        opts = {
            "dir": DOWNLOAD_DIR,
            "max-connection-per-server": "16",
            "split": "16",
            "min-split-size": "1M",
            "continue": "true"
        }
        if options:
            opts.update(options)
        return await self._call("aria2.addUri", [uris, opts])

    async def add_torrent(self, torrent_base64: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Add a torrent file encoded in base64."""
        opts = {
            "dir": DOWNLOAD_DIR,
            "max-connection-per-server": "16",
            "split": "16",
            "min-split-size": "1M",
            "continue": "true"
        }
        if options:
            opts.update(options)
        return await self._call("aria2.addTorrent", [torrent_base64, [], opts])

    async def tell_active(self) -> List[Dict[str, Any]]:
        return await self._call("aria2.tellActive") or []

    async def tell_waiting(self, offset: int = 0, num: int = 50) -> List[Dict[str, Any]]:
        return await self._call("aria2.tellWaiting", [offset, num]) or []

    async def tell_stopped(self, offset: int = 0, num: int = 50) -> List[Dict[str, Any]]:
        return await self._call("aria2.tellStopped", [offset, num]) or []

    async def get_global_stat(self) -> Dict[str, Any]:
        return await self._call("aria2.getGlobalStat") or {}

    async def pause(self, gid: str) -> str:
        return await self._call("aria2.pause", [gid])

    async def unpause(self, gid: str) -> str:
        return await self._call("aria2.unpause", [gid])

    async def remove(self, gid: str) -> str:
        return await self._call("aria2.remove", [gid])

    async def remove_download_result(self, gid: str) -> str:
        return await self._call("aria2.removeDownloadResult", [gid])

    async def purge_download_result(self) -> str:
        return await self._call("aria2.purgeDownloadResult")

    def parse_task(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert aria2 raw status into UI-friendly structure."""
        gid = raw.get("gid", "")
        status = raw.get("status", "unknown")
        total_length = int(raw.get("totalLength", 0))
        completed_length = int(raw.get("completedLength", 0))
        download_speed = int(raw.get("downloadSpeed", 0))
        upload_speed = int(raw.get("uploadSpeed", 0))
        connections = int(raw.get("connections", 0))

        # Determine file / task name
        name = "Unknown file"
        if "bittorrent" in raw and "info" in raw["bittorrent"]:
            name = raw["bittorrent"]["info"].get("name", name)
        elif raw.get("files"):
            first_file = raw["files"][0]
            path = first_file.get("path", "")
            if path:
                name = os.path.basename(path)
            elif first_file.get("uris"):
                first_uri = first_file["uris"][0].get("uri", "")
                name = os.path.basename(first_uri.split("?")[0]) or first_uri[:50]

        # Calculate progress %
        progress = 0.0
        if total_length > 0:
            progress = round((completed_length / total_length) * 100, 1)
        elif status == "complete":
            progress = 100.0

        # Calculate ETA
        eta_sec = 0
        if download_speed > 0 and total_length > completed_length:
            eta_sec = int((total_length - completed_length) / download_speed)

        return {
            "gid": gid,
            "name": name,
            "status": status,
            "progress": progress,
            "download_speed_raw": download_speed,
            "download_speed": f"{format_bytes(download_speed)}/s",
            "upload_speed": f"{format_bytes(upload_speed)}/s",
            "completed_length": completed_length,
            "completed_formatted": format_bytes(completed_length),
            "total_length": total_length,
            "total_formatted": format_bytes(total_length),
            "eta": format_eta(eta_sec),
            "connections": connections,
            "error_code": raw.get("errorCode"),
            "error_message": raw.get("errorMessage", "")
        }

def check_aria2c_installed() -> bool:
    return shutil.which("aria2c") is not None

def start_aria2c_daemon(download_dir: str = DOWNLOAD_DIR, port: int = ARIA2_PORT) -> bool:
    """Launches aria2c as background daemon if installed and not yet running."""
    if not check_aria2c_installed():
        logger.warning("aria2c is not installed on PATH.")
        return False

    os.makedirs(download_dir, exist_ok=True)
    cmd = [
        "aria2c",
        "--enable-rpc",
        "--rpc-listen-all=true",
        f"--rpc-listen-port={port}",
        "--max-connection-per-server=16",
        "--split=16",
        "--min-split-size=1M",
        "--max-concurrent-downloads=5",
        "--continue=true",
        f"--dir={download_dir}",
        "--rpc-allow-origin-all=true",
        "--daemon=true"
    ]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"Started aria2c daemon on port {port}")
        return True
    except Exception as e:
        logger.error(f"Failed to start aria2c daemon: {e}")
        return False
