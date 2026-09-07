#!/usr/bin/env python3
"""
ONLINE EARNING SHORTS GENERATOR V7

Main improvements:
- One continuous Edge-TTS narration per Short (no chopped voice between slides).
- Exact narration is also the only on-screen text.
- Text appears word-by-word while spoken, then stays on screen as numbered steps.
- Every short sentence gets its own matching background visual.
- Smooth 0.32s visual crossfades instead of hard cuts.
- No extra title, pill, progress bar, labels, or unrelated frame text.
- Fast pacing: scripts are written as short sentences, normally ~1–2.2s each.
- 3 original Shorts per run.
- YouTube trend discovery remains enabled.

GitHub secrets:
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
from PIL import Image, ImageDraw, ImageFont, ImageChops

try:
    import edge_tts
except ImportError:
    edge_tts = None

W, H, FPS = 1080, 1920, 30
SHORT_COUNT = 3
MAX_SECONDS = 35
VOICE = "en-US-EricNeural"
VOICE_RATE = "+10%"
VOICE_PITCH = "+2Hz"

# Smooth transition. This is deliberately short so the edit stays fast.
TRANSITION = 0.32
MIN_SENTENCE = 0.70
MAX_SENTENCE = 2.00
STEP_MAX_LINES = 2

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_REGION = os.getenv("YOUTUBE_REGION", "US").strip() or "US"
TREND_WINDOW_DAYS = int(os.getenv("TREND_WINDOW_DAYS", "7"))

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "_work_reference_style_v7"
FONTS_DIR = ROOT / "fonts"

REGULAR_FONT = FONTS_DIR / "NotoSans-Regular.ttf"
BOLD_FONT = FONTS_DIR / "NotoSans-Bold.ttf"
SYSTEM_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
SYSTEM_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

WHITE = (255, 255, 255, 255)
MUTED = (205, 211, 220, 225)
DIM = (150, 158, 170, 190)
BLACK = (0, 0, 0, 230)

TREND_QUERIES = [
    "make money online", "online earning tips", "side hustle",
    "AI earning", "affiliate marketing", "freelancing",
    "TikTok monetization", "YouTube Shorts monetization",
    "Facebook monetization", "digital products", "remote work",
    "online business", "ecommerce tips",
]

# Each sentence is intentionally short.
# "text" is EXACTLY what is sent to the voice generator.
# "query" is the visual search for that exact sentence.
TOPICS = {
    "facebook": {
        "title": "Facebook earning",
        "key": "facebook-earning",
        "keywords": ["Facebook", "content", "audience", "monetization"],
        "sentences": [
            ("Want to earn from Facebook? Start with useful content.", "facebook creator smartphone social media"),
            ("Open Facebook and create or log in to your account.", "facebook website smartphone login"),
            ("Choose one clear topic and create useful videos.", "facebook creator filming smartphone video"),
            ("Post consistently and build a real audience.", "facebook creator audience analytics smartphone"),
            ("Then check which monetization features you qualify for.", "facebook monetization creator smartphone analytics"),
        ],
        "cta": ("Follow for practical Facebook earning ideas.", "social media creator smartphone"),
    },
    "ai": {
        "title": "AI freelancing",
        "key": "ai-freelancing",
        "keywords": ["AI", "freelancing", "clients", "skills"],
        "sentences": [
            ("AI can help you earn when you use it for a real skill.", "AI laptop freelancer technology"),
            ("Choose one service you can deliver well.", "freelancer choosing skill laptop"),
            ("Use AI to speed up the repetitive parts of that work.", "AI chatbot laptop typing"),
            ("Check the result and create a sample for clients.", "freelancer checking laptop portfolio"),
            ("Then offer that useful result to real clients.", "freelancer client meeting laptop"),
        ],
        "cta": ("Save this for your next AI side hustle.", "AI freelancer laptop"),
    },
    "affiliate": {
        "title": "Affiliate marketing",
        "key": "affiliate-marketing",
        "keywords": ["affiliate", "product", "link", "commission"],
        "sentences": [
            ("Affiliate marketing can pay a commission when someone buys through your link.", "affiliate product smartphone online shopping"),
            ("Choose a product people genuinely need.", "product research smartphone online shopping"),
            ("Join a legitimate affiliate program and get your link.", "affiliate dashboard laptop online business"),
            ("Create useful content that explains the product.", "person reviewing product smartphone"),
            ("Add your link and follow the program rules.", "smartphone affiliate link social media creator"),
        ],
        "cta": ("Follow for practical affiliate ideas.", "affiliate marketing smartphone"),
    },
    "tiktok": {
        "title": "TikTok earning",
        "key": "tiktok-earning",
        "keywords": ["TikTok", "content", "niche", "monetization"],
        "sentences": [
            ("TikTok can create earning opportunities with useful content.", "TikTok creator smartphone vertical video"),
            ("Choose one clear niche for your videos.", "social media niche smartphone creator"),
            ("Make short videos that teach or demonstrate something.", "creator filming vertical smartphone video"),
            ("Build an audience with consistent original content.", "social media audience analytics smartphone"),
            ("Then use eligible monetization, affiliate, or service options.", "TikTok creator monetization smartphone"),
        ],
        "cta": ("Save this before your next TikTok.", "TikTok creator smartphone"),
    },
    "youtube": {
        "title": "YouTube Shorts",
        "key": "youtube-shorts",
        "keywords": ["YouTube", "Shorts", "hook", "retention"],
        "sentences": [
            ("A good Short solves one problem quickly.", "YouTube Shorts creator smartphone"),
            ("Choose one clear problem to solve.", "content creator planning laptop"),
            ("Show the useful part immediately.", "video editing vertical smartphone"),
            ("Change the visual when the idea changes.", "creator editing vertical video laptop"),
            ("Keep the explanation simple, useful, and original.", "YouTube creator recording smartphone"),
        ],
        "cta": ("Follow for more Shorts growth ideas.", "YouTube Shorts creator smartphone"),
    },
    "freelance": {
        "title": "Freelancing",
        "key": "freelancing",
        "keywords": ["freelance", "skill", "client", "portfolio"],
        "sentences": [
            ("Start freelancing with one skill you can deliver well.", "freelancer laptop home office"),
            ("Create one simple sample of your work.", "freelancer portfolio laptop"),
            ("Make one clear offer around one useful result.", "freelancer business proposal laptop"),
            ("Show your sample to potential clients.", "freelancer client meeting laptop"),
            ("Improve your offer using real feedback.", "freelancer feedback laptop business"),
        ],
        "cta": ("Save this and build your first sample.", "freelancer laptop portfolio"),
    },
    "digital": {
        "title": "Digital products",
        "key": "digital-products",
        "keywords": ["digital product", "template", "guide", "sale"],
        "sentences": [
            ("A digital product should solve a real problem.", "digital product creator laptop"),
            ("Find one problem people already want to solve.", "person planning laptop notes"),
            ("Create a simple template, checklist, or guide.", "digital template laptop design"),
            ("Show it to real people and improve it.", "customer feedback laptop digital product"),
            ("Then sell the improved product through a suitable platform.", "digital product online store laptop"),
        ],
        "cta": ("Follow for realistic digital business ideas.", "digital product laptop creator"),
    },
    "selling": {
        "title": "Online selling",
        "key": "online-selling",
        "keywords": ["ecommerce", "sales", "cost", "profit"],
        "sentences": [
            ("Sales are not profit, so check your numbers first.", "ecommerce calculator money business"),
            ("Test demand before buying lots of stock.", "online shopping ecommerce packages"),
            ("Count product, delivery, platform, and return costs.", "calculator ecommerce business money"),
            ("Check the margin left after every cost.", "business profit calculator money"),
            ("Track real profit instead of only revenue.", "online seller calculator laptop"),
        ],
        "cta": ("Save this before you buy your first stock.", "ecommerce packages business"),
    },
    "remote": {
        "title": "Remote work",
        "key": "remote-work",
        "keywords": ["remote job", "CV", "skills", "safety"],
        "sentences": [
            ("Start with a skill employers actually need.", "person learning laptop online course"),
            ("Prepare a clear CV and useful portfolio.", "resume CV laptop job application"),
            ("Apply through legitimate companies or platforms.", "online job search laptop"),
            ("Never pay a stranger to unlock a promised job.", "online job scam warning laptop"),
            ("Keep applying and improve your applications.", "remote worker laptop job search"),
        ],
        "cta": ("Share this with someone looking for remote work.", "remote worker laptop"),
    },
    "pod": {
        "title": "Print on demand",
        "key": "print-on-demand",
        "keywords": ["print on demand", "design", "niche", "ecommerce"],
        "sentences": [
            ("Print on demand lets you test designs without storing lots of stock.", "print on demand t shirt ecommerce"),
            ("Choose a specific audience or niche.", "designer t shirt niche laptop"),
            ("Create original designs for that audience.", "graphic designer creating t shirt"),
            ("List the design clearly on a selling platform.", "online store t shirt product page"),
            ("Test demand and improve the designs people respond to.", "online store t shirt order"),
        ],
        "cta": ("Follow for practical ecommerce ideas.", "print on demand ecommerce"),
    },
    "general": {
        "title": "Online earning",
        "key": "online-earning",
        "keywords": ["skill", "problem", "market", "results"],
        "sentences": [
            ("Ignore easy money hype and start with a real problem.", "online business money laptop"),
            ("Choose one skill you can improve.", "person learning laptop online course"),
            ("Solve one specific problem for someone.", "small business problem solving laptop"),
            ("Test your idea with real people.", "customer feedback small business laptop"),
            ("Improve the offer using real results, not hype.", "young entrepreneur laptop business"),
        ],
        "cta": ("Save this for your next online earning idea.", "online business laptop money"),
    },
}

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

# ------------------------------------------------------------
# YOUTUBE TREND DISCOVERY
# ------------------------------------------------------------
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
        ("facebook", "facebook"), ("meta", "facebook"),
        ("chatgpt", "ai"), ("ai", "ai"), ("automation", "ai"),
        ("affiliate", "affiliate"), ("amazon associates", "affiliate"),
        ("tiktok", "tiktok"),
        ("youtube", "youtube"), ("shorts", "youtube"),
        ("freelanc", "freelance"), ("fiverr", "freelance"), ("upwork", "freelance"),
        ("digital product", "digital"), ("template", "digital"),
        ("ecommerce", "selling"), ("shopify", "selling"), ("dropship", "selling"),
        ("remote job", "remote"), ("remote work", "remote"),
        ("work from home", "remote"),
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
                "published": sn.get("publishedAt", ""),
            }

    if not candidates:
        return [dict(TOPICS[k]) for k in random.sample(list(TOPICS), SHORT_COUNT)]

    ids = list(candidates)[:50]
    try:
        stats = youtube_get(
            "videos",
            {"part": "statistics,snippet", "id": ",".join(ids)}
        )
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
        remaining = [
            dict(TOPICS[k]) for k in TOPICS if k not in used
        ]
        random.shuffle(remaining)
        selected.extend(remaining[:SHORT_COUNT - len(selected)])

    return selected[:SHORT_COUNT]

# ------------------------------------------------------------
# PEXELS
# ------------------------------------------------------------
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
        files = [x for x in v.get("video_files", []) if x.get("link")]
        portrait = [
            x for x in files
            if (x.get("height") or 0) >= (x.get("width") or 0)
        ]
        candidates = portrait or files
        candidates.sort(
            key=lambda x: abs((x.get("height") or 1080) - 1920)
        )
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
            got = download_url(link, path)
            if got:
                return got
    return None

def get_visual(query, folder, index):
    # Prefer video for a more natural, less slideshow-like result.
    if random.random() < 0.72:
        got = pexels_video(query, folder / f"visual_{index}.mp4")
        if got:
            return got
        return pexels_photo(query, folder / f"visual_{index}.jpg")

    got = pexels_photo(query, folder / f"visual_{index}.jpg")
    if got:
        return got
    return pexels_video(query, folder / f"visual_{index}.mp4")

# ------------------------------------------------------------
# CONTINUOUS VOICE + WORD TIMINGS
# ------------------------------------------------------------
async def tts_with_boundaries(text, out):
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed.")

    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate=VOICE_RATE,
        pitch=VOICE_PITCH,
    )

    boundaries = []

    with open(out, "wb") as f:
        async for chunk in communicate.stream():
            kind = chunk.get("type")
            if kind == "audio":
                f.write(chunk["data"])
            elif kind == "WordBoundary":
                boundaries.append({
                    "text": chunk.get("text", ""),
                    "offset": float(chunk.get("offset", 0)) / 10_000_000,
                    "duration": float(chunk.get("duration", 0)) / 10_000_000,
                })

    return boundaries

def make_voice(text, out):
    return asyncio.run(tts_with_boundaries(text, out))

def media_duration(path):
    r = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ], capture=True)
    return float(r.stdout.strip())

def words_only(text):
    return re.findall(r"[A-Za-z0-9']+", text)

def align_sentences(sentences, boundaries, total_duration):
    """
    Map each sentence to the actual TTS word timings.
    Falls back safely to proportional timing if a TTS engine response
    has an unusual boundary sequence.
    """
    b = [x for x in boundaries if x.get("text")]
    result = []
    pos = 0

    for sentence, query in sentences:
        target = words_only(sentence)
        count = len(target)

        if pos + count <= len(b):
            start = b[pos]["offset"]
            end_item = b[pos + count - 1]
            end = end_item["offset"] + max(0.05, end_item["duration"])
            pos += count
        else:
            start = result[-1]["end"] if result else 0.0
            end = start + max(MIN_SENTENCE, total_duration / max(1, len(sentences)))

        if end <= start:
            end = start + MIN_SENTENCE

        result.append({
            "text": sentence,
            "query": query,
            "start": max(0.0, start),
            "end": min(total_duration, end),
        })

    # Normalize gaps and enforce short scene pacing.
    for i in range(len(result)):
        if i > 0:
            result[i]["start"] = max(
                result[i]["start"],
                result[i - 1]["start"] + 0.05
            )
        result[i]["end"] = max(
            result[i]["end"],
            result[i]["start"] + MIN_SENTENCE
        )

    # Last sentence must reach the actual end of the narration.
    if result:
        result[-1]["end"] = total_duration

    return result

# ------------------------------------------------------------
# CAPTION DESIGN
# -------------------------------------------------def _rounded_gradient_card(base, box, top_rgb, bottom_rgb, alpha=205, radius=34):
    """Draw a polished translucent gradient card with a subtle border."""
    x1, y1, x2, y2 = map(int, box)
    layer = Image.new("RGBA", (x2 - x1, y2 - y1), (0, 0, 0, 0))
    px = layer.load()
    h = max(1, y2 - y1)

    for yy in range(h):
        t = yy / max(1, h - 1)
        r = int(top_rgb[0] * (1-t) + bottom_rgb[0] * t)
        g = int(top_rgb[1] * (1-t) + bottom_rgb[1] * t)
        b = int(top_rgb[2] * (1-t) + bottom_rgb[2] * t)
        for xx in range(x2 - x1):
            px[xx, yy] = (r, g, b, alpha)

    mask = Image.new("L", layer.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, layer.width-1, layer.height-1), radius=radius, fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    base.alpha_composite(layer, (x1, y1))

    d = ImageDraw.Draw(base)
    d.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=radius,
        outline=(255, 255, 255, 105),
        width=2,
    )


def _step_font_size(step_count):
    if step_count <= 3:
        return 55
    if step_count <= 4:
        return 50
    if step_count <= 5:
        return 44
    return 39


def _fit_step_text(draw, text, font, max_width):
    """Wrap without cutting words whenever possible."""
    lines = wrap(draw, text.upper(), font, max_width, stroke=1)
    if len(lines) <= STEP_MAX_LINES:
        return lines

    # If the last line would overflow, use a slightly smaller font.
    size = font.size
    while size > 32:
        size -= 2
        test_font = F(size, True)
        lines = wrap(draw, text.upper(), test_font, max_width, stroke=1)
        if len(lines) <= STEP_MAX_LINES:
            return lines, test_font
    return lines[:STEP_MAX_LINES], font


def caption_image(completed_steps, current_step=None, current_words=None):
    """
    V7 polished step-board:
      - Elegant numbered circles.
      - Thin vertical connector between steps.
      - Soft glass-style cards with a subtle accent edge.
      - Current step is brighter and larger.
      - Spoken words build progressively.
      - Completed steps remain visible.
      - No unrelated UI text.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # Gentle readability veil only behind the step area.
    panel = Image.new("RGBA", (W, 1050), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    for yy in range(1050):
        alpha = int(105 * (yy / 1050) ** 2)
        pd.line((0, yy, W, yy), fill=(0, 0, 0, alpha))
    img.alpha_composite(panel, (0, H - 1050))

    d = ImageDraw.Draw(img)

    steps = list(completed_steps)
    if current_step is not None and current_words:
        steps.append(" ".join(current_words))
    if not steps:
        return img

    font_size = _step_font_size(len(steps))
    base_font = F(font_size, True)

    card_left = 48
    card_right = W - 48
    circle_x = 112
    text_x = 174
    max_text_width = card_right - text_x - 34

    rendered = []
    for i, text in enumerate(steps):
        result = _fit_step_text(d, text, base_font, max_text_width)
        if isinstance(result, tuple):
            lines, font = result
        else:
            lines, font = result, base_font
        rendered.append((i, lines, font))

    line_heights = [font.size + 7 for _, _, font in rendered]
    card_heights = [
        max(92, len(lines) * lh + 34)
        for (_, lines, font), lh in zip(rendered, line_heights)
    ]
    gap = 14
    total_h = sum(card_heights) + gap * (len(card_heights) - 1)

    # Keep enough room for the background hero and avoid clipping on long stacks.
    top = max(500, min(910, int(H - 305 - total_h)))
    if top + total_h > H - 95:
        top = H - 95 - total_h

    # Connector line first, so it sits behind the numbered circles.
    y_positions = []
    y = top
    for h in card_heights:
        y_positions.append(y)
        y += h + gap

    if len(y_positions) > 1:
        for a, b, ha, hb in zip(
            y_positions[:-1],
            y_positions[1:],
            card_heights[:-1],
            card_heights[1:],
        ):
            y1 = int(a + ha / 2 + 29)
            y2 = int(b + hb / 2 - 29)
            d.line((circle_x, y1, circle_x, y2), fill=(255, 255, 255, 125), width=3)

    for pos, ((idx, lines, font), h) in enumerate(zip(rendered, card_heights)):
        y = y_positions[pos]
        is_current = current_step is not None and idx == len(rendered) - 1

        # Alternating subtle tones keep the stack visually alive.
        if is_current:
            top_rgb = (20, 46, 74)
            bottom_rgb = (8, 24, 42)
            alpha = 222
            accent = (96, 205, 255, 255)
        else:
            top_rgb = (20, 27, 37)
            bottom_rgb = (9, 14, 22)
            alpha = 164
            accent = (255, 255, 255, 95)

        _rounded_gradient_card(
            img,
            (card_left, y, card_right, y + h),
            top_rgb,
            bottom_rgb,
            alpha=alpha,
            radius=32,
        )

        # Small accent strip gives the current step a premium visual cue.
        d.rounded_rectangle(
            (card_left + 4, y + 7, card_left + 10, y + h - 7),
            radius=4,
            fill=accent,
        )

        # Number badge: outer ring + inner disc.
        cy = y + h / 2
        outer_r = 31
        inner_r = 24

        d.ellipse(
            (circle_x-outer_r, cy-outer_r, circle_x+outer_r, cy+outer_r),
            fill=(8, 14, 21, 225),
            outline=(255, 255, 255, 120),
            width=2,
        )
        d.ellipse(
            (circle_x-inner_r, cy-inner_r, circle_x+inner_r, cy+inner_r),
            fill=(255, 255, 255, 245) if is_current else (210, 219, 228, 225),
        )

        number = str(idx + 1)
        number_font = F(29 if len(number) < 2 else 25, True)
        nb = d.textbbox((0, 0), number, font=number_font)
        nw, nh = nb[2] - nb[0], nb[3] - nb[1]
        d.text(
            (circle_x - nw/2, cy - nh/2 - 2),
            number,
            font=number_font,
            fill=(7, 13, 20, 255),
        )

        # Current step gets a tiny "active" dot.
        if is_current:
            d.ellipse(
                (card_right - 35, y + 17, card_right - 21, y + 31),
                fill=(96, 205, 255, 240),
            )

        # Text with restrained shadow: cleaner than a heavy black stroke.
        line_h = font.size + 7
        text_y = y + (h - len(lines) * line_h) / 2 - 2

        for line in lines:
            tw = text_width(d, line, font, 1)
            x = min(text_x, card_right - 30 - tw)

            d.text(
                (x + 2, text_y + 3),
                line,
                font=font,
                fill=(0, 0, 0, 205),
            )
            d.text(
                (x, text_y),
                line,
                font=font,
                fill=(255, 255, 255, 255) if is_current else (235, 239, 244, 238),
            )
            text_y += line_h

    return img

return img


def make_caption_frames(folder, sentence_data, total_duration, word_boundaries=None):
    """
    Create cumulative step-board PNGs.

    The actual narration is one continuous audio track.
    Caption changes are timed to the TTS word boundaries when available.
    Spoken words are added progressively and never removed.
    """
    events = []

    # Build a boundary list once. We use it only to synchronize visible words.
    boundaries = [x for x in (word_boundaries or []) if x.get("text")]

    boundary_pos = 0

    for idx, s in enumerate(sentence_data):
        ws = words_only(s["text"])
        start = s["start"]
        end = s["end"]
        dur = max(0.15, end - start)

        # Prefer real TTS word timings.
        sentence_boundaries = boundaries[boundary_pos:boundary_pos + len(ws)]

        if len(sentence_boundaries) == len(ws):
            for j, b in enumerate(sentence_boundaries, 1):
                t = max(start, float(b["offset"]))
                events.append((t, idx, ws[:j]))
            boundary_pos += len(ws)
        else:
            # Reliable fallback: evenly reveal words across the spoken sentence.
            for j in range(1, len(ws) + 1):
                t = start + dur * ((j - 1) / max(1, len(ws)))
                events.append((t, idx, ws[:j]))

    # Sort and remove impossible duplicate/negative timestamps.
    events.sort(key=lambda x: x[0])
    paths = []

    for i, (t, idx, current_words) in enumerate(events):
        # Previous sentences remain permanently visible.
        prior = [s["text"] for s in sentence_data[:idx]]

        img = caption_image(
            prior,
            current_step=sentence_data[idx]["text"],
            current_words=current_words,
        )

        p = folder / f"caption_{i:04d}.png"
        img.save(p, "PNG")
        paths.append((max(0.0, min(total_duration, t)), p))

    if not paths:
        final_img = caption_image(
            [s["text"] for s in sentence_data],
            current_step=None,
            current_words=None,
        )
        final_path = folder / "caption_final.png"
        final_img.save(final_path, "PNG")
        return [(0.0, final_path)], final_path

    final_img = caption_image(
        [s["text"] for s in sentence_data],
        current_step=None,
        current_words=None,
    )
    final_path = folder / "caption_final.png"
    final_img.save(final_path, "PNG")

    return paths, final_path


def build_caption_video(folder, sentence_data, total_duration, word_boundaries=None):
    """
    Build a transparent caption video.

    Each word reveal is a new frame, while previous spoken steps stay on screen.
    """
    paths, final_path = make_caption_frames(
        folder,
        sentence_data,
        total_duration,
        word_boundaries=word_boundaries,
    )

    timeline = folder / "caption_timeline.txt"

    # Collapse timestamps that are effectively identical.
    cleaned = []
    for t, p in paths:
        if cleaned and abs(t - cleaned[-1][0]) < 0.025:
            cleaned[-1] = (t, p)
        else:
            cleaned.append((t, p))

    with open(timeline, "w", encoding="utf-8") as f:
        for i, (t, p) in enumerate(cleaned):
            next_t = cleaned[i + 1][0] if i + 1 < len(cleaned) else total_duration
            dur = max(0.035, next_t - t)
            f.write(f"file '{Path(p).resolve()}'\n")
            f.write(f"duration {dur:.4f}\n")

        # concat demuxer needs the last file repeated.
        f.write(f"file '{Path(cleaned[-1][1]).resolve()}'\n")

    caption_video = folder / "captions.mov"
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", timeline,
        "-t", f"{total_duration:.3f}",
        "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS},format=rgba",
        "-c:v", "qtrle",
        "-pix_fmt", "argb",
        caption_video
    ])
    return caption_video


# ------------------------------------------------------------
# VISUAL CLIPS
# ------------------------------------------------------------
def prepare_visual(path, out, duration, variant):
    if not path or not Path(path).exists():
        return None

    ext = Path(path).suffix.lower()
    zoom = 1.04 + (variant % 4) * 0.012

    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        vf = (
            "scale=1320:2346:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"zoompan=z='min({zoom}+on*0.00035,{zoom+0.035})':"
            f"d={max(1,int(duration*FPS))}:s=1080x1920:fps={FPS},"
            "eq=brightness=-0.015:saturation=1.03,format=yuv420p"
        )
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", path,
            "-t", f"{duration:.3f}", "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "23", out
        ])
    else:
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "eq=brightness=-0.015:saturation=1.03,format=yuv420p"
        )
        run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", path,
            "-t", f"{duration:.3f}", "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "23", out
        ])

    return out

def build_visual_timeline(sentence_data, folder, total_duration):
    """
    Make one visual per sentence and crossfade them.
    No black fade-in/fade-out between slides.
    """
    clips = []

    for i, s in enumerate(sentence_data):
        # Keep every sentence visually represented.
        dur = max(0.35, s["end"] - s["start"])
        if i < len(sentence_data) - 1:
            dur += TRANSITION

        media = get_visual(
            f"{s['query']} realistic natural footage",
            folder,
            i + 1,
        )

        prepared = prepare_visual(
            media,
            folder / f"prepared_{i+1}.mp4",
            dur,
            i + 1,
        )

        if prepared:
            clips.append(prepared)

    if not clips:
        # Emergency fallback.
        blank = folder / "blank.mp4"
        run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=black:s={W}x{H}:r={FPS}",
            "-t", f"{total_duration:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", blank
        ])
        return blank

    if len(clips) == 1:
        return clips[0]

    current = clips[0]
    current_duration = media_duration(current)

    for i, nxt in enumerate(clips[1:], start=1):
        next_duration = media_duration(nxt)
        out = folder / f"xfade_{i}.mp4"

        offset = max(0.0, current_duration - TRANSITION)

        filter_complex = (
            f"[0:v]settb=AVTB,setpts=PTS-STARTPTS,fps={FPS}[a];"
            f"[1:v]settb=AVTB,setpts=PTS-STARTPTS,fps={FPS}[b];"
            f"[a][b]xfade=transition=smoothleft:"
            f"duration={TRANSITION}:offset={offset:.3f},"
            "format=yuv420p[v]"
        )

        run([
            "ffmpeg", "-y",
            "-i", current,
            "-i", nxt,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-movflags", "+faststart",
            out
        ])

        current = out
        current_duration = current_duration + next_duration - TRANSITION

    # Trim/pad visual timeline to exact narration duration.
    final_visual = folder / "visual_timeline.mp4"
    run([
        "ffmpeg", "-y", "-i", current,
        "-t", f"{total_duration:.3f}",
        "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", final_visual
    ])

    return final_visual

# ------------------------------------------------------------
# CAPTION VIDEO
# ------------------------------------------------------------

# ------------------------------------------------------------
# FINAL VIDEO
# ------------------------------------------------------------
def compose(video, captions, voice, output, duration):
    run([
        "ffmpeg", "-y",
        "-i", video,
        "-i", captions,
        "-i", voice,
        "-filter_complex",
        "[0:v][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]",
        "-map", "2:a",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        output
    ])

# ------------------------------------------------------------
# METADATA
# ------------------------------------------------------------
def write_metadata(topic, output_file, duration, script):
    title = f"{topic['title']}: practical steps #shorts"

    tag = safe_slug(topic["key"]).replace("-", "")
    hashtags = [
        "#shorts",
        "#onlineearning",
        "#sidehustle",
        "#makemoneyonline",
        f"#{tag}",
    ]

    description = (
        f"{topic['title']} — practical online earning content.\\n\\n"
        f"Video script:\\n{script}\\n\\n"
        "Educational content only. No income is guaranteed; results vary "
        "by skill, effort, market, location and eligibility.\\n\\n"
        "Visuals provided by Pexels: https://www.pexels.com/\\n\\n"
        + " ".join(hashtags)
    )

    tags = list(dict.fromkeys([
        topic["title"].lower(),
        "online earning",
        "make money online",
        "side hustle",
        "earning tips",
        "online business",
        "money tips",
        "shorts",
        *[x.lower() for x in topic["keywords"]],
    ]))

    data = {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags": tags,
        "topic": topic["title"],
        "script": script,
        "duration_seconds": round(duration, 2),
        "voice": VOICE,
        "voice_rate": VOICE_RATE,
        "continuous_voice": True,
        "word_by_word_captions": True,
        "visual_changes": "one matching visual per sentence with smooth crossfade",
        "trend_source_title": topic.get("trend_source_title"),
        "trend_views": topic.get("trend_views"),
        "trend_age_hours": topic.get("trend_age_hours"),
        "trend_score": topic.get("trend_score"),
        "original_content": True,
    }

    output_file.with_suffix(".txt").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )

# ------------------------------------------------------------
# CREATE ONE SHORT
# ------------------------------------------------------------
def create_short(topic, number):
    folder = WORK_DIR / f"video_{number}"

    if folder.exists():
        shutil.rmtree(folder)

    folder.mkdir(parents=True, exist_ok=True)

    sentence_list = list(topic["sentences"])
    sentence_list.append(topic["cta"])

    script = " ".join(x[0] for x in sentence_list)

    voice_path = folder / "narration.mp3"
    boundaries = make_voice(script, voice_path)
    total_duration = media_duration(voice_path)

    # If the script becomes too long, speed the entire continuous narration.
    # This preserves synchronization because captions are built from the final audio.
    if total_duration > MAX_SECONDS:
        factor = total_duration / MAX_SECONDS
        sped_voice = folder / "narration_sped.mp3"
        atempo = max(1.0, min(2.0, factor))

        run([
            "ffmpeg", "-y",
            "-i", voice_path,
            "-filter:a", f"atempo={atempo:.5f}",
            "-c:a", "aac", "-b:a", "160k",
            sped_voice
        ])

        voice_path = sped_voice
        total_duration = media_duration(voice_path)

        # Recreate boundaries for the sped narration is unnecessary for relative
        # timing below; proportional sentence timing is used if boundaries mismatch.
        boundaries = []

    sentence_data = align_sentences(
        sentence_list,
        boundaries,
        total_duration
    )

    # Visuals change at every spoken sentence. We do not cut a sentence in half.
    # The scripts themselves use short sentences, normally around 1–2 seconds.
    # If a sentence is slightly longer, the narration stays continuous and the
    # visual remains until the sentence finishes.
    for i in range(len(sentence_data) - 1):
        sentence_data[i]["end"] = max(
            sentence_data[i]["start"] + MIN_SENTENCE,
            sentence_data[i]["end"]
        )

    sentence_data[-1]["end"] = total_duration

    print("\nSCRIPT:")
    for i, s in enumerate(sentence_data, 1):
        print(f"{i}. {s['text']}  [{s['start']:.2f}-{s['end']:.2f}s]")

    visual = build_visual_timeline(
        sentence_data,
        folder,
        total_duration
    )

    captions = build_caption_video(
        folder,
        sentence_data,
        total_duration,
        word_boundaries=boundaries
    )

    final = folder / "final.mp4"
    compose(
        visual,
        captions,
        voice_path,
        final,
        total_duration
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"online_earning_short_{number}.mp4"
    shutil.copy2(final, output)

    write_metadata(
        topic,
        output,
        total_duration,
        script
    )

    print(
        f"CREATED: {output} | {total_duration:.1f}s | "
        f"{topic['title']} | {len(sentence_data)} spoken steps"
    )

    return output

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
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
        print(
            f"{i}. {topic['title']} | "
            f"trend={topic.get('trend_source_title', 'fallback')}"
        )

    made = []
    for i, topic in enumerate(selected, 1):
        try:
            made.append(create_short(topic, i))
        except Exception as exc:
            import traceback
            print(f"ERROR video {i}: {exc}")
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"FINISHED: {len(made)}/{SHORT_COUNT}")
    for p in made:
        print(p)

    if len(made) != SHORT_COUNT:
        raise RuntimeError(
            f"Only {len(made)}/{SHORT_COUNT} Shorts were created. "
            "See the detailed error above."
        )

if __name__ == "__main__":
    main()
