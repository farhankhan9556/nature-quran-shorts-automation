#!/usr/bin/env python3
"""
Professional Online-Earning Shorts Generator

Design goals:
- Daily YouTube trend discovery for online-earning topics.
- Three ORIGINAL Shorts per run; trend titles are inspiration only.
- Multiple 2–4 second visual scenes per Short.
- Scene visuals are matched to the spoken idea (money -> money visuals,
  TikTok -> TikTok/social visuals, freelancing -> laptop/client visuals, etc.).
- Mixes Pexels video clips and photos with subtle Ken Burns motion.
- Professional editorial layout: cards, step numbers, progress bar,
  keyword highlights, animated arrows, transitions, and clean captions.
- Natural youthful male TTS using Microsoft/Edge TTS.
- Flexible duration, normally ~18–35 seconds; never pads a video with filler.
- Metadata is generated from the exact topic/angle used in the video.

GitHub Actions secrets:
  PEXELS_API_KEY
  YOUTUBE_API_KEY

Keep the filename as nature_quran_generator.py if the existing workflow calls it.
"""

import asyncio
import json
import math
import os
import random
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

try:
    import edge_tts
except ImportError:
    edge_tts = None

# ============================================================
# SETTINGS
# ============================================================
W, H, FPS = 1080, 1920, 30
SHORT_COUNT = 3
MIN_SECONDS = 18
MAX_SECONDS = 35

# Eric is a standard US male voice. A modest pitch/rate change makes it
# brighter/younger without trying to imitate a child.
VOICE = "en-US-EricNeural"
VOICE_RATE = "+8%"
VOICE_PITCH = "+3Hz"

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_REGION = os.getenv("YOUTUBE_REGION", "US").strip() or "US"
TREND_WINDOW_DAYS = int(os.getenv("TREND_WINDOW_DAYS", "7"))

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "_work_professional"
FONTS_DIR = ROOT / "fonts"
REGULAR_FONT = FONTS_DIR / "NotoSans-Regular.ttf"
BOLD_FONT = FONTS_DIR / "NotoSans-Bold.ttf"
SYSTEM_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
SYSTEM_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# Reference-inspired palette: light background + strong blue + dark type.
BG = (247, 249, 252, 255)
BLUE = (17, 108, 229, 255)
BLUE_DARK = (9, 73, 160, 255)
PALE_BLUE = (225, 239, 255, 255)
DARK = (20, 27, 38, 255)
MUTED = (93, 104, 119, 255)
WHITE = (255, 255, 255, 255)
GREEN = (28, 160, 93, 255)
YELLOW = (255, 196, 61, 255)
RED = (226, 74, 74, 255)
SHADOW = (15, 23, 42, 55)

TREND_QUERIES = [
    "make money online",
    "online earning tips",
    "side hustle",
    "AI earning",
    "affiliate marketing",
    "freelancing",
    "TikTok monetization",
    "YouTube Shorts monetization",
    "digital products",
    "remote work",
    "online business",
    "ecommerce tips",
]

# Every topic has scene-specific visual search terms. This is the key change:
# the background is selected for the exact concept being spoken about.
TOPICS = {
    "ai": {
        "title": "AI freelancing",
        "key": "ai-freelancing",
        "keywords": ["AI", "freelancing", "ChatGPT", "clients"],
        "hook": "AI can speed up a skill — but the skill still matters.",
        "steps": [
            ("1", "PICK ONE SERVICE", "Writing, research, design or admin.", "freelancer laptop work"),
            ("2", "USE AI TO SPEED IT UP", "Draft faster, then check the result yourself.", "AI chatbot laptop typing"),
            ("3", "SELL THE RESULT", "Show a sample that solves a real client problem.", "freelancer client meeting laptop"),
        ],
        "script": "Want to use AI to earn? Pick one real freelance service. Use AI to speed up the work, check the result yourself, then sell the finished outcome to a real client.",
        "cta": "Save this if you want practical AI earning ideas.",
        "visual_hook": "young person laptop technology work",
    },
    "affiliate": {
        "title": "Affiliate marketing",
        "key": "affiliate-marketing",
        "keywords": ["affiliate", "product", "link", "commission"],
        "hook": "You can earn from a product without owning the product.",
        "steps": [
            ("1", "PICK A USEFUL PRODUCT", "Choose something your audience genuinely needs.", "online shopping product smartphone"),
            ("2", "SHARE YOUR LINK", "Use a legitimate affiliate program.", "smartphone link social media"),
            ("3", "EXPLAIN THE VALUE", "Helpful content can lead to qualifying purchases.", "person reviewing product phone"),
        ],
        "script": "Affiliate marketing is simple. Pick a useful product, join a legitimate affiliate program, share your link, and explain the product honestly. A qualifying purchase may earn you a commission.",
        "cta": "Follow for practical online business tips.",
        "visual_hook": "online shopping smartphone product review",
    },
    "tiktok": {
        "title": "TikTok earning",
        "key": "tiktok-earning",
        "keywords": ["TikTok", "content", "niche", "monetize"],
        "hook": "Don't chase random views. Build a useful TikTok niche.",
        "steps": [
            ("1", "CHOOSE ONE NICHE", "Make your topic obvious in the first seconds.", "TikTok creator smartphone vertical video"),
            ("2", "POST USEFUL CONTENT", "Teach, compare, demonstrate or review.", "social media creator filming phone"),
            ("3", "MONETIZE CAREFULLY", "Use eligible features, affiliates or services.", "TikTok social media analytics phone"),
        ],
        "script": "Want to earn from TikTok? Start with one clear niche. Post useful videos people want to watch, then explore eligible monetization, affiliate offers, or your own services.",
        "cta": "Save this before you start your next TikTok.",
        "visual_hook": "TikTok social media smartphone creator",
    },
    "youtube": {
        "title": "YouTube Shorts",
        "key": "youtube-shorts",
        "keywords": ["YouTube", "Shorts", "hook", "watch"],
        "hook": "A good Short solves one problem fast.",
        "steps": [
            ("1", "ONE CLEAR PROBLEM", "Give viewers one useful answer.", "YouTube Shorts smartphone creator"),
            ("2", "HOOK IMMEDIATELY", "Show the promise in the opening seconds.", "video editing timeline smartphone"),
            ("3", "KEEP IT ORIGINAL", "Add your own explanation, examples and visuals.", "content creator editing laptop"),
        ],
        "script": "For Shorts, solve one clear problem. Show the value immediately, then keep the story moving with useful examples and original visuals. Give viewers a reason to stay until the end.",
        "cta": "Follow for more Shorts growth tips.",
        "visual_hook": "YouTube Shorts creator smartphone editing",
    },
    "freelance": {
        "title": "Freelancing",
        "key": "freelancing",
        "keywords": ["freelance", "skill", "client", "portfolio"],
        "hook": "Your first freelance offer should be easy to understand.",
        "steps": [
            ("1", "PICK ONE SKILL", "Start with something you can actually deliver.", "freelancer working laptop home office"),
            ("2", "MAKE A SIMPLE OFFER", "Sell one clear result, not ten vague services.", "freelancer portfolio laptop"),
            ("3", "SHOW PROOF", "Create samples before you pitch clients.", "freelancer client presentation"),
        ],
        "script": "Want your first freelance client? Pick one skill you can actually deliver. Turn it into one clear offer, create a few useful samples, and show clients the result you can provide.",
        "cta": "Save this and build your first sample today.",
        "visual_hook": "freelancer laptop home office client",
    },
    "digital": {
        "title": "Digital products",
        "key": "digital-products",
        "keywords": ["digital product", "template", "guide", "sale"],
        "hook": "A digital product works best when it solves a repeated problem.",
        "steps": [
            ("1", "FIND THE PROBLEM", "Look for something people repeatedly need.", "person planning notes laptop"),
            ("2", "MAKE A SIMPLE RESOURCE", "Try a template, checklist or short guide.", "digital template laptop design"),
            ("3", "TEST BEFORE SCALING", "Improve it from real feedback.", "small business customer feedback laptop"),
        ],
        "script": "To build a digital product, start with a problem people repeatedly have. Turn the solution into a simple template, checklist or guide, then improve it from real feedback before scaling.",
        "cta": "Follow for realistic online business ideas.",
        "visual_hook": "digital product template laptop creator",
    },
    "selling": {
        "title": "Online selling",
        "key": "online-selling",
        "keywords": ["online store", "sales", "cost", "profit"],
        "hook": "Sales are not profit. Check the numbers first.",
        "steps": [
            ("1", "TEST DEMAND", "Start small before buying lots of stock.", "ecommerce online store smartphone"),
            ("2", "COUNT EVERY COST", "Product, fees, delivery and returns all matter.", "calculator ecommerce business money"),
            ("3", "TRACK REAL PROFIT", "Revenue alone does not tell the full story.", "business profit calculator money"),
        ],
        "script": "If you sell online, remember this: sales are not profit. Test demand first, count product cost, fees, delivery and returns, then track what is actually left.",
        "cta": "Save this before you buy your first stock.",
        "visual_hook": "ecommerce shopping packages money calculator",
    },
    "remote": {
        "title": "Remote work",
        "key": "remote-work",
        "keywords": ["remote job", "CV", "skills", "safe"],
        "hook": "A real remote job should not start with a mystery payment.",
        "steps": [
            ("1", "BUILD A USEFUL SKILL", "Focus on something employers actually need.", "remote worker laptop home office"),
            ("2", "SHOW YOUR RESULTS", "Use a clear CV and simple portfolio.", "resume CV laptop job application"),
            ("3", "APPLY SAFELY", "Use legitimate companies and job platforms.", "online job search laptop safety"),
        ],
        "script": "For remote work, build a useful skill, show results with a clear CV or portfolio, and apply through legitimate companies or platforms. Never pay a stranger for a promised job.",
        "cta": "Share this with someone looking for remote work.",
        "visual_hook": "remote worker laptop home office job search",
    },
    "pod": {
        "title": "Print on demand",
        "key": "print-on-demand",
        "keywords": ["print on demand", "design", "shirt", "niche"],
        "hook": "You can test designs without storing a warehouse of stock.",
        "steps": [
            ("1", "CHOOSE A NICHE", "Design for a specific audience.", "designer t shirt ecommerce laptop"),
            ("2", "CREATE ORIGINAL WORK", "Avoid copyrighted characters and logos.", "graphic designer creating t shirt"),
            ("3", "TEST DEMAND", "Keep improving what your audience responds to.", "online store t shirt order package"),
        ],
        "script": "Print on demand can let you test original designs without holding inventory yourself. Choose a niche, create original work, and test demand before investing more time or money.",
        "cta": "Follow for practical ecommerce ideas.",
        "visual_hook": "print on demand t shirt ecommerce design",
    },
    "general": {
        "title": "Online earning",
        "key": "online-earning",
        "keywords": ["money", "skill", "problem", "results"],
        "hook": "Ignore easy-money hype. Start with a real problem.",
        "steps": [
            ("1", "CHOOSE ONE SKILL", "Pick something you can improve and deliver.", "person learning laptop online course"),
            ("2", "SOLVE ONE PROBLEM", "Make the offer useful and specific.", "small business problem solving laptop"),
            ("3", "TEST THE MARKET", "Learn from real people and real results.", "small business customer feedback"),
        ],
        "script": "Ignore the easy-money hype. Choose one useful skill, solve one specific problem, and test your idea with real people. Improve from feedback instead of chasing every new trend.",
        "cta": "Save this if you want realistic earning ideas.",
        "visual_hook": "money laptop online business young entrepreneur",
    },
}

# ============================================================
# BASIC UTILITIES
# ============================================================
def run(cmd, check=True, capture=False):
    print("$", " ".join(str(x) for x in cmd))
    return subprocess.run(
        [str(x) for x in cmd],
        check=check,
        text=True,
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


def text_width(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def wrap(draw, text, font, max_width):
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = f"{line} {word}".strip()
        if text_width(draw, test, font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def shadow_box(img, box, radius=32):
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow)
    x1, y1, x2, y2 = box
    d.rounded_rectangle((x1 + 10, y1 + 14, x2 + 10, y2 + 14), radius=radius, fill=SHADOW)
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(shadow)


def add_side_design(img):
    d = ImageDraw.Draw(img)
    d.polygon([(0, 0), (65, 0), (18, H), (0, H)], fill=BLUE)
    d.polygon([(1010, 0), (W, 0), (W, H), (1060, H)], fill=PALE_BLUE)
    d.rectangle((72, 0, 78, H), fill=PALE_BLUE)
    d.rounded_rectangle((108, 50, 280, 84), 17, fill=PALE_BLUE)
    return d


def add_header(d, topic):
    d.text((108, 112), "EARN SMART", font=F(28, True), fill=BLUE)
    d.text((108, 154), topic["title"].upper(), font=F(23, True), fill=MUTED)


def add_progress(d, scene_num, total):
    x1, x2, y = 108, 972, 1785
    d.rounded_rectangle((x1, y, x2, y + 8), 4, fill=(224, 229, 236, 255))
    end = x1 + (x2 - x1) * scene_num / total
    d.rounded_rectangle((x1, y, end, y + 8), 4, fill=BLUE)
    d.text((108, 1810), f"{scene_num}/{total}", font=F(22, True), fill=MUTED)
    d.text((800, 1810), "FOLLOW FOR MORE", font=F(22, True), fill=BLUE)


def fit_lines_center(d, text, font, y, max_width, fill, spacing=8):
    lines = wrap(d, text, font, max_width)
    yy = y
    for line in lines:
        w = text_width(d, line, font)
        d.text(((W - w) / 2, yy), line, font=font, fill=fill)
        yy += font.size + spacing
    return yy


def topic_title_from_trend(title):
    t = title.lower()
    mapping = [
        ("ai", "ai"), ("chatgpt", "ai"), ("automation", "ai"),
        ("affiliate", "affiliate"), ("amazon associates", "affiliate"),
        ("tiktok", "tiktok"),
        ("youtube", "youtube"), ("shorts", "youtube"),
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


def discover_topics():
    if not YOUTUBE_API_KEY:
        print("YOUTUBE_API_KEY missing; using built-in topics.")
        return [dict(TOPICS[k]) for k in random.sample(list(TOPICS), SHORT_COUNT)]

    since = datetime.now(timezone.utc) - timedelta(days=max(1, TREND_WINDOW_DAYS))
    published_after = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    queries = random.sample(TREND_QUERIES, min(4, len(TREND_QUERIES)))
    candidates = {}

    # Four search.list calls keeps daily quota comfortably below the default
    # search quota while still giving several topic signals.
    for q in queries:
        try:
            data = youtube_get("search", {
                "part": "snippet",
                "q": q,
                "type": "video",
                "order": random.choice(["viewCount", "date"]),
                "publishedAfter": published_after,
                "maxResults": 12,
                "regionCode": YOUTUBE_REGION,
                "relevanceLanguage": "en",
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
                "description": sn.get("description", ""),
                "published": sn.get("publishedAt", ""),
            }

    if not candidates:
        return [dict(TOPICS[k]) for k in random.sample(list(TOPICS), SHORT_COUNT)]

    ids = list(candidates)[:50]
    try:
        stats = youtube_get("videos", {
            "part": "statistics,snippet",
            "id": ",".join(ids),
        })
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
        # Trend signal = recent view velocity + a small engagement signal.
        velocity = views / age_h
        engagement = ((likes * 2) + (comments * 5)) / max(views, 1) * 100000
        score = velocity + engagement
        scored.append((score, title, views, age_h, vid))

    scored.sort(reverse=True, key=lambda x: x[0])
    selected = []
    used = set()
    for score, title, views, age_h, vid in scored:
        key = topic_title_from_trend(title)
        if key in used:
            continue
        topic = dict(TOPICS[key])
        topic.update({
            "trend_source_title": title,
            "trend_views": views,
            "trend_age_hours": round(age_h, 1),
            "trend_score": round(score, 2),
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
# PEXELS VISUAL SEARCH
# ============================================================
def pexels_json(endpoint, params):
    if not PEXELS_API_KEY:
        return {}
    r = requests.get(
        f"https://api.pexels.com/v1/{endpoint}",
        headers={"Authorization": PEXELS_API_KEY},
        params=params,
        timeout=30,
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
            "query": query,
            "orientation": "portrait",
            "size": "medium",
            "per_page": 12,
        })
    except Exception as exc:
        print("Pexels video search failed:", exc)
        return None
    videos = data.get("videos", [])
    random.shuffle(videos)
    for v in videos:
        files = v.get("video_files", [])
        files = [x for x in files if x.get("link")]
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
            "query": query,
            "orientation": "portrait",
            "size": "large",
            "per_page": 12,
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
            return download_url(link, path)
    return None


def get_visual(query, folder, index):
    # Use a mix of video and photo media. Each scene gets its own query.
    if not PEXELS_API_KEY:
        return None
    if index % 2 == 1:
        p = folder / f"visual_{index}.mp4"
        return pexels_video(query, p)
    p = folder / f"visual_{index}.jpg"
    return pexels_photo(query, p)

# ============================================================
# VOICE + AUDIO
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
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ], capture=True)
    return float(r.stdout.strip())


def make_music(out, duration):
    # Very light original bed. Keep it quiet under the narration.
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "sine=frequency=220:sample_rate=44100",
        "-t", f"{duration:.2f}", "-af", "volume=0.018,afade=t=in:st=0:d=0.5,afade=t=out:st="
        f"{max(0.5, duration-0.8):.2f}:d=0.8", "-c:a", "aac", "-b:a", "64k", out
    ])

# ============================================================
# DESIGN / SCENES
# ============================================================
def make_background():
    img = Image.new("RGBA", (W, H), BG)
    add_side_design(img)
    return img


def draw_title_card(img, topic, hook, scene_no, total):
    d = ImageDraw.Draw(img)
    add_header(d, topic)
    # Big hook
    y = 330
    for i, line in enumerate(wrap(d, hook, F(70, True), 820)):
        fill = BLUE if i == 0 else DARK
        tw = text_width(d, line, F(70, True))
        d.text(((W - tw) / 2, y), line, font=F(70, True), fill=fill)
        y += 86

    # Small "watch" cue
    rounded(d, (150, 760, 930, 1040), 42, WHITE, outline=(222, 228, 237, 255), width=3)
    d.text((205, 815), "TODAY'S TIP", font=F(28, True), fill=BLUE)
    fit_lines_center(d, topic["keywords"][0].upper() + " • " + topic["keywords"][1].upper(), F(48, True), 890, 650, DARK)
    # Arrow
    d.line((540, 1100, 540, 1245), fill=BLUE, width=10)
    d.polygon([(505, 1215), (575, 1215), (540, 1275)], fill=BLUE)
    add_progress(d, scene_no, total)


def draw_step_card(img, topic, step, scene_no, total):
    num, title, detail, _ = step
    d = ImageDraw.Draw(img)
    add_header(d, topic)

    # Scene number
    rounded(d, (110, 285, 270, 445), 38, BLUE)
    d.text((162, 320), num, font=F(68, True), fill=WHITE)

    # Step title
    title_font = F(52, True)
    lines = wrap(d, title, title_font, 650)
    yy = 310
    for line in lines:
        d.text((315, yy), line, font=title_font, fill=DARK)
        yy += 62

    # Practical detail card
    shadow_box(img, (115, 600, 965, 1040), 40)
    rounded(d, (115, 600, 965, 1040), 40, WHITE, outline=(224, 229, 236, 255), width=3)
    d.text((175, 660), "DO THIS", font=F(27, True), fill=BLUE)
    fit_lines_center(d, detail, F(43, True), 745, 680, DARK, 12)

    # Check + mini timeline
    d.ellipse((170, 1140, 230, 1200), fill=GREEN)
    d.text((185, 1140), "✓", font=F(35, True), fill=WHITE)
    d.text((260, 1140), "Practical step", font=F(31, True), fill=MUTED)
    d.line((200, 1240, 880, 1240), fill=PALE_BLUE, width=12)
    d.ellipse((170 + (scene_no - 1) * 250, 1218, 210 + (scene_no - 1) * 250, 1258), fill=BLUE)

    # Highlighted keyword
    key = topic["keywords"][min(scene_no, len(topic["keywords"]) - 1)].upper()
    rounded(d, (170, 1340, 910, 1430), 24, PALE_BLUE)
    tw = text_width(d, key, F(28, True))
    d.text(((W - tw) / 2, 1368), key, font=F(28, True), fill=BLUE_DARK)
    add_progress(d, scene_no, total)


def draw_cta(img, topic, cta, scene_no, total):
    d = ImageDraw.Draw(img)
    add_header(d, topic)
    d.text((110, 360), "KEEP IT", font=F(74, True), fill=DARK)
    d.text((110, 445), "PRACTICAL.", font=F(74, True), fill=BLUE)

    shadow_box(img, (110, 670, 970, 1180), 44)
    rounded(d, (110, 670, 970, 1180), 44, DARK)
    fit_lines_center(d, cta, F(44, True), 800, 700, WHITE, 14)

    rounded(d, (160, 1310, 920, 1435), 30, BLUE)
    tw = text_width(d, "SAVE • SHARE • FOLLOW", F(32, True))
    d.text(((W - tw) / 2, 1350), "SAVE • SHARE • FOLLOW", font=F(32, True), fill=WHITE)

    add_progress(d, scene_no, total)


def render_card_for_scene(topic, scene_type, step=None, scene_no=1, total=5):
    img = make_background()
    if scene_type == "hook":
        draw_title_card(img, topic, topic["hook"], scene_no, total)
    elif scene_type == "step":
        draw_step_card(img, topic, step, scene_no, total)
    else:
        draw_cta(img, topic, topic["cta"], scene_no, total)
    return img


def prepare_visual_clip(path, out, duration):
    # Produce a vertical 1080x1920 clip with subtle zoom and darkening for
    # readability. Photos become moving clips with Ken Burns motion.
    if path is None or not Path(path).exists():
        return None
    p = str(path)
    ext = Path(p).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        frames = (
            f"scale=1400:2490:force_original_aspect_ratio=increase,crop=1080:1920," 
            f"zoompan=z='min(zoom+0.0008,1.08)':d={int(duration*FPS)}:s=1080x1920:fps={FPS},"
            "eq=brightness=-0.02:saturation=0.95,format=yuv420p"
        )
        run(["ffmpeg", "-y", "-loop", "1", "-i", p, "-t", f"{duration:.2f}", "-vf", frames,
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", out])
    else:
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920," 
            "eq=brightness=-0.03:saturation=0.92,format=yuv420p"
        )
        run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", p, "-t", f"{duration:.2f}",
             "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", out])
    return out


def make_scene_video(card, visual, voice, duration, out):
    # Visual = full-frame practical stock media; card = translucent editorial UI.
    # The card is animated by a short fade/slide effect.
    card_png = str(card)
    if visual and Path(visual).exists():
        filter_complex = (
            "[0:v]format=rgba,colorchannelmixer=aa=0.92[bg];"
            f"[1:v]format=rgba,fade=t=in:st=0:d=0.22:alpha=1,"
            f"fade=t=out:st={max(0.3,duration-0.28):.2f}:d=0.28:alpha=1[card];"
            "[bg][card]overlay=0:0:format=auto,format=yuv420p[v]"
        )
        run(["ffmpeg", "-y", "-i", visual, "-loop", "1", "-i", card_png, "-i", voice,
             "-t", f"{duration:.2f}", "-filter_complex", filter_complex,
             "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "24", "-c:a", "aac", "-b:a", "128k", "-shortest", out])
    else:
        run(["ffmpeg", "-y", "-loop", "1", "-i", card_png, "-i", voice,
             "-t", f"{duration:.2f}", "-vf", "format=yuv420p", "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac",
             "-b:a", "128k", "-shortest", out])


def concat_videos(files, output):
    list_file = output.parent / "concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"file '{Path(p).resolve()}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac",
         "-b:a", "128k", "-movflags", "+faststart", output])


def add_music_and_normalize(video, music, out, duration):
    # Narration is dominant; music is intentionally subtle.
    run(["ffmpeg", "-y", "-i", video, "-i", music,
         "-filter_complex", "[1:a]volume=0.025[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]",
         "-map", "0:v", "-map", "[a]", "-t", f"{duration:.2f}",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out])

# ============================================================
# SCRIPT / METADATA
# ============================================================
def scene_script(topic):
    # Each sentence is deliberately short so the matching visual can change
    # quickly while the narration stays natural.
    return [
        topic["hook"],
        f"Step one: {topic['steps'][0][1].lower()}. {topic['steps'][0][2]}",
        f"Step two: {topic['steps'][1][1].lower()}. {topic['steps'][1][2]}",
        f"Step three: {topic['steps'][2][1].lower()}. {topic['steps'][2][2]}",
        topic["cta"],
    ]


def safe_slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def write_metadata(topic, output_file, duration):
    title = f"{topic['title']}: {topic['hook']} #shorts"
    hashtags = [
        "#shorts", "#onlineearning", "#sidehustle", "#makemoneyonline",
        f"#{safe_slug(topic['key']).replace('-', '')}",
    ]
    description = (
        f"{topic['title']} explained with 3 practical steps.\n\n"
        f"The video focuses on: {', '.join(topic['keywords'])}.\n\n"
        "This is educational content, not a promise of income. Results vary by skill, effort, market, location and eligibility.\n\n"
        + " ".join(hashtags)
    )
    tags = list(dict.fromkeys([
        topic["title"].lower(), "online earning", "make money online", "side hustle",
        "earning tips", "online business", "money tips", "shorts", "youtube shorts",
        *[x.lower() for x in topic["keywords"]],
    ]))
    data = {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
        "topic": topic["title"],
        "keywords": topic["keywords"],
        "duration_seconds": round(duration, 2),
        "voice": VOICE,
        "trend_source_title": topic.get("trend_source_title"),
        "trend_views": topic.get("trend_views"),
        "trend_age_hours": topic.get("trend_age_hours"),
        "trend_score": topic.get("trend_score"),
        "original_content": True,
        "note": "Trend-inspired original educational Short; no income is guaranteed.",
    }
    output_file.with_suffix(".txt").write_text(json.dumps(data, indent=2), encoding="utf-8")

# ============================================================
# CREATE ONE SHORT
# ============================================================
def create_short(topic, number):
    folder = WORK_DIR / f"video_{number}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)

    scripts = scene_script(topic)
    total_scenes = 5
    scene_cards = []
    scene_media = []
    scene_files = []

    # Scene 1: hook visual matches the hook concept.
    queries = [topic["visual_hook"]] + [s[3] for s in topic["steps"]] + [topic["visual_hook"]]
    for idx, q in enumerate(queries, start=1):
        media = get_visual(q, folder, idx)
        scene_media.append(media)

    # Render cards. Each step card has the exact words spoken for that scene.
    scene_cards.append(render_card_for_scene(topic, "hook", scene_no=1, total=total_scenes))
    for i, step in enumerate(topic["steps"], start=2):
        scene_cards.append(render_card_for_scene(topic, "step", step=step, scene_no=i, total=total_scenes))
    scene_cards.append(render_card_for_scene(topic, "cta", scene_no=5, total=total_scenes))

    for i, text in enumerate(scripts, start=1):
        card_path = folder / f"card_{i}.png"
        scene_cards[i - 1].save(card_path, "PNG")
        voice_path = folder / f"voice_{i}.mp3"
        make_voice(text, voice_path)
        vd = media_duration(voice_path)
        # A little breathing room, but no artificial padding.
        duration = max(2.2, vd + 0.12)
        visual = scene_media[i - 1]
        prepared = None
        if visual:
            prepared = folder / f"prepared_{i}.mp4"
            prepare_visual_clip(visual, prepared, duration)
        scene_path = folder / f"scene_{i}.mp4"
        make_scene_video(card_path, prepared, voice_path, duration, scene_path)
        scene_files.append(scene_path)

    joined = folder / "joined.mp4"
    concat_videos(scene_files, joined)
    duration = media_duration(joined)

    # If the script somehow runs long, speed audio/video together slightly.
    if duration > MAX_SECONDS:
        factor = duration / MAX_SECONDS
        fixed = folder / "fixed.mp4"
        atempo = max(0.5, min(2.0, factor))
        run(["ffmpeg", "-y", "-i", joined,
             "-filter_complex", f"[0:v]setpts=PTS/{factor}[v];[0:a]atempo={atempo}[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", fixed])
        shutil.copy2(fixed, joined)
        duration = media_duration(joined)

    # Add a quiet original music bed.
    music = folder / "music.m4a"
    make_music(music, duration)
    final = folder / "final.mp4"
    add_music_and_normalize(joined, music, final, duration)

    output = OUTPUT_DIR / f"online_earning_short_{number}.mp4"
    shutil.copy2(final, output)
    write_metadata(topic, output, duration)
    print(f"CREATED: {output} | {duration:.1f}s | {topic['title']}")
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
