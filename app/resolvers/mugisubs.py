import aiohttp
import urllib.parse
from typing import Dict, Any, List
from .base import BaseResolver

class MugiSubsResolver(BaseResolver):
    name = "MugiSubs / GoIndex"

    def can_handle(self, url: str) -> bool:
        lower = url.lower()
        return "mugisubs" in lower or "workers.dev" in lower

    async def resolve(self, url: str) -> Dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        raw_path = urllib.parse.unquote(parsed.path)

        # Normalize GoIndex path
        if not raw_path or raw_path == "/":
            raw_path = "/0:/"
        elif not raw_path.startswith("/0:/") and not raw_path.startswith("0:/"):
            raw_path = "/0:/" + raw_path.lstrip("/")
        if not raw_path.endswith("/"):
            raw_path += "/"

        # If it's already a direct download link
        if any(raw_path.lower().endswith(ext) for ext in [".mkv", ".mp4", ".zip", ".rar", ".7z"]) or "download.aspx" in url:
            filename = urllib.parse.unquote(raw_path.strip("/").split("/")[-1])
            return {
                "type": "single",
                "title": filename or "MugiSubs Direct File",
                "items": [{
                    "name": filename or "video.mkv",
                    "url": url,
                    "size": 0,
                    "size_formatted": "MugiSubs Direct File"
                }]
            }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        async def fetch_folder(path_to_fetch: str):
            encoded_path = urllib.parse.quote(path_to_fetch, safe="/:")
            folder_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
            payload = {
                "id": "",
                "type": "folder",
                "password": "",
                "page_token": "",
                "page_index": 0
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(folder_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"MugiSubs index returned HTTP {resp.status}")
                    data = await resp.json()
                    return data.get("data", {}).get("files", []), folder_url

        files, final_url = await fetch_folder(raw_path)

        # If it's root or contains subfolder 'Soft' or anime directories:
        soft_folder = next((f for f in files if f.get("name") == "Soft" or (f.get("size") == "0" and not f.get("link"))), None)
        if soft_folder:
            sub_path = raw_path + urllib.parse.quote(soft_folder.get("name", "Soft"), safe="") + "/"
            try:
                sub_files, _ = await fetch_folder(sub_path)
                if sub_files:
                    files = sub_files
            except Exception:
                pass

        # Or if root had Bleach:
        bleach_folder = next((f for f in files if "bleach" in f.get("name", "").lower()), None)
        if bleach_folder and len(files) <= 5: # root listing
            sub_path = raw_path + urllib.parse.quote(bleach_folder.get("name"), safe="") + "/Soft/"
            try:
                sub_files, _ = await fetch_folder(sub_path)
                if sub_files:
                    files = sub_files
            except Exception:
                pass

        # Build items list
        base_loader = f"{parsed.scheme}://loader.mugisubs1.workers.dev" if "mugisubs" in parsed.netloc else f"{parsed.scheme}://{parsed.netloc}"
        items: List[Dict[str, Any]] = []

        for f in files:
            name = f.get("name", "video.mkv")
            link = f.get("link", "")
            if not link:
                continue
            size_bytes = int(f.get("size", 0))
            full_download_url = urllib.parse.urljoin(base_loader, link)

            size_mb = size_bytes / (1024 * 1024)
            size_formatted = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{(size_mb/1024):.2f} GB"

            items.append({
                "name": name,
                "url": full_download_url,
                "size": size_bytes,
                "size_formatted": size_formatted
            })

        if not items:
            raise RuntimeError("لم يتم العثور على ملفات فيديو داخل مجلد MugiSubs المحدد.")

        path_parts = [urllib.parse.unquote(p) for p in raw_path.strip("/").split("/") if p and p != "0:"]
        title = path_parts[-1] if path_parts else "MugiSubs Anime"

        return {
            "type": "batch" if len(items) > 1 else "single",
            "title": title,
            "items": items
        }
