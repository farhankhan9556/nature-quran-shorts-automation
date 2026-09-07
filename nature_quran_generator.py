#!/usr/bin/env python3
"""
REFERENCE-STYLE ONLINE EARNING SHORTS GENERATOR

Built from the user's existing professional generator, but redesigned around the
uploaded reference video's editing language:
- Portrait 1080x1920 Shorts.
- Full-screen visual footage is the hero; no giant opaque cards covering it.
- Very fast visual changes and short spoken beats.
- Large bold white caption words at the bottom with strong shadow/stroke.
- Small supporting caption above the main word when useful.
- Matching visuals for the exact spoken idea (money, TikTok, laptop, AI, etc.).
- Subtle punch-in / movement, dark vignette, and quick transitions.
- Duration is natural: no forced filler. Usually 10–35 seconds depending on script.
- Daily YouTube trend discovery remains enabled.
- Three original videos per run.
- Metadata follows the actual topic/content.

Keep filename as nature_quran_generator.py if the existing GitHub workflow uses it.
Required GitHub secrets:
  PEXELS_API_KEY
  YOUTUBE_API_KEY
"""

import asyncio
import json
import os
import random
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    import edge_tts
except ImportError:
    edge_tts = None

# ============================================================
# SETTINGS
# ============================================================
W, H, FPS = 1080, 1920, 30
SHORT_COUNT = 3
MAX_SECONDS = 35
MIN_BEAT_SECONDS = 0.72
MAX_BEAT_SECONDS = 3.20

VOICE = "en-US-EricNeural"
VOICE_RATE = "+8%"
VOICE_PITCH = "+3Hz"

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_REGION = os.getenv("YOUTUBE_REGION", "US").strip() or "US"
TREND_WINDOW_DAYS = int(os.getenv("TREND_WINDOW_DAYS", "7"))

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "_work_reference_style"
FONTS_DIR = ROOT / "fonts"
REGULAR_FONT = FONTS_DIR / "NotoSans-Regular.ttf"
BOLD_FONT = FONTS_DIR / "NotoSans-Bold.ttf"
SYSTEM_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
SYSTEM_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# Dark, high-contrast palette inspired by the reference.
BLACK = (3, 5, 10, 255)
WHITE = (255, 255, 255, 255)
MUTED = (215, 220, 230, 255)
ACCENT = (80, 170, 255, 255)
GREEN = (67, 220, 135, 255)
SHADOW = (0, 0, 0, 210)
PANEL = (0, 0, 0, 145)

TREND_QUERIES = [
    "make money online", "online earning tips", "side hustle", "AI earning",
    "affiliate marketing", "freelancing", "TikTok monetization",
    "YouTube Shorts monetization", "digital products", "remote work",
    "online business", "ecommerce tips",
]

TOPICS = {
    "ai": {
        "title": "AI freelancing", "key": "ai-freelancing",
        "keywords": ["AI", "freelancing", "ChatGPT", "clients"],
        "hook": "AI can help you earn — if you use it for a real skill.",
        "beats": [
            ("PICK ONE SKILL", "writing, research, design or admin", "freelancer laptop work"),
            ("USE AI", "to speed up the boring parts", "AI chatbot laptop typing"),
            ("CHECK IT", "never send unverified AI work", "person checking laptop work"),
            ("SELL THE RESULT", "show a sample that solves a client problem", "freelancer client meeting laptop"),
        ],
        "cta": "Save this for your next AI side hustle.",
        "visual_hook": "young freelancer laptop technology work",
    },
    "affiliate": {
        "title": "Affiliate marketing", "key": "affiliate-marketing",
        "keywords": ["affiliate", "product", "link", "commission"],
        "hook": "You can earn from a product without owning the product.",
        "beats": [
            ("PICK A PRODUCT", "choose something people actually need", "online shopping product smartphone"),
            ("GET A LINK", "use a legitimate affiliate program", "smartphone link social media"),
            ("MAKE CONTENT", "show the product honestly", "person reviewing product phone"),
            ("EARN COMMISSION", "when a qualifying purchase happens", "online sales commission money phone"),
        ],
        "cta": "Follow for practical affiliate ideas.",
        "visual_hook": "online shopping smartphone product review",
    },
    "tiktok": {
        "title": "TikTok earning", "key": "tiktok-earning",
        "keywords": ["TikTok", "content", "niche", "monetize"],
        "hook": "Don't chase random views. Build one useful TikTok niche.",
        "beats": [
            ("CHOOSE A NICHE", "make your topic obvious fast", "TikTok creator smartphone vertical video"),
            ("POST USEFUL CONTENT", "teach, compare, demonstrate or review", "social media creator filming phone"),
            ("BUILD AN AUDIENCE", "give people a reason to return", "social media analytics smartphone"),
            ("MONETIZE", "use eligible features, affiliates or services", "TikTok social media analytics phone"),
        ],
        "cta": "Save this before your next TikTok.",
        "visual_hook": "TikTok social media smartphone creator",
    },
    "youtube": {
        "title": "YouTube Shorts", "key": "youtube-shorts",
        "keywords": ["YouTube", "Shorts", "hook", "watch"],
        "hook": "A good Short solves one problem fast.",
        "beats": [
            ("ONE PROBLEM", "give viewers one useful answer", "YouTube Shorts creator smartphone"),
            ("HOOK FAST", "show the promise immediately", "video editing timeline smartphone"),
            ("KEEP MOVING", "change visuals as the idea changes", "content creator editing laptop"),
            ("STAY ORIGINAL", "add your own explanation and examples", "creator recording video laptop"),
        ],
        "cta": "Follow for more Shorts growth ideas.",
        "visual_hook": "YouTube Shorts creator smartphone editing",
    },
    "freelance": {
        "title": "Freelancing", "key": "freelancing",
        "keywords": ["freelance", "skill", "client", "portfolio"],
        "hook": "Your first freelance offer should be easy to understand.",
        "beats": [
            ("PICK ONE SKILL", "start with something you can deliver", "freelancer working laptop home office"),
            ("MAKE ONE OFFER", "sell one clear result", "freelancer portfolio laptop"),
            ("CREATE PROOF", "build useful samples before pitching", "freelancer client presentation"),
            ("CONTACT CLIENTS", "show them the result you can provide", "freelancer business meeting laptop"),
        ],
        "cta": "Save this and build your first sample.",
        "visual_hook": "freelancer laptop home office client",
    },
    "digital": {
        "title": "Digital products", "key": "digital-products",
        "keywords": ["digital product", "template", "guide", "sale"],
        "hook": "A digital product works best when it solves a repeated problem.",
        "beats": [
            ("FIND A PROBLEM", "look for something people repeatedly need", "person planning notes laptop"),
            ("MAKE A RESOURCE", "try a template, checklist or guide", "digital template laptop design"),
            ("TEST IT", "show it to real people first", "small business customer feedback laptop"),
            ("IMPROVE IT", "use feedback before you scale", "digital product creator laptop"),
        ],
        "cta": "Follow for realistic digital business ideas.",
        "visual_hook": "digital product template laptop creator",
    },
    "selling": {
        "title": "Online selling", "key": "online-selling",
        "keywords": ["online store", "sales", "cost", "profit"],
        "hook": "Sales are not profit. Check the numbers first.",
        "beats": [
            ("TEST DEMAND", "start small before buying lots of stock", "ecommerce online store smartphone"),
            ("COUNT EVERY COST", "product, fees, delivery and returns", "calculator ecommerce business money"),
            ("CHECK YOUR MARGIN", "know what is left after costs", "business profit calculator money"),
            ("TRACK REAL PROFIT", "revenue alone is not enough", "online seller package calculator"),
        ],
        "cta": "Save this before you buy your first stock.",
        "visual_hook": "ecommerce shopping packages money calculator",
    },
    "remote": {
        "title": "Remote work", "key": "remote-work",
        "keywords": ["remote job", "CV", "skills", "safe"],
        "hook": "A real remote job should not start with a mystery payment.",
        "beats": [
            ("BUILD A SKILL", "focus on something employers need", "remote worker laptop home office"),
            ("SHOW RESULTS", "use a clear CV and portfolio", "resume CV laptop job application"),
            ("APPLY SAFELY", "use legitimate companies and platforms", "online job search laptop safety"),
            ("NEVER PAY FIRST", "a promised job should not require a stranger's fee", "online job scam warning laptop"),
        ],
        "cta": "Share this with someone looking for remote work.",
        "visual_hook": "remote worker laptop home office job search",
    },
    "pod": {
        "title": "Print on demand", "key": "print-on-demand",
        "keywords": ["print on demand", "design", "shirt", "niche"],
        "hook": "You can test designs without storing a warehouse of stock.",
        "beats": [
            ("CHOOSE A NICHE", "design for a specific audience", "designer t shirt ecommerce laptop"),
            ("CREATE ORIGINAL WORK", "avoid copyrighted characters and logos", "graphic designer creating t shirt"),
            ("LIST THE DESIGN", "show it clearly to your audience", "online store t shirt product page"),
            ("TEST DEMAND", "improve what people respond to", "online store t shirt order package"),
        ],
        "cta": "Follow for practical ecommerce ideas.",
        "visual_hook": "print on demand t shirt ecommerce design",
    },
    "general": {
        "title": "Online earning", "key": "online-earning",
        "keywords": ["money", "skill", "problem", "results"],
        "hook": "Ignore easy-money hype. Start with a real problem.",
        "beats": [
            ("CHOOSE ONE SKILL", "pick something you can improve", "person learning laptop online course"),
            ("SOLVE ONE PROBLEM", "make the offer specific and useful", "small business problem solving laptop"),
            ("TEST THE MARKET", "learn from real people", "small business customer feedback"),
            ("IMPROVE", "use real results instead of hype", "young entrepreneur laptop business"),
        ],
        "cta": "Save this if you want realistic earning ideas.",
        "visual_hook": "money laptop online business young entrepreneur",
    },
}

# ============================================================
# UTILITIES
# ============================================================
def run(cmd, check=True, capture=False):
    print("$", " ".join(str(x) for x in cmd))
    return subprocess.run(
        [str(x) for x in cmd], check=check, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def require_program(name):
    if shutil.which(name) is None:
        raise RuntimeError(f"Required program not found: {name}")


def font_path(bold=False):
    p = BOLD_FONT if bold else REGULAR_FONT
    fallback = SYSTEM_BOLD if bold else SYSTEM_REGULAR
    return str(p if p.exists() else fallback)


def F(size, bold=False):
    return ImageFont.truetype(font_path(bold), size)


def text_width(draw, text, font, stroke=0):
    b = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    return b[2] - b[0]


def wrap(draw, text, font, max_width, stroke=0):
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = f"{line} {word}".strip()
        if text_width(draw, test, font, stroke) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def safe_slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# ============================================================
# YOUTUBE TREND DISCOVERY
# ============================================================
def youtube_get(path, params):
    url = f"https://www.googleapis.com/youtube/v3/{path}"
    p = dict(params)
    p["key"] = YOUTUBE_API_KEY
    r = requests.get(url, params=p, timeout=30)
    r.raise_for_status()
    return r.json()


def topic_from_title(title):
    t = title.lower()
    mapping = [
        ("chatgpt", "ai"), ("ai", "ai"), ("automation", "ai"),
        ("affiliate", "affiliate"), ("amazon associates", "affiliate"),
        ("tiktok", "tiktok"), ("youtube", "youtube"), ("shorts", "youtube"),
        ("freelanc", "freelance"), ("fiverr", "freelance"), ("upwork", "freelance"),
        ("digital product", "digital"), ("template", "digital"),
        ("ecommerce", "selling"), ("shopify", "selling"), ("dropship", "selling"),
        ("remote job", "remote"), ("remote work", "remote"), ("work from home", "remote"),
        ("print on demand", "pod"), ("merch", "pod"),
    ]
    for word, key in mapping:
        if word in t:
            return key
    return "general"


def discover_topics():
    if not YOUTUBE_API_KEY:
        keys = random.sample(list(TOPICS), SHORT_COUNT)
        return [dict(TOPICS[k]) for k in keys]

    since = datetime.now(timezone.utc) - timedelta(days=max(1, TREND_WINDOW_DAYS))
    published_after = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    queries = random.sample(TREND_QUERIES, min(4, len(TREND_QUERIES)))
    candidates = {}

    for q in queries:
        try:
            data = youtube_get("search", {
                "part": "snippet", "q": q, "type": "video",
                "order": random.choice(["viewCount", "date"]),
                "publishedAfter": published_after, "maxResults": 12,
                "regionCode": YOUTUBE_REGION, "relevanceLanguage": "en",
                "safeSearch": "moderate",
            })
        except Exception as exc:
            print("YouTube search failed:", exc)
            continue
        for item in data.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if not vid:
                continue
            sn = item.get("snippet", {})
            candidates[vid] = {
                "title": sn.get("title", ""),
                "published": sn.get("publishedAt", ""),
            }

    if not candidates:
        return [dict(TOPICS[k]) for k in random.sample(list(TOPICS), SHORT_COUNT)]

    ids = list(candidates)[:50]
    try:
        stats = youtube_get("videos", {"part": "statistics,snippet", "id": ",".join(ids)})
    except Exception as exc:
        print("YouTube statistics failed:", exc)
        return [dict(TOPICS[k]) for k in random.sample(list(TOPICS), SHORT_COUNT)]

    now = datetime.now(timezone.utc)
    scored = []
    for item in stats.get("items", []):
        vid = item.get("id")
        base = candidates.get(vid, {})
        title = base.get("title", "")
        try:
            views = int(item.get("statistics", {}).get("viewCount", 0) or 0)
        except Exception:
            views = 0
        pub = item.get("snippet", {}).get("publishedAt") or base.get("published")
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            age_h = max(1.0, (now - dt).total_seconds() / 3600)
        except Exception:
            age_h = max(24.0, TREND_WINDOW_DAYS * 24.0)
        likes = int(item.get("statistics", {}).get("likeCount", 0) or 0)
        comments = int(item.get("statistics", {}).get("commentCount", 0) or 0)
        velocity = views / age_h
        engagement = ((likes * 2) + (comments * 5)) / max(views, 1) * 100000
        scored.append((velocity + engagement, title, views, age_h, vid))

    scored.sort(reverse=True, key=lambda x: x[0])
    selected, used = [], set()
    for score, title, views, age_h, vid in scored:
        key = topic_from_title(title)
        if key in used:
            continue
        topic = dict(TOPICS[key])
        topic.update({
            "trend_source_title": title, "trend_views": views,
            "trend_age_hours": round(age_h, 1), "trend_score": round(score, 2),
            "trend_video_id": vid,
        })
        selected.append(topic)
        used.add(key)
        print(f"TREND: {key} | {views:,} views | {age_h:.1f}h | {title[:90]}")
        if len(selected) >= SHORT_COUNT:
            break

    if len(selected) < SHORT_COUNT:
        remaining = [dict(TOPICS[k]) for k in TOPICS if k not in used]
        random.shuffle(remaining)
        selected.extend(remaining[:SHORT_COUNT - len(selected)])
    return selected[:SHORT_COUNT]

# ============================================================
# PEXELS
# ============================================================
def pexels_json(endpoint, params):
    if not PEXELS_API_KEY:
        return {}
    r = requests.get(
        f"https://api.pexels.com/v1/{endpoint}",
        headers={"Authorization": PEXELS_API_KEY}, params=params, timeout=30,
    )
    r.raise_for_status()
    return r.json()


def download_url(url, path):
    try:
        r = requests.get(url, timeout=60, stream=True)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(262144):
                if chunk:
                    f.write(chunk)
        return path if path.exists() and path.stat().st_size > 10000 else None
    except Exception as exc:
        print("download failed:", exc)
        return None


def pexels_video(query, path):
    try:
        data = pexels_json("videos/search", {
            "query": query, "orientation": "portrait", "size": "medium", "per_page": 10,
        })
    except Exception as exc:
        print("Pexels video search failed:", exc)
        return None
    videos = data.get("videos", [])
    random.shuffle(videos)
    for v in videos:
        files = [x for x in v.get("video_files", []) if x.get("link")]
        portrait = [x for x in files if (x.get("height") or 0) >= (x.get("width") or 0)]
        candidates = portrait or files
        candidates.sort(key=lambda x: abs((x.get("height") or 1080) - 1920))
        for vf in candidates[:3]:
            got = download_url(vf["link"], path)
            if got:
                return got
    return None


def pexels_photo(query, path):
    try:
        data = pexels_json("search", {
            "query": query, "orientation": "portrait", "size": "large", "per_page": 10,
        })
    except Exception as exc:
        print("Pexels photo search failed:", exc)
        return None
    photos = data.get("photos", [])
    random.shuffle(photos)
    for p in photos:
        src = p.get("src", {})
        link = src.get("large2x") or src.get("large") or src.get("original")
        if link:
            got = download_url(link, path)
            if got:
                return got
    return None


def get_visual(query, folder, index):
    # Alternate video/photo to keep the edit feeling alive.
    if index % 2:
        return pexels_video(query, folder / f"visual_{index}.mp4")
    return pexels_photo(query, folder / f"visual_{index}.jpg")

# ============================================================
# VOICE
# ============================================================
async def tts_async(text, out):
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed.")
    communicate = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE, pitch=VOICE_PITCH)
    await communicate.save(str(out))


def make_voice(text, out):
    asyncio.run(tts_async(text, out))


def media_duration(path):
    r = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ], capture=True)
    return float(r.stdout.strip())

# ============================================================
# REFERENCE-STYLE GRAPHICS
# ============================================================
def base_overlay(topic, label, main_words, subtext, progress):
    """Transparent overlay: footage remains visible everywhere except a subtle caption zone."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Top micro-label. Minimal, not a title card.
    d.rounded_rectangle((48, 54, 310, 104), 25, fill=(0, 0, 0, 125), outline=(255,255,255,55), width=2)
    d.text((72, 65), "EARN SMART", font=F(24, True), fill=WHITE)

    # Thin progress line like a modern short-form edit.
    d.rounded_rectangle((48, 122, 1032, 128), 3, fill=(255,255,255,65))
    d.rounded_rectangle((48, 122, 48 + int(984 * progress), 128), 3, fill=WHITE)

    # Soft bottom gradient/panel. Keeps the actual visual visible.
    panel = Image.new("RGBA", (W, H), (0,0,0,0))
    pd = ImageDraw.Draw(panel)
    for i in range(620):
        alpha = int(150 * (i / 620) ** 1.7)
        y = H - 620 + i
        pd.line((0, y, W, y), fill=(0,0,0,alpha))
    img.alpha_composite(panel)
    d = ImageDraw.Draw(img)

    # Small contextual label.
    d.text((70, H - 565), label.upper(), font=F(28, True), fill=ACCENT,
           stroke_width=2, stroke_fill=(0,0,0,220))

    # Main reference-like bold caption. It can be one word or a short phrase.
    font = F(86 if len(main_words) <= 11 else 68, True)
    lines = wrap(d, main_words.upper(), font, 940, stroke=5)
    y = H - 475
    for line in lines[-2:]:
        tw = text_width(d, line, font, stroke=5)
        x = (W - tw) / 2
        d.text((x + 4, y + 6), line, font=font, fill=(0,0,0,235),
               stroke_width=9, stroke_fill=(0,0,0,220))
        d.text((x, y), line, font=font, fill=WHITE,
               stroke_width=5, stroke_fill=(0,0,0,255))
        y += font.size + 8

    # Short support line.
    support_font = F(31, False)
    sub_lines = wrap(d, subtext, support_font, 900, stroke=2)[:2]
    yy = H - 210
    for line in sub_lines:
        tw = text_width(d, line, support_font, stroke=2)
        d.text(((W-tw)/2, yy), line, font=support_font, fill=MUTED,
                stroke_width=2, stroke_fill=(0,0,0,220))
        yy += 40

    # Tiny beat marker.
    d.ellipse((48, H-68, 64, H-52), fill=GREEN)
    d.text((78, H-82), f"{topic['title']}  •  {int(progress*100)}%", font=F(22, True), fill=WHITE,
           stroke_width=1, stroke_fill=(0,0,0,180))
    return img


def render_overlay(topic, beat, beat_index, total):
    label, detail, _ = beat
    return base_overlay(topic, label, label, detail, beat_index / max(1, total))


def render_hook_overlay(topic, total):
    # Hook gets an even bigger caption and no clutter.
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((48,54,310,104),25,fill=(0,0,0,125),outline=(255,255,255,55),width=2)
    d.text((72,65), "EARN SMART", font=F(24,True), fill=WHITE)
    d.rounded_rectangle((48,122,1032,128),3,fill=(255,255,255,65))
    d.rounded_rectangle((48,122,48+int(984/total),128),3,fill=WHITE)

    # Strong centered hook, with a dark readability area but still transparent.
    d.rounded_rectangle((54, H-880, W-54, H-330), 34, fill=(0,0,0,120), outline=(255,255,255,40), width=2)
    lines = wrap(d, topic["hook"].upper(), F(86,True), 900, stroke=5)
    y = H-810
    for line in lines[:4]:
        tw = text_width(d,line,F(86,True),stroke=5)
        d.text(((W-tw)/2,y),line,font=F(86,True),fill=WHITE,stroke_width=5,stroke_fill=(0,0,0,255))
        y += 100
    d.text((75,H-275), "WATCH • LEARN • APPLY", font=F(27,True), fill=ACCENT,
           stroke_width=2,stroke_fill=(0,0,0,220))
    return img

# ============================================================
# VIDEO PREPARATION
# ============================================================
def prepare_visual_clip(path, out, duration, variant=0):
    if path is None or not Path(path).exists():
        return None
    ext = Path(path).suffix.lower()
    # Slightly different zoom/crop each beat avoids a repetitive template feel.
    zoom = 1.04 + (variant % 3) * 0.02
    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        frames = (
            f"scale=1320:2346:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min({zoom}+on*0.00045,{zoom+0.045})':d={max(1,int(duration*FPS))}:s=1080x1920:fps={FPS},"
            "eq=brightness=-0.03:saturation=1.02,format=yuv420p"
        )
        run(["ffmpeg","-y","-loop","1","-i",path,"-t",f"{duration:.3f}","-vf",frames,
             "-an","-c:v","libx264","-preset","veryfast","-crf","24",out])
    else:
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "eq=brightness=-0.025:saturation=1.02,format=yuv420p"
        )
        run(["ffmpeg","-y","-stream_loop","-1","-i",path,"-t",f"{duration:.3f}","-vf",vf,
             "-an","-c:v","libx264","-preset","veryfast","-crf","24",out])
    return out


def make_scene_video(card, visual, voice, duration, out, beat_index=0):
    # Quick fade in/out on the transparent overlay + visual; the footage stays dominant.
    card_png = str(card)
    fade_out = max(0.18, duration - 0.18)
    if visual and Path(visual).exists():
        fc = (
            "[0:v]format=yuv420p,"
            f"fade=t=in:st=0:d=0.10,fade=t=out:st={fade_out:.3f}:d=0.16[v0];"
            "[1:v]format=rgba,"
            "fade=t=in:st=0:d=0.10:alpha=1,"
            f"fade=t=out:st={fade_out:.3f}:d=0.16:alpha=1[ov];"
            "[v0][ov]overlay=0:0:format=auto,format=yuv420p[v]"
        )
        run(["ffmpeg","-y","-i",visual,"-loop","1","-i",card_png,"-i",voice,
             "-t",f"{duration:.3f}","-filter_complex",fc,
             "-map","[v]","-map","2:a","-c:v","libx264","-preset","veryfast",
             "-crf","23","-c:a","aac","-b:a","128k","-shortest",out])
    else:
        run(["ffmpeg","-y","-loop","1","-i",card_png,"-i",voice,"-t",f"{duration:.3f}",
             "-vf","format=yuv420p","-map","0:v","-map","1:a","-c:v","libx264",
             "-preset","veryfast","-crf","23","-c:a","aac","-b:a","128k","-shortest",out])


def concat_videos(files, output):
    list_file = output.parent / "concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"file '{Path(p).resolve()}'\n")
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",list_file,
         "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac",
         "-b:a","128k","-movflags","+faststart",output])


def add_music(video, out, duration, folder):
    # Quiet simple bed. Narration remains clearly dominant.
    music = folder / "music.m4a"
    run(["ffmpeg","-y","-f","lavfi","-i","sine=frequency=196:sample_rate=44100",
         "-t",f"{duration:.2f}","-af",f"volume=0.012,afade=t=in:st=0:d=0.3,afade=t=out:st={max(0.4,duration-0.6):.2f}:d=0.6",
         "-c:a","aac","-b:a","64k",music])
    run(["ffmpeg","-y","-i",video,"-i",music,
         "-filter_complex","[1:a]volume=0.55[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=1[a]",
         "-map","0:v","-map","[a]","-t",f"{duration:.2f}","-c:v","copy","-c:a","aac",
         "-b:a","128k","-movflags","+faststart",out])

# ============================================================
# BEAT CREATION
# ============================================================
def hook_beats(topic):
    """Split the hook into a few natural spoken chunks so visuals can change quickly."""
    h = topic["hook"].replace("—", ",").replace(".", "")
    parts = [x.strip() for x in re.split(r",|;|\band\b", h, flags=re.I) if x.strip()]
    if len(parts) < 2:
        words = h.split()
        mid = max(3, len(words)//2)
        parts = [" ".join(words[:mid]), " ".join(words[mid:])]
    return parts[:3]


def build_beats(topic):
    beats = []
    hook_parts = hook_beats(topic)
    for i, text in enumerate(hook_parts):
        beats.append({
            "kind": "hook", "speech": text + ("." if not text.endswith(".") else ""),
            "label": "HOOK", "caption": text, "detail": "Stay for the practical steps.",
            "query": topic["visual_hook"],
        })
    for label, detail, query in topic["beats"]:
        speech = f"{label.title().replace(' ', ' ')}: {detail}."
        # Main caption is the exact action phrase, not an unrelated headline.
        beats.append({"kind":"step","speech":speech,"label":label,"caption":label,
                      "detail":detail,"query":query})
    beats.append({"kind":"cta","speech":topic["cta"],"label":"NEXT STEP","caption":"SAVE THIS",
                  "detail":topic["cta"],"query":topic["visual_hook"]})
    return beats

# ============================================================
# METADATA
# ============================================================
def write_metadata(topic, output_file, duration):
    title = f"{topic['title']}: {topic['hook']} #shorts"
    topic_tag = safe_slug(topic["key"]).replace("-", "")
    hashtags = ["#shorts", "#onlineearning", "#sidehustle", "#makemoneyonline", f"#{topic_tag}"]
    description = (
        f"{topic['title']} — practical online earning content.\n\n"
        f"This Short covers: {', '.join(topic['keywords'])}.\n\n"
        "Educational content only. No income is guaranteed; results vary by skill, effort, market, location and eligibility.\n\n"
        "Visuals provided by Pexels: https://www.pexels.com/\n\n"
        + " ".join(hashtags)
    )
    tags = list(dict.fromkeys([
        topic["title"].lower(), "online earning", "make money online", "side hustle",
        "earning tips", "online business", "money tips", "shorts", "youtube shorts",
        *[x.lower() for x in topic["keywords"]],
    ]))
    data = {
        "title": title, "description": description, "hashtags": hashtags, "tags": tags,
        "topic": topic["title"], "keywords": topic["keywords"],
        "duration_seconds": round(duration, 2), "voice": VOICE,
        "trend_source_title": topic.get("trend_source_title"),
        "trend_views": topic.get("trend_views"), "trend_age_hours": topic.get("trend_age_hours"),
        "trend_score": topic.get("trend_score"), "original_content": True,
        "reference_style": "fast-cut portrait footage + bold bottom captions",
        "note": "Trend-inspired original educational Short; no income is guaranteed.",
    }
    output_file.with_suffix(".txt").write_text(json.dumps(data, indent=2), encoding="utf-8")

# ============================================================
# CREATE SHORT
# ============================================================
def create_short(topic, number):
    folder = WORK_DIR / f"video_{number}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)

    beats = build_beats(topic)
    total = len(beats)
    scene_files = []
    media_cache = {}

    # Search/download one visual for every conceptual beat. Queries are exact to the spoken idea.
    for i, beat in enumerate(beats, start=1):
        q = beat["query"]
        # Reuse hook visual only for CTA to reduce API load.
        if q in media_cache:
            media = media_cache[q]
        else:
            media = get_visual(q, folder, i)
            media_cache[q] = media
        beat["media"] = media

    for i, beat in enumerate(beats, start=1):
        card_path = folder / f"overlay_{i}.png"
        voice_path = folder / f"voice_{i}.mp3"
        prepared_path = folder / f"prepared_{i}.mp4"
        scene_path = folder / f"scene_{i}.mp4"

        make_voice(beat["speech"], voice_path)
        vd = media_duration(voice_path)
        duration = max(MIN_BEAT_SECONDS, min(MAX_BEAT_SECONDS, vd + 0.06))

        if beat["kind"] == "hook":
            # First hook beat gets the large reference-style opener; later hook beats use normal captions.
            if i == 1:
                overlay = render_hook_overlay(topic, total)
            else:
                fake = (beat["label"], beat["detail"], beat["query"])
                overlay = render_overlay(topic, fake, i, total)
        elif beat["kind"] == "step":
            fake = (beat["label"], beat["detail"], beat["query"])
            overlay = render_overlay(topic, fake, i, total)
        else:
            fake = (beat["label"], beat["detail"], beat["query"])
            overlay = render_overlay(topic, fake, i, total)

        overlay.save(card_path, "PNG")
        prepared = None
        if beat.get("media"):
            prepared = prepare_visual_clip(beat["media"], prepared_path, duration, variant=i)
        make_scene_video(card_path, prepared, voice_path, duration, scene_path, i)
        scene_files.append(scene_path)

    joined = folder / "joined.mp4"
    concat_videos(scene_files, joined)
    duration = media_duration(joined)

    # Keep natural duration, but prevent an accidental long result.
    if duration > MAX_SECONDS:
        factor = duration / MAX_SECONDS
        fixed = folder / "fixed.mp4"
        atempo = max(0.5, min(2.0, factor))
        run(["ffmpeg","-y","-i",joined,
             "-filter_complex",f"[0:v]setpts=PTS/{factor}[v];[0:a]atempo={atempo}[a]",
             "-map","[v]","-map","[a]","-c:v","libx264","-preset","veryfast","-crf","23",
             "-c:a","aac","-b:a","128k","-movflags","+faststart",fixed])
        shutil.copy2(fixed, joined)
        duration = media_duration(joined)

    final = folder / "final.mp4"
    add_music(joined, final, duration, folder)

    output = OUTPUT_DIR / f"online_earning_short_{number}.mp4"
    shutil.copy2(final, output)
    write_metadata(topic, output, duration)
    print(f"CREATED: {output} | {duration:.1f}s | {topic['title']} | {total} beats")
    return output

# ============================================================
# MAIN
# ============================================================
def main():
    require_program("ffmpeg")
    require_program("ffprobe")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    for p in OUTPUT_DIR.glob("online_earning_short_*.mp4"):
        p.unlink(missing_ok=True)
    for p in OUTPUT_DIR.glob("online_earning_short_*.txt"):
        p.unlink(missing_ok=True)

    selected = discover_topics()
    print("\nSELECTED TOPICS:")
    for i, topic in enumerate(selected, 1):
        print(f"{i}. {topic['title']} | trend={topic.get('trend_source_title', 'fallback')}")

    made = []
    for i, topic in enumerate(selected, 1):
        try:
            made.append(create_short(topic, i))
        except Exception as exc:
            print(f"ERROR video {i}: {exc}")

    print("\n" + "=" * 70)
    print(f"FINISHED: {len(made)}/{SHORT_COUNT}")
    for p in made:
        print(p)


if __name__ == "__main__":
    main()
