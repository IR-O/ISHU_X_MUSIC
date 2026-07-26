# ishu/youtube.py - ERROR FREE WITH COOKIES
import asyncio
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
DOWNLOAD_DIR = "downloads"

_dl_locks = {}
JS_RUNTIMES = {"node": {}}

# ── Cache System ────────────────────────────────────────────────────────
_stream_cache = {}
_cache_ttl = 300  # 5 minutes

def _get_cached(video_id):
    """Get cached URL if valid"""
    if video_id in _stream_cache:
        url, timestamp = _stream_cache[video_id]
        if _time.time() - timestamp < _cache_ttl:
            return url
        else:
            del _stream_cache[video_id]
    return None

def _cache_url(video_id, url):
    """Cache stream URL"""
    _stream_cache[video_id] = (url, _time.time())

# ── Cookie Helper ──────────────────────────────────────────────────────
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
    return None

# ── Fast yt-dlp Options ──────────────────────────────────────────────
def _with_js_runtime(opts):
    out = dict(opts)
    out["js_runtimes"] = JS_RUNTIMES
    out["socket_timeout"] = 8
    out["retries"] = 2
    out["sleep_interval"] = 0.5
    out["user_agent"] = "Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
    
    use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
    
    if use_cookies:
        out["extractor_args"] = {
            "youtube": {
                "player_client": ["mweb"],
                "player_skip": ["webpage", "configs"],
                "skip": ["hls", "dash"]
            }
        }
    else:
        out["extractor_args"] = {
            "youtube": {
                "player_client": ["tv", "ios", "android"],
                "player_skip": ["webpage", "configs"],
                "skip": ["hls", "dash"]
            }
        }
    
    proxy = os.environ.get("YTDLP_PROXY")
    if proxy:
        out["proxy"] = proxy
    return out

# ── Format Duration (FIXED) ──────────────────────────────────────────
def _format_duration(seconds):
    try:
        if isinstance(seconds, float):
            seconds = int(seconds)
        elif isinstance(seconds, str):
            seconds = int(float(seconds))
        if seconds < 0:
            seconds = 0
        if seconds < 60:
            return f"0:{seconds:02d}"
        elif seconds < 3600:
            return f"{seconds//60}:{seconds%60:02d}"
        else:
            return f"{seconds//3600}:{(seconds%3600)//60:02d}:{seconds%60:02d}"
    except Exception:
        return "0:00"

# ── Link Helpers ──────────────────────────────────────────────────────
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

# ── Fast Stream URL ──────────────────────────────────────────────────
async def _get_stream_url(video_id, video=False):
    link = f"https://www.youtube.com/watch?v={video_id}"
    
    cached = _get_cached(video_id)
    if cached:
        logger.info(f"⚡ Cache hit: {video_id}")
        return cached
    
    try:
        loop = asyncio.get_event_loop()
        
        def _run():
            opts = {
                "format": "bestaudio/best" if not video else "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 8,
                "retries": 2,
                "sleep_interval": 0.5,
                "extract_flat": True,
                "js_runtimes": JS_RUNTIMES,
                "user_agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
            }
            
            use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
            if use_cookies:
                cookie_file = cookie_txt_file()
                if cookie_file and os.path.exists(cookie_file):
                    opts["cookiefile"] = cookie_file
                    opts["extractor_args"] = {
                        "youtube": {
                            "player_client": ["mweb"],
                            "player_skip": ["webpage", "configs"],
                            "skip": ["hls", "dash"]
                        }
                    }
                else:
                    opts["extractor_args"] = {
                        "youtube": {
                            "player_client": ["tv", "ios", "android"],
                            "player_skip": ["webpage", "configs"],
                            "skip": ["hls", "dash"]
                        }
                    }
            else:
                opts["extractor_args"] = {
                    "youtube": {
                        "player_client": ["tv", "ios", "android"],
                        "player_skip": ["webpage", "configs"],
                        "skip": ["hls", "dash"]
                    }
                }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False)
                url = info.get("url")
                if not url:
                    formats = info.get("formats") or []
                    for f in formats:
                        if f.get("acodec") != "none" and f.get("vcodec") == "none":
                            url = f.get("url")
                            break
                    if not url and formats:
                        url = formats[0].get("url")
                return url
        
        url = await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=2)
        if url:
            _cache_url(video_id, url)
            logger.info(f"⚡ New: {video_id}")
            return url
            
    except asyncio.TimeoutError:
        logger.warning(f"⏰ Timeout: {video_id}")
    except Exception as e:
        logger.warning(f"Error: {e}")
    
    if RAILWAY_YT_API_URL and RAILWAY_YT_API_KEY:
        try:
            endpoint = "play/video/hq" if video else "play/audio"
            media_url = f"{RAILWAY_YT_API_URL}/{endpoint}?id={video_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.head(media_url, timeout=1) as resp:
                    if resp.status in (200, 206):
                        _cache_url(video_id, media_url)
                        logger.info(f"⚡ Railway: {video_id}")
                        return media_url
        except Exception:
            pass
    
    return None

# ── YouTube Class ───────────────────────────────────────────────────────

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        self.cookies_dir = os.path.join(os.path.dirname(__file__), "..", "cookies")
        self._load_cookies()
        self.dl_stats = {"total": 0, "cache": 0, "new": 0, "failed": 0}

    def _load_cookies(self):
        import base64, gzip, re, time
        
        def _write(decoded, src):
            os.makedirs(self.cookies_dir, exist_ok=True)
            cookie_path = os.path.join(self.cookies_dir, "cookie_0.txt")
            with open(cookie_path, "w") as f:
                f.write(decoded)
            
            if "youtube.com" in decoded:
                now = int(time.time())
                expired = re.findall(r'\.youtube\.com\s+TRUE\s+/\s+FALSE\s+(\d+)\s+', decoded)
                if expired:
                    valid = [e for e in expired if int(e) > now]
                    logger.info(f"✅ Cookies loaded: {len(valid)}/{len(expired)} valid from {src}")
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

    async def get_stream_url(self, video_id, video=False, force_cookies=False):
        self.dl_stats["total"] += 1
        
        cached = _get_cached(video_id)
        if cached:
            self.dl_stats["cache"] += 1
            return cached
        
        url = await _get_stream_url(video_id, video)
        if url:
            self.dl_stats["new"] += 1
            return url
        
        self.dl_stats["failed"] += 1
        return None

    async def search(self, query, message_id, video=False):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'socket_timeout': 3,
            'retries': 1,
        }
        
        use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
        if use_cookies:
            cookie_file = cookie_txt_file()
            if cookie_file and os.path.exists(cookie_file):
                ydl_opts["cookiefile"] = cookie_file
                ydl_opts["extractor_args"] = {
                    "youtube": {
                        "player_client": ["mweb"],
                        "skip": ["hls", "dash"]
                    }
                }
            else:
                ydl_opts["extractor_args"] = {
                    "youtube": {
                        "player_client": ["tv", "ios", "android"],
                        "skip": ["hls", "dash"]
                    }
                }
        else:
            ydl_opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["tv", "ios", "android"],
                    "skip": ["hls", "dash"]
                }
            }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch2:{query}", download=False)
                results = info.get('entries', [])
                
                for r in results[:1]:
                    vid = r.get('id')
                    if not vid:
                        continue
                    duration = r.get('duration', 0)
                    # FIXED: Float error handle
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

    async def download(self, video_id, video=False, title=None):
        return await self.get_stream_url(video_id, video)

    async def details(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True, 'socket_timeout': 3}
            use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
            if use_cookies:
                cookie_file = cookie_txt_file()
                if cookie_file and os.path.exists(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                dur = info.get("duration", 0)
                return info.get("title", "Unknown"), _format_duration(dur), dur, f"https://img.youtube.com/vi/{info.get('id')}/hqdefault.jpg", info.get("id", "")
        except Exception:
            return "Unknown", "0:00", 0, "", ""

    async def title(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
            use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
            if use_cookies:
                cookie_file = cookie_txt_file()
                if cookie_file and os.path.exists(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                return info.get("title")
        except Exception:
            return None

    async def playlist(self, limit, mention, link, video=False):
        from ishu.helpers._dataclass import Track
        link = _normalize_youtube_link(link)
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
            use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
            if use_cookies:
                cookie_file = cookie_txt_file()
                if cookie_file and os.path.exists(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                entries = info.get('entries', [])[:limit]
                
                tracks = []
                for data in entries:
                    vid = data.get("id")
                    if not vid:
                        continue
                    dur = data.get("duration", 0)
                    dur_str = _format_duration(dur)
                    tracks.append(Track(
                        id=vid, 
                        title=data.get("title") or vid, 
                        url=f"https://youtube.com/watch?v={vid}",
                        duration=dur_str, 
                        duration_sec=dur,
                        thumbnail=f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                        user=mention, 
                        video=video, 
                        time=int(_time.time()),
                        channel_name=data.get("channel", "")
                    ))
                return tracks
        except Exception:
            return []

    async def get_related(self, video_id, message_id):
        link = self.base + video_id
        loop = asyncio.get_event_loop()
        
        def _run():
            opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "socket_timeout": 3}
            use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
            if use_cookies:
                cookie_file = cookie_txt_file()
                if cookie_file and os.path.exists(cookie_file):
                    opts["cookiefile"] = cookie_file
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False) or {}
                for r in info.get("related_videos") or []:
                    if r.get("id") and r["id"] != video_id and "list=" not in (r.get("url") or ""):
                        return r
            return None
        
        try:
            r = await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=3)
        except:
            return None
        
        if not r:
            return None
        rid = r["id"]
        dur = r.get("duration", 0)
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

    async def formats(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
        use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
        if use_cookies:
            cookie_file = cookie_txt_file()
            if cookie_file and os.path.exists(cookie_file):
                ydl_opts["cookiefile"] = cookie_file
        
        info = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)
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
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return 0, "timed out"
        return (1, stdout.decode().split("\n")[0]) if stdout else (0, stderr.decode())

    async def slider(self, link, query_type, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
        use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
        if use_cookies:
            cookie_file = cookie_txt_file()
            if cookie_file and os.path.exists(cookie_file):
                ydl_opts["cookiefile"] = cookie_file
        
        info = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)
        entries = info.get('entries', [])
        if entries and query_type < len(entries):
            s = entries[query_type]
            dur = s.get("duration", 0)
            return s.get("title", "Unknown"), _format_duration(dur), f"https://img.youtube.com/vi/{s.get('id')}/hqdefault.jpg", s.get("id")
        raise ValueError("No suitable videos")

    async def thumbnail(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        try:
            ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
            use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
            if use_cookies:
                cookie_file = cookie_txt_file()
                if cookie_file and os.path.exists(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file
            
            info = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)
            return f"https://img.youtube.com/vi/{info.get('id')}/hqdefault.jpg"
        except Exception:
            return None

    async def track(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        try:
            ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
            use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
            if use_cookies:
                cookie_file = cookie_txt_file()
                if cookie_file and os.path.exists(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file
            
            info = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)
            vid = info.get("id")
            if vid:
                return {"title": info.get("title", "Unknown"), "link": link, "vidid": vid, 
                        "duration_min": _format_duration(info.get("duration", 0)), 
                        "thumb": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"}, vid
        except Exception:
            pass
        return None, None

    async def duration(self, link, videoid=None):
        if videoid:
            link = self.base + link
        link = _normalize_youtube_link(link)
        try:
            ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
            use_cookies = os.environ.get("ALLOW_COOKIE_DOWNLOAD") == "1"
            if use_cookies:
                cookie_file = cookie_txt_file()
                if cookie_file and os.path.exists(cookie_file):
                    ydl_opts["cookiefile"] = cookie_file
            
            info = yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=False)
            return _format_duration(info.get("duration", 0))
        except Exception:
            return None
