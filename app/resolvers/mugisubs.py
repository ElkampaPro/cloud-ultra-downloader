import asyncio
import aiohttp
import urllib.parse
from typing import Dict, Any, List
from .base import BaseResolver

MUGISUBS_CATALOG = [
    {
        "id": "mugi-bleach",
        "title": "Bleach - Sennen Kessen-hen S4 (الحلقات 41 - 48)",
        "path": "/Bleach - Sennen Kessen-hen S4/",
        "count": "8 حلقات",
        "size_str": "8.46 GB"
    },
    {
        "id": "mugi-frieren",
        "title": "Sousou no Frieren S2 (الحلقات 01 - 10)",
        "path": "/Sousou no Frieren S2/",
        "count": "10 حلقات",
        "size_str": "10.3 GB"
    },
    {
        "id": "mugi-solo",
        "title": "Solo Leveling Season 2 (الحلقات 13 - 25)",
        "path": "/Solo Leveling/",
        "count": "13 حلقة",
        "size_str": "12.2 GB"
    },
    {
        "id": "mugi-tobehero",
        "title": "To Be Hero X (الحلقات 01 - 24)",
        "path": "/To Be Hero X/",
        "count": "24 حلقة",
        "size_str": "23.2 GB"
    }
]

class MugiSubsResolver(BaseResolver):
    name = "MugiSubs / GoIndex"

    def can_handle(self, url: str) -> bool:
        lower = url.lower()
        return "mugisubs" in lower or ("workers.dev" in lower and ("0:" in lower or "download.aspx" in lower or "bleach" in lower or "frieren" in lower or "solo" in lower or "hero" in lower or "/" in lower))

    async def resolve(self, url: str) -> Dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        raw_path = urllib.parse.unquote(parsed.path)
        netloc = parsed.netloc or "ddl.mugisubs.workers.dev"
        scheme = parsed.scheme or "https"
        base_origin = f"{scheme}://{netloc}"
        base_loader = "https://loader.mugisubs1.workers.dev"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": f"{base_origin}/"
        }

        # If it's already a direct download link
        if "download.aspx" in url or any(raw_path.lower().endswith(ext) for ext in [".mkv", ".mp4", ".zip", ".rar", ".7z"]):
            filename = urllib.parse.unquote(raw_path.strip("/").split("/")[-1])
            if not filename or filename.startswith("?"):
                filename = "video.mkv"
            
            # Ensure full url uses loader host for download.aspx
            download_url = url
            if url.startswith("/") or "download.aspx" in url:
                if not url.startswith("http"):
                    download_url = urllib.parse.urljoin(base_loader, url)
                elif base_origin in url and "download.aspx" in url:
                    download_url = url.replace(base_origin, base_loader)

            return {
                "type": "single",
                "title": filename,
                "items": [{
                    "name": filename,
                    "url": download_url,
                    "size": 0,
                    "size_formatted": "رابط مباشر متجدد (MugiSubs Loader)",
                    "referer": f"{base_origin}/"
                }]
            }

        # Normalize GoIndex folder path
        clean_path = raw_path
        if not clean_path or clean_path == "/" or clean_path == "/0:":
            clean_path = "/0:/"
        elif not clean_path.startswith("/0:/") and not clean_path.startswith("0:/"):
            clean_path = "/0:/" + clean_path.lstrip("/")
        if not clean_path.endswith("/"):
            clean_path += "/"

        async def fetch_folder_files(session: aiohttp.ClientSession, path_to_fetch: str):
            unquoted = urllib.parse.unquote(path_to_fetch)
            encoded_path = urllib.parse.quote(unquoted, safe="/:")
            folder_url = f"{base_origin}{encoded_path}"
            payload = {
                "id": "",
                "type": "folder",
                "password": "",
                "page_token": "",
                "page_index": 0
            }
            async with session.post(folder_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return data.get("data", {}).get("files", [])

        async with aiohttp.ClientSession() as session:
            # Check if user requested the root index
            is_root = clean_path == "/0:/"

            folders_to_scan = []
            if is_root:
                # Fetch root folders (Bleach, Solo Leveling, Frieren, To Be Hero X)
                root_files = await fetch_folder_files(session, "/0:/")
                for rf in root_files:
                    rname = rf.get("name")
                    if rname and not rf.get("link"):
                        folders_to_scan.append(f"/0:/{rname}/")
            else:
                folders_to_scan.append(clean_path)

            if is_root or not folders_to_scan:
                folders_to_scan = [f"/0:/{cat['path'].strip('/')}/" for cat in MUGISUBS_CATALOG]

            all_video_files = []

            for folder_p in folders_to_scan:
                sub_files = await fetch_folder_files(session, folder_p)
                
                # Check if this folder has nested 'Soft' folder or direct video files
                direct_videos = [f for f in sub_files if f.get("link")]
                if direct_videos:
                    all_video_files.extend(direct_videos)
                else:
                    # Look for subfolders like 'Soft' or first subfolder
                    for sf in sub_files:
                        sf_name = sf.get("name", "")
                        if not sf.get("link") and (sf_name.lower() == "soft" or "1080" in sf_name.lower() or not direct_videos):
                            nested_path = f"{folder_p}{sf_name}/"
                            nested_files = await fetch_folder_files(session, nested_path)
                            nested_videos = [f for f in nested_files if f.get("link")]
                            all_video_files.extend(nested_videos)

            items: List[Dict[str, Any]] = []
            for f in all_video_files:
                name = f.get("name", "video.mkv")
                link = f.get("link", "")
                if not link:
                    continue
                size_bytes = int(f.get("size", 0) or 0)
                full_download_url = urllib.parse.urljoin(base_loader, link)

                size_mb = size_bytes / (1024 * 1024)
                size_formatted = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{(size_mb/1024):.2f} GB"

                items.append({
                    "name": name,
                    "url": full_download_url,
                    "size": size_bytes,
                    "size_formatted": size_formatted,
                    "referer": f"{base_origin}/"
                })

            if not items:
                raise ValueError("لم يتم العثور على ملفات فيديو داخل مجلد MugiSubs المحدد.")

            path_parts = [urllib.parse.unquote(p) for p in clean_path.strip("/").split("/") if p and p != "0:"]
            title = path_parts[-1] if path_parts else f"MugiSubs Anime Library ({len(items)} حلقة متجددة)"

            return {
                "type": "batch" if len(items) > 1 else "single",
                "title": title,
                "items": items,
                "catalog": MUGISUBS_CATALOG
            }
