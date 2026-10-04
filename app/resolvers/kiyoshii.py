import aiohttp
import urllib.parse
from typing import Dict, Any, List
from .base import BaseResolver

class KiyoshiiResolver(BaseResolver):
    name = "KiyoshiiSubs / Vercel Index"

    def can_handle(self, url: str) -> bool:
        lower = url.lower()
        return "kiyoshi" in lower or ("vercel.app" in lower and ("softsub" in lower or "arc" in lower or "piece" in lower))

    async def resolve(self, url: str) -> Dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)

        # Check if the URL points directly to a video/file
        is_file = any(path.lower().endswith(ext) for ext in [".mkv", ".mp4", ".zip", ".rar", ".7z", ".avi"])
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }

        # If it's a direct file URL on Vercel index, convert to api/raw URL to resolve 307
        if is_file or "/api/raw/" in url:
            if "/api/raw/" not in url:
                raw_url = f"{parsed.scheme}://{parsed.netloc}/api/raw/?path={urllib.parse.quote(path)}"
            else:
                raw_url = url

            filename = path.split("/")[-1] if not is_file else urllib.parse.unquote(url.split("/")[-1])
            
            # Follow redirect to obtain direct Microsoft download link
            async with aiohttp.ClientSession() as session:
                async with session.get(raw_url, headers=headers, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status in (301, 302, 307, 308):
                        direct_url = resp.headers.get("Location")
                        if direct_url:
                            return {
                                "type": "single",
                                "title": filename,
                                "items": [{
                                    "name": filename,
                                    "url": direct_url,
                                    "size": 0,
                                    "size_formatted": "Cloud Stream"
                                }]
                            }

            # If no redirect or handled as-is
            return {
                "type": "single",
                "title": filename,
                "items": [{
                    "name": filename,
                    "url": raw_url,
                    "size": 0,
                    "size_formatted": "Direct Link"
                }]
            }

        # It's a folder, query the /api/?path= endpoint
        clean_path = path if path.startswith("/") else f"/{path}"
        api_url = f"{parsed.scheme}://{parsed.netloc}/api/?path={urllib.parse.quote(clean_path)}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        files = []
                        # Onedrive vercel index format
                        if isinstance(data, dict):
                            files = data.get("data", {}).get("value", []) or data.get("value", []) or data.get("children", [])
                        
                        items = []
                        for f in files:
                            if "folder" in f:
                                continue # Skip folders
                            name = f.get("name", "file.mkv")
                            size = int(f.get("size", 0))
                            file_path = f"{clean_path.rstrip('/')}/{name}"
                            raw_file_url = f"{parsed.scheme}://{parsed.netloc}/api/raw/?path={urllib.parse.quote(file_path)}"
                            
                            size_mb = size / (1024 * 1024)
                            size_formatted = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{(size_mb/1024):.2f} GB"

                            items.append({
                                "name": name,
                                "url": raw_file_url,
                                "size": size,
                                "size_formatted": size_formatted
                            })

                        if items:
                            title = [p for p in clean_path.split("/") if p][-1]
                            return {
                                "type": "batch",
                                "title": title,
                                "items": items
                            }
            except Exception:
                pass

        # Fallback if folder API is rate-limited: treat as direct URL
        return {
            "type": "single",
            "title": "Kiyoshii Resource",
            "items": [{
                "name": path.strip("/").split("/")[-1] or "download.mkv",
                "url": url,
                "size": 0,
                "size_formatted": "Direct Link"
            }]
        }
