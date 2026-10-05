import aiohttp
import urllib.parse
from typing import Dict, Any, List
from .base import BaseResolver

# Catalog of known series and movies hosted on KiyoshiiSubs (ddl-kiyoshisubs.vercel.app)
ONE_PIECE_ELBAPH_EPISODES = [
    {"ep": 1180, "size": 450887680, "size_str": "430 MB"},
    {"ep": 1179, "size": 744488960, "size_str": "710 MB"},
    {"ep": 1178, "size": 723510272, "size_str": "690 MB"},
    {"ep": 1177, "size": 655360000, "size_str": "625 MB"},
    {"ep": 1176, "size": 723510272, "size_str": "690 MB"},
    {"ep": 1175, "size": 744488960, "size_str": "710 MB"},
    {"ep": 1174, "size": 718274560, "size_str": "685 MB"},
    {"ep": 1173, "size": 681574400, "size_str": "650 MB"},
    {"ep": 1172, "size": 765460480, "size_str": "730 MB"},
    {"ep": 1171, "size": 691756483, "size_str": "660 MB"},
    {"ep": 1170, "size": 498244072, "size_str": "475 MB"},
    {"ep": 1169, "size": 557647503, "size_str": "531 MB"},
    {"ep": 1168, "size": 747634688, "size_str": "713 MB"},
    {"ep": 1167, "size": 648019968, "size_str": "618 MB"},
    {"ep": 1166, "size": 678428672, "size_str": "647 MB"},
    {"ep": 1165, "size": 754974720, "size_str": "720 MB"},
    {"ep": 1164, "size": 706740224, "size_str": "674 MB"},
    {"ep": 1163, "size": 1138229248, "size_str": "1.06 GB"},
    {"ep": 1162, "size": 707788800, "size_str": "675 MB"},
    {"ep": 1161, "size": 713031680, "size_str": "680 MB"},
    {"ep": 1160, "size": 742391808, "size_str": "708 MB"},
    {"ep": 1159, "size": 725606400, "size_str": "692 MB"},
    {"ep": 1158, "size": 607125504, "size_str": "579 MB"},
    {"ep": 1157, "size": 688914432, "size_str": "657 MB"},
    {"ep": 1156, "size": 520057578, "size_str": "496 MB"},
]

CATALOG_ITEMS = [
    {
        "id": "onepiece-elbaph",
        "title": "One Piece - S22 [Elbaph Arc] (حلقات 1156 إلى 1180)",
        "path": "/One Piece/S22 [Elbaph Arc]/SoftSub/",
        "count": 25,
        "size_str": "~16.3 GB"
    },
    {
        "id": "onepiece-egghead",
        "title": "One Piece - S21 [Egghead Arc]",
        "path": "/One Piece/S21 [Egghead Arc]/",
        "count": "كامل الأرك",
        "size_str": "87.4 GB"
    },
    {
        "id": "onepiece-wano",
        "title": "One Piece - S20 [Wano Kuni Arc]",
        "path": "/One Piece/S20 [Wano Kuni Arc]/",
        "count": "كامل الأرك",
        "size_str": "209 GB"
    },
    {
        "id": "onepiece-film-red",
        "title": "One Piece Film Red (2022)",
        "path": "/One Piece/One Piece Film Red/",
        "count": "فيلم كامل",
        "size_str": "7.63 GB"
    },
    {
        "id": "onepiece-film-stampede",
        "title": "One Piece Film Stampede (2019)",
        "path": "/One Piece/One Piece Film Stampede/",
        "count": "فيلم كامل",
        "size_str": "8.98 GB"
    },
    {
        "id": "onepiece-film-gold",
        "title": "One Piece Film Gold (2016)",
        "path": "/One Piece/One Piece Film Gold/",
        "count": "فيلم كامل",
        "size_str": "5.97 GB"
    },
    {
        "id": "bleach-tybw",
        "title": "Bleach - [Thousand-Year Blood War]",
        "path": "/Bleach - [Thousand-Year Blood War]/",
        "count": "مواسم كاملة",
        "size_str": "57.8 GB"
    },
    {
        "id": "black-clover-s2",
        "title": "Black Clover S2 (HardSub)",
        "path": "/Black Clover S2/HardSub/",
        "count": "حلقات الموسم 2",
        "size_str": "2.18 GB"
    },
    {
        "id": "kimetsu-hashira",
        "title": "Kimetsu no Yaiba - [Hashira Geiko-hen]",
        "path": "/Kimetsu no Yaiba - [Hashira Geiko-hen]/",
        "count": "موسم تدريب الهاشيرا",
        "size_str": "17.9 GB"
    },
    {
        "id": "kimetsu-mugen-jou",
        "title": "Kimetsu no Yaiba - Movie 1 - Mugen Jou-hen",
        "path": "/Kimetsu no Yaiba - Movie 1 - Mugen Jou-hen/",
        "count": "فيلم قلعة اللانهاية",
        "size_str": "12.6 GB"
    },
    {
        "id": "chainsaw-man",
        "title": "Chainsaw Man",
        "path": "/Chainsaw Man/",
        "count": "الموسم كامل",
        "size_str": "11.0 GB"
    },
    {
        "id": "suzume",
        "title": "Suzume No Tojimari (2022)",
        "path": "/Suzume No Tojimari/",
        "count": "فيلم كامل",
        "size_str": "14.2 GB"
    },
    {
        "id": "boy-and-heron",
        "title": "The Boy and the Heron (Kimitachi wa do ikiru ka)",
        "path": "/The Boy and the Heron (Kimitachi wa do ikiru ka)/",
        "count": "فيلم هاياو ميازاكي",
        "size_str": "7.76 GB"
    },
    {
        "id": "jujutsu-0",
        "title": "Jujutsu Kaisen 0",
        "path": "/Jujutsu Kaisen 0/",
        "count": "فيلم كامل",
        "size_str": "2.94 GB"
    }
]

class KiyoshiiResolver(BaseResolver):
    name = "KiyoshiiSubs / Vercel Index"

    def can_handle(self, url: str) -> bool:
        lower = url.lower()
        return "kiyoshi" in lower or ("vercel.app" in lower and any(k in lower for k in [
            "softsub", "hardsub", "arc", "piece", "bleach", "clover", "kimetsu", "chainsaw", "mkv", "mp4", "/"
        ]))

    async def resolve(self, url: str) -> Dict[str, Any]:
        parsed = urllib.parse.urlparse(url)
        raw_path = urllib.parse.unquote(parsed.path)
        netloc = parsed.netloc or "ddl-kiyoshisubs.vercel.app"
        scheme = parsed.scheme or "https"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }

        # Check if the URL points directly to a video/file or has /api/raw/
        is_file = any(raw_path.lower().endswith(ext) for ext in [".mkv", ".mp4", ".zip", ".rar", ".7z", ".avi"])
        if is_file or "/api/raw/" in url:
            if "/api/raw/" not in url:
                raw_url = f"{scheme}://{netloc}/api/raw/?path={urllib.parse.quote(raw_path)}"
            else:
                raw_url = url

            filename = raw_path.split("/")[-1] if not is_file else urllib.parse.unquote(url.split("/")[-1])
            if not filename or filename.startswith("?"):
                # Extract filename from path query param if present
                qs = urllib.parse.parse_qs(parsed.query)
                if "path" in qs and qs["path"]:
                    filename = urllib.parse.unquote(qs["path"][0]).split("/")[-1]
                else:
                    filename = "video.mkv"

            # IMPORTANT: Do not pre-resolve to my.microsoftpersonalcontent.com because
            # tempauth tokens expire! Aria2c will request this stable /api/raw/?path=
            # URL directly at download time and follow 302 to get a fresh tempauth token.
            return {
                "type": "single",
                "title": filename,
                "items": [{
                    "name": filename,
                    "url": raw_url,
                    "size": 0,
                    "size_formatted": "رابط مباشر متجدد تلقائياً (Aria2 Follow-Redirect)"
                }]
            }

        # Black Clover S2 check
        if "black clover" in raw_path.lower():
            items = [
                {
                    "name": "[KiyoshiiSubs] Black Clover S2 - 01 [HardSub - 1080p].mp4",
                    "url": f"{scheme}://{netloc}/api/raw/?path=/Black%20Clover%20S2/HardSub/%5BKiyoshiiSubs%5D%20Black%20Clover%20S2%20-%2001%20%5BHardSub%20-%201080p%5D.mp4",
                    "size": 1385100000,
                    "size_formatted": "1.29 GB"
                },
                {
                    "name": "[KiyoshiiSubs] Black Clover S2 - 02 [HardSub - 1080p].mp4",
                    "url": f"{scheme}://{netloc}/api/raw/?path=/Black%20Clover%20S2/HardSub/%5BKiyoshiiSubs%5D%20Black%20Clover%20S2%20-%2002%20%5BHardSub%20-%201080p%5D.mp4",
                    "size": 933200000,
                    "size_formatted": "890 MB"
                }
            ]
            return {
                "type": "batch",
                "title": "Black Clover S2 (KiyoshiiSubs)",
                "items": items
            }

        # One Piece Films check
        if "film red" in raw_path.lower():
            movie_url = f"{scheme}://{netloc}/api/raw/?path=/One%20Piece/One%20Piece%20Film%20Red/%5BKiyoshiiSubs%5D%20One%20Piece%20Film%20Red%20%5B1080p%5D%5BH.265%20-%2010Bit%5D.mkv"
            return {
                "type": "single",
                "title": "One Piece Film Red [1080p]",
                "items": [{
                    "name": "[KiyoshiiSubs] One Piece Film Red [1080p][H.265 - 10Bit].mkv",
                    "url": movie_url,
                    "size": 8192000000,
                    "size_formatted": "7.63 GB"
                }]
            }

        # Dynamic query attempt for folder contents (checking folder.value & data.value)
        clean_path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
        api_url = f"{scheme}://{netloc}/api/?path={urllib.parse.quote(clean_path)}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        files = []
                        if isinstance(data, dict):
                            # On onedrive-vercel-index, items are inside folder.value
                            files = (
                                data.get("folder", {}).get("value", [])
                                or data.get("data", {}).get("value", [])
                                or data.get("value", [])
                                or data.get("children", [])
                            )

                        items = []
                        for f in files:
                            # Skip subfolders if we are listing files
                            if "folder" in f:
                                continue
                            name = f.get("name", "file.mkv")
                            size = int(f.get("size", 0))
                            file_path = f"{clean_path.rstrip('/')}/{name}"
                            raw_file_url = f"{scheme}://{netloc}/api/raw/?path={urllib.parse.quote(file_path)}"

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

        # Complete 25-Episode Catalog for One Piece S22 Elbaph Arc (1156 to 1180)
        # Built dynamically with stable /api/raw/ endpoints that renew Microsoft tempauth on download
        items = []
        base_template = f"{scheme}://{netloc}/api/raw/?path=/One%20Piece/S22%20%5BElbaph%20Arc%5D/SoftSub/%5BKiyoshiiSubs%5D%20One%20Piece%20-%20{{ep}}%20%5B1080p%5D%5BH.265%20-%2010Bit%5D.mkv"
        for ep_info in ONE_PIECE_ELBAPH_EPISODES:
            ep = ep_info["ep"]
            items.append({
                "name": f"[KiyoshiiSubs] One Piece - {ep} [1080p][H.265 - 10Bit].mkv",
                "url": base_template.format(ep=ep),
                "size": ep_info["size"],
                "size_formatted": ep_info["size_str"]
            })

        return {
            "type": "batch",
            "title": "One Piece - S22 [Elbaph Arc] (25 حلقة كاملة: 1156 إلى 1180)",
            "items": items,
            "catalog": CATALOG_ITEMS
        }
