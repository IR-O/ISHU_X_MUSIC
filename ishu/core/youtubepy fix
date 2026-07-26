# ishu/youtube.py
import asyncio
import glob
import os
import re
import time as _time
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from ishu import config, logger
from ishu.helpers import utils
from ishu.helpers._dataclass import Track
from ishu.po_token import po_token_gen  # PO Token import

# ── Config ──────────────────────────────────────────────────────────────
SHRUTI_API_URL = getattr(config, "SHRUTI_API_URL", "https://api.shrutibots.site")
SHRUTI_API_KEY = getattr(config, "SHRUTI_API_KEY", None)
RAILWAY_YT_API_URL = getattr(config, "RAILWAY_YT_API_URL", None)
RAILWAY_YT_API_KEY = getattr(config, "RAILWAY_YT_API_KEY", None)
YTPROXY_URL = getattr(config, "YTPROXY_URL", None)
YT_API_KEY = getattr(config, "YT_API_KEY", None)
DOWNLOAD_DIR = "downloads"

_dl_locks = {}
JS_RUNTIMES = {"node": {}}
_DEFAULT_PLAYER_CLIENTS = "tv,ios,android,web_safari,mweb"

def _format_duration(seconds):
    """Duration ko MM:SS ya HH:MM:SS mein convert karo - FIXED for float"""
    try:
        # Agar float hai toh int mein convert karo
        if isinstance(seconds, float):
            seconds = int(seconds)
        elif isinstance(seconds, str):
            seconds = int(float(seconds))
        
        if seconds < 60:
            return f"0:{seconds:02d}"
        elif seconds < 3600:
            return f"{seconds//60}:{seconds%60:02d}"
        else:
            return f"{seconds//3600}:{(seconds%3600)//60:02d}:{seconds%60:02d}"
    except Exception as e:
        logger.warning(f"Duration format error: {e}, value: {seconds}")
        return "0:00"

def _with_js_runtime(opts):
    out = dict(opts)
    out["js_runtimes"] = JS_RUNTIMES
    out["user_agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    
    # PO Token support
    if os.environ.get("USE_PO_TOKEN"):
        extractor_args = dict(out.get("extractor_args") or {})
        yt_args = dict(extractor_args.get("youtube") or {})
        yt_args["player_client"] = ["tv", "ios", "android"]
        yt_args["player_skip"] = ["webpage", "configs"]
        extractor_args["youtube"] = yt_args
        out["extractor_args"] = extractor_args
    else:
        out["extractor_args"] = {
            "youtube": {
                "player_client": ["tv", "mweb", "web_safari", "android_vr"],
                "player_skip": ["webpage", "configs"]
            }
        }
    
    proxy = os.environ.get("YTDLP_PROXY")
    if proxy:
        out["proxy"] = proxy
    return out

_COOKIE_PATH = None

def cookie_txt_file():
    global _COOKIE_PATH
    if _COOKIE_PATH:
        return _COOKIE_PATH
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cookies")
    primary = os.path.join(folder, "cookie_0.txt")
    if os.path.exists(primary):
        _COOKIE_PATH = primary
        return primary
    txt_files = glob.glob(os.path.join(folder, "*.txt"))
    _COOKIE_PATH = txt_files[0] if txt_files else None
    return _COOKIE_PATH

def _normalize_youtube_link(link, base="https://www.youtube.com/watch?v="):
    if not link:
        return ""
    cleaned = link.strip()
    if "youtube.com" not in cleaned and "youtu.be" not in cleaned:
        cleaned = base + cleaned
    cleaned = cleaned.split("&si=")[0].split("?si=")[0]
    return cleaned.split("&")[0] if "&" in cleaned and "list=" not in cleaned else cleaned

def _extract_video_id(link):
    cleaned = _normalize_youtube_link(link)
    if not cleaned:
        return None
    if "v=" in cleaned:
        return cleaned.split("v=")[-1].split("&")[0]
    if "youtu.be/" in cleaned:
        return cleaned.split("youtu.be/")[-1].split("?")[0].split("&")[0]
    return cleaned if len(cleaned) == 11 else None

def _resolve_downloaded_file(video_id, ext):
    candidates = [os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")]
    for c in glob.glob(os.path.join(DOWNLOAD_DIR, f"{video_id}.*")):
        if not c.endswith((".part", ".ytdl")) and ".orig." not in os.path.basename(c):
            candidates.append(c)
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 0:
            return c
    return None

def _dl_lock(video_id):
    if video_id not in _dl_locks:
        _dl_locks[video_id] = asyncio.Lock()
    return _dl_locks[video_id]

# ── Downloaders ────────────────────────────────────────────────────────

async def _cookies_download(link, media_type):
    video_id = _extract_video_id(link) or link
    ext = "mp4" if media_type == "video" else "mp3"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    async with _dl_lock(video_id):
        existing = _resolve_downloaded_file(video_id, ext)
        if existing:
            return existing
        
        cookie = cookie_txt_file()
        if not cookie or not os.environ.get("ALLOW_COOKIE_DOWNLOAD"):
            return None
        
        try:
            # Try PO Token if available
            po_token = None
            if os.environ.get("USE_PO_TOKEN"):
                po_token = po_token_gen.get_token(video_id)
                if po_token:
                    logger.info(f"✅ Using PO Token for {video_id}")
            
            outtmpl = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")
            ydl_opts = {
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "cookiefile": cookie,
            }
            
            # Add PO Token to extractor args
            ydl_opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["tv", "ios", "android"],
                    "skip": ["dash", "hls"]
                }
            }
            
            if po_token:
                ydl_opts["extractor_args"]["youtube"]["po_token"] = po_token
            
            if media_type == "video":
                ydl_opts.update({"format": "bestvideo[height<=720]+bestaudio/best[height<=720]", "merge_output_format": "mp4"})
            else:
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
                })
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(_with_js_runtime(ydl_opts)).download([_normalize_youtube_link(link)]))
            
            result = _resolve_downloaded_file(video_id, ext)
            if result:
                logger.info(f"✅ Cookies + PO Token ✓ {video_id}")
                return result
        except Exception as e:
            logger.warning(f"⚠️ Cookies failed: {e}")
    return None

async def _ytdlp_nocookie_download(link, media_type):
    video_id = _extract_video_id(link) or link
    ext = "mp4" if media_type == "video" else "mp3"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    async with _dl_lock(video_id):
        existing = _resolve_downloaded_file(video_id, ext)
        if existing:
            return existing
        
        try:
            outtmpl = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")
            ydl_opts = {
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "extractor_args": {"youtube": {"player_client": ["tv", "ios", "android"]}}
            }
            
            if media_type == "video":
                ydl_opts.update({"format": "bestvideo[height<=720]+bestaudio/best[height<=720]", "merge_output_format": "mp4"})
            else:
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
                })
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(_with_js_runtime(ydl_opts)).download([_normalize_youtube_link(link)]))
            
            result = _resolve_downloaded_file(video_id, ext)
            if result:
                logger.info(f"✅ yt-dlp ✓ {video_id}")
                return result
        except Exception as e:
            logger.warning(f"⚠️ yt-dlp failed: {e}")
    return None

async def _railway_download(video_id, media_type):
    if not RAILWAY_YT_API_URL or not RAILWAY_YT_API_KEY:
        return None
    ext = "mp4" if media_type == "video" else "mp3"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path
    
    headers = {"User-Agent": "Mozilla/5.0", "X-API-Key": str(RAILWAY_YT_API_KEY)}
    endpoints = ["play/video/hq", "play/video"] if media_type == "video" else ["play/audio"]
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            for endpoint in endpoints:
                media_url = f"{RAILWAY_YT_API_URL}/{endpoint}?id={video_id}"
                async with session.get(media_url, timeout=aiohttp.ClientTimeout(total=300), allow_redirects=True) as resp:
                    if resp.status == 200:
                        with open(file_path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(1024 * 1024):
                                f.write(chunk)
                        if os.path.getsize(file_path) > 0:
                            logger.info(f"✅ Railway ✓ {video_id}")
                            return file_path
    except Exception as e:
        logger.warning(f"⚠️ Railway failed: {e}")
    return None

async def _download_with_fallback(link, media_type):
    video_id = _extract_video_id(link) or link
    
    # Priority 1: Cookies + PO Token
    result = await _cookies_download(link, media_type)
    if result:
        return result, "cookies_po_token"
    
    # Priority 2: yt-dlp
    result = await _ytdlp_nocookie_download(link, media_type)
    if result:
        return result, "ytdlp"
    
    # Priority 3: Railway
    result = await _railway_download(video_id, media_type)
    if result:
        return result, "railway"
    
    logger.error(f"❌ All methods failed: {video_id}")
    return None, "none"

async def download_song(link, title=None):
    path, _ = await _download_with_fallback(link, "audio")
    return path

async def download_video(link, title=None):
    path, _ = await _download_with_fallback(link, "video")
    return path

# ── YouTube Class ───────────────────────────────────────────────────────

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        self.cookies_dir = os.path.join(os.path.dirname(__file__), "..", "cookies")
        self._load_cookies()
        self.dl_stats = {"total": 0, "cookies_po_token": 0, "ytdlp": 0, "railway": 0, "failed": 0}

    def _load_cookies(self):
        import base64, gzip, re, time
        
        def _write(decoded, src):
            os.makedirs(self.cookies_dir, exist_ok=True)
            cookie_path = os.path.join(self.cookies_dir, "cookie_0.txt")
            with open(cookie_path, "w") as f:
                f.write(decoded)
            
            # Cookie verify karo
            if "youtube.com" in decoded:
                now = int(time.time())
                expired = re.findall(r'\.youtube\.com\s+TRUE\s+/\s+FALSE\s+(\d+)\s+', decoded)
                if expired:
                    valid = [e for e in expired if int(e) > now]
                    logger.info(f"✅ Cookies loaded: {len(valid)}/{len(expired)} valid from {src}")
                    if not valid:
                        logger.warning("⚠️ ALL COOKIES EXPIRED! Get fresh cookies.")
                else:
                    logger.info(f"✅ Cookies loaded from {src}")
            else:
                logger.warning("⚠️ Invalid cookies - no YouTube entries!")
        
        cookies_data = os.environ.get("COOKIES_DATA") or getattr(config, "COOKIES_DATA", None)
        if cookies_data:
            try:
                cd = "".join(cookies_data.split())
                pad = (-len(cd)) % 4
                if pad:
                    cd += "=" * pad
                raw = base64.b64decode(cd)
                try:
                    _write(gzip.decompress(raw).decode("utf-8"), "COOKIES_DATA+gzip")
                except:
                    _write(raw.decode("utf-8"), "COOKIES_DATA")
                return
            except Exception as e:
                logger.error(f"COOKIES_DATA error: {e}")
        
        cookies_file = os.environ.get("COOKIES_FILE") or getattr(config, "COOKIES_FILE", None)
        if cookies_file and os.path.exists(cookies_file):
            try:
                data = open(cookies_file, "rb").read()
                if data[:2] == b"\x1f\x8b":
                    _write(gzip.decompress(data).decode("utf-8"), "COOKIES_FILE+gzip")
                else:
                    _write(data.decode("utf-8"), "COOKIES_FILE")
            except Exception as e:
                logger.error(f"COOKIES_FILE error: {e}")

    def valid(self, url):
        return bool(re.search(self.regex, url))

    def invalid(self, url):
        return not self.valid(url)

    async def exists(self, link, videoid=None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1):
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            text = message.text or message.caption or ""
            if message.entities:
                for entity in message.entities:
                    if entity.type in (MessageEntityType.URL, MessageEntityType.TEXT_LINK):
                        if entity.type == MessageEntityType.TEXT_LINK:
                            return entity.url
                        return text[entity.offset:entity.offset + entity.length]
            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        r = (await VideosSearch(link, limit=1).next())["result"][0]
        duration = r["duration"]
        return r["title"], duration, int(utils.to_seconds(duration)) if duration else 0, r["thumbnails"][0]["url"].split("?")[0], r["id"]

    async def title(self, link, videoid=None):
        if videoid:
            link = self.base + link
        r = (await VideosSearch(_normalize_youtube_link(link), limit=1).next())["result"]
        return r[0]["title"] if r else None

    async def duration(self, link, videoid=None):
        if videoid:
            link = self.base + link
        r = (await VideosSearch(_normalize_youtube_link(link), limit=1).next())["result"]
        return r[0]["duration"] if r else None

    async def thumbnail(self, link, videoid=None):
        if videoid:
            link = self.base + link
        r = (await VideosSearch(_normalize_youtube_link(link), limit=1).next())["result"]
        return r[0]["thumbnails"][0]["url"].split("?")[0] if r else None

    async def track(self, link, videoid=None):
        if videoid:
            link = self.base + link
        r = (await VideosSearch(_normalize_youtube_link(link), limit=1).next())["result"]
        if r:
            return {"title": r[0]["title"], "link": r[0]["link"], "vidid": r[0]["id"], 
                    "duration_min": r[0]["duration"], "thumb": r[0]["thumbnails"][0]["url"].split("?")[0]}, r[0]["id"]
        return None, None

    async def search(self, query, message_id, video=False):
        """Search using yt-dlp (more reliable) - FIXED for float duration"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'extractor_args': {'youtube': {'player_client': ['tv', 'ios', 'android']}}
        }
        
        try:
            with yt_dlp.YoutubeDL(_with_js_runtime(ydl_opts)) as ydl:
                info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                results = info.get('entries', [])
                
                for r in results:
                    vid = r.get('id')
                    if not vid:
                        continue
                    duration = r.get('duration', 0)
                    # Fix: duration ko int mein convert karo
                    try:
                        duration = int(float(duration)) if duration else 0
                    except (ValueError, TypeError):
                        duration = 0
                        
                    if 30 <= duration <= 3600:
                        return Track(
                            id=vid,
                            title=r.get('title', 'Unknown'),
                            url=f"https://youtube.com/watch?v={vid}",
                            duration=_format_duration(duration),
                            duration_sec=duration,
                            thumbnail=f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                            channel_name=r.get('channel', ''),
                            message_id=message_id,
                            video=video,
                            time=int(_time.time())
                        )
        except Exception as e:
            logger.warning(f"Search error: {e}")
        return None

    async def get_stream_url(self, video_id, video=False, force_cookies=False):
        link = _normalize_youtube_link(video_id, self.base)
        cookie = cookie_txt_file()
        use_cookies = bool(cookie) and (force_cookies or os.environ.get("ALLOW_COOKIE_DOWNLOAD"))
        
        try:
            ydl_opts = {
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]" if video else "bestaudio/best",
                "quiet": True, "no_warnings": True
            }
            ydl_opts = _with_js_runtime(ydl_opts)
            loop = asyncio.get_event_loop()
            
            def _run():
                opts = dict(ydl_opts)
                if use_cookies:
                    opts["cookiefile"] = cookie
                info = yt_dlp.YoutubeDL(opts).extract_info(link, download=False)
                return info.get("url") or (info.get("formats") or [{}])[-1].get("url")
            
            url = await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=25)
            if url:
                logger.info(f"✅ Stream via {'cookies' if use_cookies else 'yt-dlp'}: {video_id}")
                return url
        except Exception as e:
            logger.warning(f"Stream error: {e}")
        
        if RAILWAY_YT_API_URL and RAILWAY_YT_API_KEY:
            try:
                media_url = f"{RAILWAY_YT_API_URL}/{'play/video/hq' if video else 'play/audio'}?id={video_id}"
                async with aiohttp.ClientSession(headers={"X-API-Key": str(RAILWAY_YT_API_KEY)}) as session:
                    async with session.get(media_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status in (200, 206):
                            logger.info(f"✅ Stream via Railway: {video_id}")
                            return media_url
            except Exception as e:
                logger.warning(f"Railway stream error: {e}")
        return None

    async def download(self, video_id, video=False, title=None):
        self.dl_stats["total"] += 1
        link = _normalize_youtube_link(video_id, self.base)
        try:
            result, method = await _download_with_fallback(link, "video" if video else "audio")
            if result:
                self.dl_stats[method] = self.dl_stats.get(method, 0) + 1
            else:
                self.dl_stats["failed"] += 1
            return result
        except Exception as e:
            self.dl_stats["failed"] += 1
            logger.warning(f"Download error: {e}")
            return None

    async def playlist(self, limit, mention, link, video=False):
        from ishu.helpers._dataclass import Track
        link = _normalize_youtube_link(link)
        try:
            plist = await Playlist.get(link)
        except:
            return []
        
        tracks = []
        for data in (plist.get("videos") or [])[:limit]:
            if not data:
                continue
            vid = data.get("id")
            if not vid:
                continue
            dur = data.get("duration", "00:00")
            thumbs = data.get("thumbnails") or []
            tracks.append(Track(
                id=vid, title=data.get("title") or vid, url=data.get("link") or self.base + vid,
                duration=dur, duration_sec=int(utils.to_seconds(dur)) if dur else 0,
                thumbnail=thumbs[0].get("url", "").split("?")[0] if thumbs else "",
                user=mention, video=video, time=int(_time.time()),
                view_count=(data.get("viewCount") or {}).get("short") if isinstance(data.get("viewCount"), dict) else None,
                channel_name=(data.get("channel") or {}).get("name", "")
            ))
        return tracks

    async def formats(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        info = yt_dlp.YoutubeDL(_with_js_runtime({"quiet": True})).extract_info(link, download=False)
        return [{"format": f["format"], "filesize": f.get("filesize"), "format_id": f["format_id"], 
                 "ext": f["ext"], "format_note": f.get("format_note"), "yturl": link} 
                for f in info.get("formats", []) if "dash" not in str(f["format"]).lower()], link

    async def video(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "--js-runtimes", "node", "-g", "-f", "best[height<=?720][width<=?1280]", link,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return 0, "timed out"
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())

    async def get_related(self, video_id, message_id):
        """Get related video - FIXED for float duration"""
        link = self.base + video_id
        loop = asyncio.get_event_loop()
        
        def _run():
            opts = {"quiet": True, "no_warnings": True}
            cookie = cookie_txt_file()
            if cookie and os.environ.get("ALLOW_COOKIE_DOWNLOAD"):
                opts["cookiefile"] = cookie
            info = yt_dlp.YoutubeDL(_with_js_runtime(opts)).extract_info(link, download=False) or {}
            for r in info.get("related_videos") or []:
                if r.get("id") and r["id"] != video_id and "list=" not in (r.get("url") or ""):
                    return r
            return None
        
        try:
            r = await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=15)
        except:
            return None
        
        if not r:
            return None
        rid = r["id"]
        dur = r.get("duration", "00:00")
        # Fix: duration ko int mein convert karo
        try:
            dur_sec = int(float(dur)) if dur else 0
        except (ValueError, TypeError):
            dur_sec = 0
        dur_str = _format_duration(dur_sec)
        
        return Track(
            id=rid, title=r.get("title", "Unknown"), url=r.get("url", self.base + rid),
            duration=dur_str, duration_sec=dur_sec,
            thumbnail=(r.get("thumbnails") or [{}])[0].get("url", "").split("?")[0],
            channel_name=r.get("channel") or r.get("uploader") or "",
            message_id=message_id, video=False, time=int(_time.time())
        )

    async def slider(self, link, query_type, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        raw = (await VideosSearch(link, limit=10).next()).get("result", [])
        filtered = []
        for item in raw:
            dur = item.get("duration", "0:00").split(":")
            secs = int(dur[0]) * 3600 + int(dur[1]) * 60 + int(dur[2]) if len(dur) == 3 else int(dur[0]) * 60 + int(dur[1]) if len(dur) == 2 else 0
            if 0 < secs <= 3600:
                filtered.append(item)
        if not filtered or query_type >= len(filtered):
            raise ValueError("No suitable videos")
        s = filtered[query_type]
        return s["title"], s.get("duration") or "0:00", s["thumbnails"][0]["url"].split("?")[0], s["id"]
