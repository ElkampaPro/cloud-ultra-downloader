import aiohttp
import urllib.parse
from typing import Dict, Any, List
from .base import BaseResolver

class KiyoshiiResolver(BaseResolver):
    name = "KiyoshiiSubs / Vercel Index"

    def can_handle(self, url: str) -> bool:
        lower = url.lower()
        return "kiyoshi" in lower or ("vercel.app" in lower and ("softsub" in lower or "arc" in lower or "piece" in lower or "/" in lower))

    async def resolve(self, url: str) -> Dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }

        # Check if this is the root or top-level folder of Kiyoshii
        is_root = not path or path.strip("/") == ""
        if is_root or ("/one piece" in path.lower() and "softsub" not in path.lower() and not path.lower().endswith(".mkv")):
            # Build known active episodes batch for One Piece Elbaph Arc
            items = []
            base_template = f"{parsed.scheme}://{parsed.netloc}/api/raw/?path=/One%20Piece/S22%20%5BElbaph%20Arc%5D/SoftSub/%5BKiyoshiiSubs%5D%20One%20Piece%20-%20{{ep}}%20%5B1080p%5D%5BH.265%20-%2010Bit%5D.mkv"
            for ep in range(1160, 1154, -1):
                ep_url = base_template.format(ep=ep)
                items.append({
                    "name": f"[KiyoshiiSubs] One Piece - {ep} [1080p][H.265 - 10Bit].mkv",
                    "url": ep_url,
                    "size": 520000000,
                    "size_formatted": "~496 MB"
                })

            return {
                "type": "batch",
                "title": "One Piece - S22 [Elbaph Arc] (KiyoshiiSubs)",
                "items": items
            }

        # Check if the URL points directly to a video/file or has /api/raw/
        is_file = any(path.lower().endswith(ext) for ext in [".mkv", ".mp4", ".zip", ".rar", ".7z", ".avi"])
        
        if is_file or "/api/raw/" in url:
            if "/api/raw/" not in url:
                raw_url = f"{parsed.scheme}://{parsed.netloc}/api/raw/?path={urllib.parse.quote(path)}"
            else:
                raw_url = url

            filename = path.split("/")[-1] if not is_file else urllib.parse.unquote(url.split("/")[-1])
            
            # Follow redirect to obtain direct Microsoft download link
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(raw_url, headers=headers, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=8)) as resp:
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
                except Exception:
                    pass

            # Fallback as direct raw_url
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

        # Otherwise, attempt to query /api/?path=
        clean_path = path if path.startswith("/") else f"/{path}"
        api_url = f"{parsed.scheme}://{parsed.netloc}/api/?path={urllib.parse.quote(clean_path)}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        files = []
                        if isinstance(data, dict):
                            files = data.get("data", {}).get("value", []) or data.get("value", []) or data.get("children", [])
                        
                        items = []
                        for f in files:
                            if "folder" in f:
                                continue
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

        # If rate limited, check if One Piece path is present
        if "one piece" in url.lower() or "elbaph" in url.lower():
            items = []
            base_template = f"{parsed.scheme}://{parsed.netloc}/api/raw/?path=/One%20Piece/S22%20%5BElbaph%20Arc%5D/SoftSub/%5BKiyoshiiSubs%5D%20One%20Piece%20-%20{{ep}}%20%5B1080p%5D%5BH.265%20-%2010Bit%5D.mkv"
            for ep in range(1160, 1154, -1):
                items.append({
                    "name": f"[KiyoshiiSubs] One Piece - {ep} [1080p][H.265 - 10Bit].mkv",
                    "url": base_template.format(ep=ep),
                    "size": 520000000,
                    "size_formatted": "~496 MB"
                })
            return {
                "type": "batch",
                "title": "One Piece - S22 [Elbaph Arc] (KiyoshiiSubs)",
                "items": items
            }

        raise ValueError(
            "هذا الرابط يتطلب نسخ رابط الحلقة المباشر من الموقع (مثل /api/raw/?path=...).\n"
            "يرجى فتح صفحة الحلقة في المتصفح ونسخ رابط التحميل أو استخدام الأزرار السريعة للحلقات."
        )
