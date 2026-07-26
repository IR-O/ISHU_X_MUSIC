# ishu/youtube.py - FASTEST VERSION (No Cookies)
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

def _format_duration(seconds):
    try:
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
    except Exception:
        return "0:00"

def _with_js_runtime(opts):
    out = dict(opts)
    out["js_runtimes"] = JS_RUNTIMES
    out["socket_timeout"] = 5
    out["retries"] = 1
    out["sleep_interval"] = 0.5
    out["user_agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    out["extractor_args"] = {
        "youtube": {
            "player_client": ["tv"],
            "player_skip": ["webpage", "configs", "hls", "dash"],
            "skip": ["hls", "dash"]
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

# ── Fast Downloaders ────────────────────────────────────────────────────

async def _cookies_download(link, media_type):
    # Cookies disabled for speed
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
                "socket_timeout": 8,
                "retries": 2,
                "extractor_args": {"youtube": {"player_client": ["tv"], "skip": ["hls", "dash"]}}
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
                logger.info(f"✅ Fast download ✓ {video_id}")
                return result
        except Exception as e:
            logger.warning(f"⚠️ Download failed: {e}")
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
                async with session.get(media_url, timeout=aiohttp.ClientTimeout(total=60), allow_redirects=True) as resp:
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
    
    # Only yt-dlp without cookies (fastest)
    result = await _ytdlp_nocookie_download(link, media_type)
    if result:
        return result, "ytdlp"
    
    # Fallback: Railway
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
        self.dl_stats = {"total": 0, "ytdlp": 0, "railway": 0, "failed": 0}

    def _load_cookies(self):
        # Cookies not needed - keeping for compatibility
        pass

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
        """Fast search using yt-dlp"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'socket_timeout': 5,
            'retries': 1,
            'extractor_args': {'youtube': {'player_client': ['tv'], 'skip': ['hls', 'dash']}}
        }
        
        try:
            with yt_dlp.YoutubeDL(_with_js_runtime(ydl_opts)) as ydl:
                info = ydl.extract_info(f"ytsearch2:{query}", download=False)
                results = info.get('entries', [])
                
                for r in results[:2]:
                    vid = r.get('id')
                    if not vid:
                        continue
                    duration = r.get('duration', 0)
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
        """Get direct stream URL - Fastest version"""
        link = _normalize_youtube_link(video_id, self.base)
        
        # Fastest - Direct yt-dlp without cookies
        try:
            ydl_opts = {
                "format": "bestaudio/best" if not video else "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 5,
                "retries": 1,
                "sleep_interval": 0.5,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["tv"],
                        "player_skip": ["webpage", "configs", "hls", "dash"],
                        "skip": ["hls", "dash"]
                    }
                }
            }
            
            loop = asyncio.get_event_loop()
            def _run():
                with yt_dlp.YoutubeDL(_with_js_runtime(ydl_opts)) as ydl:
                    info = ydl.extract_info(link, download=False)
                    # Get direct audio URL
                    url = info.get("url")
                    if not url:
                        formats = info.get("formats") or []
                        for f in formats:
                            if f.get("acodec") != "none" and f.get("vcodec") == "none":
                                url = f.get("url")
                                break
                        if not url and formats:
                            url = formats[-1].get("url")
                    return url
            
            url = await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=8)
            if url:
                logger.info(f"✅ Fast stream: {video_id}")
                return url
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Stream timeout: {video_id}")
        except Exception as e:
            logger.warning(f"Stream error: {e}")
        
        # Fallback: Railway API
        if RAILWAY_YT_API_URL and RAILWAY_YT_API_KEY:
            try:
                media_url = f"{RAILWAY_YT_API_URL}/{'play/video/hq' if video else 'play/audio'}?id={video_id}"
                async with aiohttp.ClientSession(headers={"X-API-Key": str(RAILWAY_YT_API_KEY)}) as session:
                    async with session.get(media_url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        if resp.status in (200, 206):
                            logger.info(f"✅ Railway fallback: {video_id}")
                            return media_url
            except Exception:
                pass
        
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
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return 0, "timed out"
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())

    async def get_related(self, video_id, message_id):
        link = self.base + video_id
        loop = asyncio.get_event_loop()
        
        def _run():
            opts = {"quiet": True, "no_warnings": True, "socket_timeout": 5, "retries": 1}
            info = yt_dlp.YoutubeDL(_with_js_runtime(opts)).extract_info(link, download=False) or {}
            for r in info.get("related_videos") or []:
                if r.get("id") and r["id"] != video_id and "list=" not in (r.get("url") or ""):
                    return r
            return None
        
        try:
            r = await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=8)
        except:
            return None
        
        if not r:
            return None
        rid = r["id"]
        dur = r.get("duration", "00:00")
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
