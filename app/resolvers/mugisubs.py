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
        # Clean URL
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        
        # If it's already a direct download link
        if "download.aspx" in url or "loader." in url:
            filename = urllib.parse.unquote(path.split("/")[-1])
            return {
                "type": "single",
                "title": filename or "MugiSubs Direct File",
                "items": [{
                    "name": filename,
                    "url": url,
                    "size": 0,
                    "size_formatted": "Unknown"
                }]
            }

        # It's a folder/series link, query the GoIndex API
        folder_url = url
        if not folder_url.endswith("/"):
            folder_url += "/"

        payload = {
            "id": "",
            "type": "folder",
            "password": "",
            "page_token": "",
            "page_index": 0
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(folder_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"MugiSubs index returned HTTP {resp.status}")
                data = await resp.json()

        files = data.get("data", {}).get("files", [])
        if not files:
            raise RuntimeError("No files found in MugiSubs folder.")

        # Determine series title from URL path
        path_parts = [urllib.parse.unquote(p) for p in path.strip("/").split("/") if p and p != "0:"]
        title = path_parts[-1] if path_parts else "MugiSubs Release"

        items: List[Dict[str, Any]] = []
        for f in files:
            name = f.get("name", "video.mkv")
            size_bytes = int(f.get("size", 0))
            link = f.get("link", "")
            
            # Construct download loader URL
            # The loader worker host is typically https://loader.mugisubs1.workers.dev
            base_loader = f"{parsed.scheme}://loader.mugisubs1.workers.dev" if "mugisubs" in parsed.netloc else f"{parsed.scheme}://{parsed.netloc}"
            full_download_url = urllib.parse.urljoin(base_loader, link)

            # Format size
            size_mb = size_bytes / (1024 * 1024)
            size_formatted = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{(size_mb/1024):.2f} GB"

            items.append({
                "name": name,
                "url": full_download_url,
                "size": size_bytes,
                "size_formatted": size_formatted
            })

        return {
            "type": "batch" if len(items) > 1 else "single",
            "title": title,
            "items": items
        }
