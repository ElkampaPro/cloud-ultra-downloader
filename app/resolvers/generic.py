import aiohttp
import urllib.parse
import re
from typing import Dict, Any, List
from .base import BaseResolver

class GenericResolver(BaseResolver):
    name = "Generic / Direct Link"

    def can_handle(self, url: str) -> bool:
        return True # Fallback for all other URLs

    async def resolve(self, url: str) -> Dict[str, Any]:
        url = url.strip()

        # Handle Magnet link
        if url.startswith("magnet:"):
            # Extract display name from magnet dn parameter
            dn_match = re.search(r"dn=([^&]+)", url)
            name = urllib.parse.unquote_plus(dn_match.group(1)) if dn_match else "Magnet Download"
            return {
                "type": "single",
                "title": name,
                "items": [{
                    "name": name,
                    "url": url,
                    "size": 0,
                    "size_formatted": "Torrent Swarm"
                }]
            }

        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        filename = path.split("/")[-1] if path and "/" in path else "download.bin"
        if not filename:
            filename = "download.bin"

        size_bytes = 0
        size_formatted = "Unknown"

        # Try lightweight HEAD request to inspect filename & content length
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.head(url, headers=headers, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        cl = resp.headers.get("Content-Length")
                        if cl and cl.isdigit():
                            size_bytes = int(cl)
                            size_mb = size_bytes / (1024 * 1024)
                            size_formatted = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{(size_mb/1024):.2f} GB"

                        cd = resp.headers.get("Content-Disposition", "")
                        fn_match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\n]+)["\']?', cd, re.IGNORECASE)
                        if fn_match:
                            filename = urllib.parse.unquote(fn_match.group(1))
        except Exception:
            pass

        return {
            "type": "single",
            "title": filename,
            "items": [{
                "name": filename,
                "url": url,
                "size": size_bytes,
                "size_formatted": size_formatted
            }]
        }
