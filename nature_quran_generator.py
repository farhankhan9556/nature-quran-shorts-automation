#!/usr/bin/env python3
"""
Online Earning Shorts Generator - Trending Edition

What it does:
- Checks YouTube daily for recent/high-view online-earning videos.
- Uses the trend titles/keywords only as topic inspiration; it does NOT copy scripts.
- Selects 3 different trend angles per run.
- Creates original, practical vertical reels with a clean editorial design.
- Uses a youthful male TTS voice (Eric) with a slightly higher pitch.
- Uses Pexels portrait footage as small practical visual cards.
- Flexible video length: normally about 12-30 seconds.

Required GitHub Actions secrets:
  PEXELS_API_KEY
  YOUTUBE_API_KEY

Keep this filename as nature_quran_generator.py if your workflow already calls it.
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
from urllib.parse import quote_plus

import requests
from PIL import Image, ImageDraw, ImageFont

try:
    import edge_tts
except ImportError:
    edge_tts = None

# ============================================================
# SETTINGS
# ============================================================
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
SHORT_COUNT = 3
MIN_SECONDS = 12
MAX_SECONDS = 30

# Youthful male voice. Microsoft currently lists EricNeural as a male
# standard voice; a small positive pitch shift makes it sound younger.
VOICE = "en-US-EricNeural"
VOICE_RATE = "+10%"
VOICE_PITCH = "+4Hz"

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_REGION = os.getenv("YOUTUBE_REGION", "US").strip() or "US"
TREND_WINDOW_DAYS = int(os.getenv("TREND_WINDOW_DAYS", "7"))

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "_work_online_earning"
FONTS_DIR = ROOT / "fonts"
REGULAR_FONT = FONTS_DIR / "NotoSans-Regular.ttf"
BOLD_FONT = FONTS_DIR / "NotoSans-Bold.ttf"
SYSTEM_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
SYSTEM_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# Clean editorial palette inspired by the reference reel.
BG = (248, 250, 252, 255)
BLUE = (18, 115, 232, 255)
DARK = (22, 28, 38, 255)
MUTED = (93, 103, 118, 255)
WHITE = (255, 255, 255, 255)
PALE_BLUE = (228, 241, 255, 255)
GREEN = (24, 155, 91, 255)
YELLOW = (255, 196, 64, 255)

# Search themes. A random subset is checked every run so the search pattern
# changes slightly from day to day.
TREND_QUERIES = [
    "make money online",
    "online earning tips",
    "side hustle",
    "AI money making",
    "affiliate marketing",
    "freelancing online",
    "TikTok monetization",
    "YouTube Shorts money",
    "digital products",
    "remote work income",
    "online business ideas",
    "passive income ideas",
]

# Original content templates. Trend titles select an angle; these templates
# provide original narration instead of copying another creator.
TOPIC_TEMPLATES = {
    "ai": {
        "key": "ai-tools",
        "title": "AI freelancing",
        "search": "AI freelancer laptop desk",
        "hooks": [
            "AI is useful when it saves real work.",
            "Want to use AI to earn? Start with a skill.",
            "Don't sell AI. Sell the result AI helps you create.",
        ],
        "steps": [
            ("1", "Pick one service", "Writing, research, design or admin."),
            ("2", "Use AI to speed up", "Edit and check the result yourself."),
            ("3", "Sell the outcome", "Show samples that solve a real problem."),
        ],
        "script": "Pick one freelance service, use AI to speed up the work, check the final result yourself, and sell a clear outcome to clients who actually need it.",
        "caption": "Skill + AI + a real client problem",
    },
    "affiliate": {
        "key": "affiliate-marketing",
        "title": "Affiliate marketing",
        "search": "affiliate marketing shopping laptop",
        "hooks": [
            "Affiliate marketing starts with useful content.",
            "You don't need your own product to start.",
            "Here's the simple affiliate model.",
        ],
        "steps": [
            ("1", "Pick a useful product", "Choose something your audience needs."),
            ("2", "Get an affiliate link", "Use a legitimate affiliate program."),
            ("3", "Explain the value", "Recommend it honestly and clearly."),
        ],
        "script": "Pick a useful product, join a legitimate affiliate program, and create helpful content explaining why it may be useful. A qualifying purchase can earn you a commission, depending on the program.",
        "caption": "Helpful content • honest recommendations",
    },
    "tiktok": {
        "key": "tiktok-earning",
        "title": "TikTok earning",
        "search": "TikTok creator smartphone social media",
        "hooks": [
            "TikTok is not only about getting views.",
            "Want to turn attention into an income stream?",
            "The first step on TikTok is a clear niche.",
        ],
        "steps": [
            ("1", "Choose one niche", "Make it easy for people to know your topic."),
            ("2", "Post useful videos", "Teach, compare or demonstrate something."),
            ("3", "Monetize carefully", "Use eligible features, affiliates or services."),
        ],
        "script": "Choose one useful niche, post practical videos consistently, and build trust. Depending on your location and eligibility, income can come from platform features, affiliates, or your own services.",
        "caption": "Attention first. Trust next.",
    },
    "youtube": {
        "key": "youtube-shorts",
        "title": "YouTube Shorts",
        "search": "YouTube creator smartphone editing",
        "hooks": [
            "A Short can solve one problem in seconds.",
            "Want to grow a useful Shorts channel?",
            "Don't chase views before you have a useful idea.",
        ],
        "steps": [
            ("1", "Solve one problem", "Give one clear, useful answer."),
            ("2", "Hook quickly", "Make the opening easy to understand."),
            ("3", "Stay original", "Add your own explanation and examples."),
        ],
        "script": "Solve one simple problem, make the opening clear, and keep the video useful. Add your own explanation and examples instead of copying another creator's content.",
        "caption": "Useful + original + consistent",
    },
    "freelance": {
        "key": "freelancing",
        "title": "Freelancing",
        "search": "freelancer laptop client work",
        "hooks": [
            "Don't sell everything. Sell one result.",
            "One clear freelance service is easier to explain.",
            "Want your first freelance client? Start with proof.",
        ],
        "steps": [
            ("1", "Pick one skill", "Start with something you can actually do."),
            ("2", "Package the service", "Make the offer simple to understand."),
            ("3", "Show proof", "Create useful samples before pitching."),
        ],
        "script": "Start with one skill you can actually do. Package it as one clear service, create a few strong samples, and show clients the result you can help them achieve.",
        "caption": "One skill • one offer • clear proof",
    },
    "digital": {
        "key": "digital-products",
        "title": "Digital products",
        "search": "digital product template laptop creator",
        "hooks": [
            "A simple digital product can solve a real problem.",
            "You don't need a huge course to sell something useful.",
            "Find a repeated problem. Turn the solution into a resource.",
        ],
        "steps": [
            ("1", "Find a problem", "Look for something people repeatedly need."),
            ("2", "Build a simple resource", "Try a template, checklist or guide."),
            ("3", "Improve from feedback", "Make it better using real user needs."),
        ],
        "script": "Find a problem people repeatedly have, turn your solution into a useful template, checklist or guide, and improve it from real feedback. The goal is usefulness, not a get-rich-quick promise.",
        "caption": "Template • checklist • guide",
    },
    "selling": {
        "key": "online-selling",
        "title": "Online selling",
        "search": "ecommerce online store smartphone laptop",
        "hooks": [
            "Before buying stock, test demand.",
            "Sales are not the same as profit.",
            "Want to sell online? Start with the numbers.",
        ],
        "steps": [
            ("1", "Choose a real need", "Look for a product that solves a problem."),
            ("2", "Test interest", "Start small before buying lots of stock."),
            ("3", "Track profit", "Include fees, returns and delivery costs."),
        ],
        "script": "Before buying lots of stock, test demand. Start small and track selling fees, delivery, returns, product cost and actual profit. Revenue alone does not tell you if a business works.",
        "caption": "Revenue ≠ profit",
    },
    "remote": {
        "key": "remote-work",
        "title": "Remote work",
        "search": "remote work laptop home office",
        "hooks": [
            "Want a remote income? Build a useful skill first.",
            "Remote work starts with proof, not promises.",
            "A real remote job should not require a mystery payment.",
        ],
        "steps": [
            ("1", "Build a skill", "Focus on something employers need."),
            ("2", "Show results", "Use a simple CV and portfolio."),
            ("3", "Apply safely", "Use legitimate companies and platforms."),
        ],
        "script": "Build a skill employers actually need, make a simple CV that shows results, and apply through legitimate companies or job platforms. Never pay a stranger for a promised job.",
        "caption": "Skills + proof + safe applications",
    },
    "pod": {
        "key": "print-on-demand",
        "title": "Print on demand",
        "search": "print on demand t shirt ecommerce",
        "hooks": [
            "Want to test designs without storing stock?",
            "Print on demand can reduce inventory risk.",
            "The hard part is not uploading a design. It's finding demand.",
        ],
        "steps": [
            ("1", "Choose a niche", "Make designs for a specific audience."),
            ("2", "Create original work", "Avoid copyrighted characters and logos."),
            ("3", "Test demand", "Improve what your audience responds to."),
        ],
        "script": "Print on demand lets you test original designs without storing inventory yourself. Choose a niche, create your own designs, and test demand. Avoid copyrighted artwork and brands you do not have permission to use.",
        "caption": "Original designs only",
    },
    "course": {
        "key": "online-course",
        "title": "Online courses",
        "search": "online course creator laptop education",
        "hooks": [
            "Know something useful? Teach one clear outcome.",
            "A useful course solves a specific problem.",
            "Don't make a huge course before testing the idea.",
        ],
        "steps": [
            ("1", "Choose one outcome", "Teach one specific result."),
            ("2", "Make short lessons", "Keep every lesson practical."),
            ("3", "Add examples", "Show how to apply the skill."),
        ],
        "script": "Choose one useful outcome, break it into short practical lessons, and show real examples. Test the idea before spending weeks building a huge course.",
        "caption": "One outcome • short lessons • examples",
    },
    "general": {
        "key": "online-earning",
        "title": "Online earning",
        "search": "online earning laptop smartphone",
        "hooks": [
            "Want to earn online? Start with a real problem.",
            "Ignore the easy-money hype. Build something useful.",
            "A better online income plan starts small.",
        ],
        "steps": [
            ("1", "Choose one skill", "Pick something you can improve."),
            ("2", "Solve one problem", "Make your offer useful and specific."),
            ("3", "Test the market", "Learn from real people and results."),
        ],
        "script": "Ignore the easy-money hype. Choose one useful skill, solve one specific problem, and test your idea with real people. Improve from feedback instead of chasing every new trend.",
        "caption": "Useful skill • real problem • real feedback",
    },
}

# ============================================================
# UTILITIES
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
    preferred = BOLD_FONT if bold else REGULAR_FONT
    fallback = SYSTEM_BOLD if bold else SYSTEM_REGULAR
    if preferred.exists():
        return str(preferred)
    if fallback.exists():
        return str(fallback)
    raise RuntimeError("No usable font found.")


def F(size, bold=False):
    return ImageFont.truetype(font_path(bold), size)


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def add_centered_text(draw, text, y, font, fill, max_width=900, spacing=8):
    lines = wrap_text(draw, text, font, max_width)
    line_heights = [draw.textbbox((0, 0), x, font=font)[3] for x in lines]
    total = sum(line_heights) + spacing * max(0, len(lines) - 1)
    cy = y
    for line, h in zip(lines, line_heights):
        box = draw.textbbox((0, 0), line, font=font)
        w = box[2] - box[0]
        draw.text(((VIDEO_WIDTH - w) / 2, cy), line, font=font, fill=fill)
        cy += h + spacing
    return total


def make_slide_base():
    img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), BG)
    d = ImageDraw.Draw(img)

    # Reference-style side geometry.
    d.polygon([(0, 0), (70, 0), (22, 1920), (0, 1920)], fill=BLUE)
    d.polygon([(1010, 0), (1080, 0), (1080, 1920), (1058, 1920)], fill=PALE_BLUE)
    d.rectangle((70, 0, 76, VIDEO_HEIGHT), fill=PALE_BLUE)

    # Tiny top and bottom accents.
    d.rounded_rectangle((110, 52, 275, 88), radius=18, fill=PALE_BLUE)
    d.rounded_rectangle((805, 1830, 970, 1866), radius=18, fill=PALE_BLUE)
    return img, d


def add_brand(d, title):
    d.text((110, 115), "EARN SMART", font=F(30, True), fill=BLUE)
    d.text((110, 160), title.upper(), font=F(24, True), fill=MUTED)


def add_footer(d, text="FOLLOW FOR PRACTICAL ONLINE EARNING TIPS"):
    rounded_rect(d, (110, 1770, 970, 1840), 22, fill=DARK)
    box = d.textbbox((0, 0), text, font=F(25, True))
    d.text(((VIDEO_WIDTH - (box[2] - box[0])) / 2, 1790), text, font=F(25, True), fill=WHITE)


def draw_highlight_words(d, text, y, highlight=None, max_width=900):
    font = F(66, True)
    lines = wrap_text(d, text, font, max_width)
    yy = y
    for line in lines:
        parts = line.split()
        widths = [d.textbbox((0, 0), p + " ", font=font)[2] for p in parts]
        total = sum(widths)
        x = (VIDEO_WIDTH - total) / 2
        for p, w in zip(parts, widths):
            fill = BLUE if highlight and highlight.lower() in p.lower() else DARK
            d.text((x, yy), p + " ", font=font, fill=fill)
            x += w
        yy += 78
    return yy


def make_hook_slide(topic):
    img, d = make_slide_base()
    add_brand(d, topic["title"])

    # Number badge.
    rounded_rect(d, (110, 270, 260, 340), 25, fill=BLUE)
    d.text((158, 294), "TIP", font=F(32, True), fill=WHITE)

    draw_highlight_words(d, random.choice(topic["hooks"]), 420, highlight="online")

    rounded_rect(d, (150, 930, 930, 1390), 40, fill=WHITE, outline=(220, 227, 235, 255), width=3)
    d.text((205, 990), "TODAY'S ANGLE", font=F(28, True), fill=BLUE)
    add_centered_text(d, topic["caption"], 1070, F(43, True), DARK, 680, 10)

    # Animated-looking arrow/line.
    d.line((540, 1430, 540, 1515), fill=BLUE, width=8)
    d.polygon([(515, 1495), (565, 1495), (540, 1530)], fill=BLUE)
    add_footer(d)
    return img


def make_step_slide(topic, step_index):
    img, d = make_slide_base()
    add_brand(d, topic["title"])
    num, title, detail = topic["steps"][step_index]

    rounded_rect(d, (110, 285, 255, 430), 34, fill=BLUE)
    d.text((158, 325), num, font=F(62, True), fill=WHITE)

    d.text((295, 305), title, font=F(58, True), fill=DARK)
    d.line((295, 385, 935, 385), fill=PALE_BLUE, width=8)

    # Practical visual card.
    rounded_rect(d, (150, 550, 930, 1080), 40, fill=WHITE, outline=(220, 227, 235, 255), width=3)
    d.text((205, 610), "PRACTICAL", font=F(27, True), fill=BLUE)
    add_centered_text(d, detail, 700, F(44, True), DARK, 650, 12)

    # Check marks.
    for i, yy in enumerate((1120, 1215, 1310)):
        if i <= step_index:
            d.ellipse((175, yy, 225, yy + 50), fill=GREEN)
            d.text((188, yy + 5), "✓", font=F(30, True), fill=WHITE)
    d.text((255, 1120), "Useful", font=F(31, True), fill=MUTED)
    d.text((255, 1215), "Practical", font=F(31, True), fill=MUTED)
    d.text((255, 1310), "Original", font=F(31, True), fill=MUTED)

    add_footer(d)
    return img


def make_end_slide(topic):
    img, d = make_slide_base()
    add_brand(d, topic["title"])
    d.text((110, 350), "KEEP IT", font=F(70, True), fill=DARK)
    d.text((110, 430), "PRACTICAL.", font=F(70, True), fill=BLUE)

    rounded_rect(d, (110, 650, 970, 1220), 44, fill=DARK)
    add_centered_text(
        d,
        "No guaranteed income. Test the idea, track the numbers, and improve from real results.",
        760,
        F(42, True),
        WHITE,
        700,
        12,
    )

    # Social CTA buttons.
    for x, label in [(160, "LIKE"), (390, "SHARE"), (660, "FOLLOW")]:
        rounded_rect(d, (x, 1370, x + 240, 1450), 24, fill=BLUE if label == "FOLLOW" else PALE_BLUE)
        col = WHITE if label == "FOLLOW" else BLUE
        box = d.textbbox((0, 0), label, font=F(27, True))
        d.text((x + (240 - (box[2] - box[0])) / 2, 1393), label, font=F(27, True), fill=col)

    add_footer(d, "SAVE THIS • FOLLOW FOR MORE")
    return img


def create_scene_slides(topic, folder):
    slides = [make_hook_slide(topic)]
    slides += [make_step_slide(topic, i) for i in range(3)]
    slides.append(make_end_slide(topic))
    paths = []
    for i, image in enumerate(slides, start=1):
        p = folder / f"slide_{i}.png"
        image.save(p, "PNG")
        paths.append(p)
    return paths


def clean_text_for_filename(s):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s).strip("_")

# ============================================================
# YOUTUBE TREND DISCOVERY
# ============================================================
def youtube_get(path, params):
    url = f"https://www.googleapis.com/youtube/v3/{path}"
    params = dict(params)
    params["key"] = YOUTUBE_API_KEY
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def classify_trend(text):
    t = text.lower()
    groups = [
        ("ai", ["ai", "chatgpt", "artificial intelligence", "automation", "prompt"]),
        ("affiliate", ["affiliate", "amazon associates", "commission"]),
        ("tiktok", ["tiktok", "creator fund", "tiktok shop"]),
        ("youtube", ["youtube", "shorts", "faceless channel", "youtube automation"]),
        ("freelance", ["freelance", "fiverr", "upwork", "client", "freelancer"]),
        ("digital", ["digital product", "template", "notion template", "ebook", "printable"]),
        ("selling", ["ecommerce", "e-commerce", "shopify", "store", "dropshipping", "sell online"]),
        ("remote", ["remote job", "remote work", "work from home", "wfh", "online job"]),
        ("pod", ["print on demand", "pod", "merch", "t-shirt"]),
        ("course", ["course", "teach online", "online teaching", "udemy"]),
    ]
    for key, words in groups:
        if any(w in t for w in words):
            return key
    return "general"


def discover_trending_topics():
    """Return unique topic templates selected from recent YouTube interest."""
    if not YOUTUBE_API_KEY:
        print("YOUTUBE_API_KEY is missing. Falling back to built-in topics.")
        return random.sample(list(TOPIC_TEMPLATES.values()), SHORT_COUNT)

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=max(1, TREND_WINDOW_DAYS))
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    queries = random.sample(TREND_QUERIES, min(6, len(TREND_QUERIES)))
    candidates = {}

    for q in queries:
        for order in ("viewCount", "date"):
            try:
                data = youtube_get(
                    "search",
                    {
                        "part": "snippet",
                        "q": q,
                        "type": "video",
                        "order": order,
                        "publishedAfter": published_after,
                        "maxResults": 8,
                        "regionCode": YOUTUBE_REGION,
                        "relevanceLanguage": "en",
                        "safeSearch": "moderate",
                    },
                )
            except Exception as exc:
                print(f"YouTube search failed for '{q}' ({order}): {exc}")
                continue

            for item in data.get("items", []):
                vid = item.get("id", {}).get("videoId")
                snippet = item.get("snippet", {})
                if not vid:
                    continue
                candidates[vid] = {
                    "id": vid,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published": snippet.get("publishedAt", ""),
                }

    if not candidates:
        print("No current YouTube candidates found. Falling back to built-in topics.")
        return random.sample(list(TOPIC_TEMPLATES.values()), SHORT_COUNT)

    ids = list(candidates.keys())[:50]
    try:
        stats = youtube_get(
            "videos",
            {
                "part": "statistics,snippet,contentDetails",
                "id": ",".join(ids),
            },
        )
    except Exception as exc:
        print("YouTube statistics lookup failed:", exc)
        return random.sample(list(TOPIC_TEMPLATES.values()), SHORT_COUNT)

    scored = []
    now = datetime.now(timezone.utc)
    for item in stats.get("items", []):
        vid = item.get("id")
        base = candidates.get(vid, {})
        title = base.get("title", "")
        try:
            views = int(item.get("statistics", {}).get("viewCount", 0))
        except Exception:
            views = 0
        published = item.get("snippet", {}).get("publishedAt") or base.get("published")
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            age_hours = max(1.0, (now - dt).total_seconds() / 3600)
        except Exception:
            age_hours = float(TREND_WINDOW_DAYS * 24)

        # Approximate momentum: recent views per hour, with a small engagement
        # component. This is a trend signal, not a claim about YouTube's algorithm.
        likes = int(item.get("statistics", {}).get("likeCount", 0) or 0)
        comments = int(item.get("statistics", {}).get("commentCount", 0) or 0)
        velocity = views / age_hours
        engagement = (likes * 2 + comments * 5) / max(views, 1) * 100000
        score = velocity + engagement
        scored.append((score, title, views, age_hours))

    scored.sort(reverse=True, key=lambda x: x[0])

    selected = []
    used_groups = set()
    for score, title, views, age_hours in scored:
        group = classify_trend(title)
        if group in used_groups:
            continue
        template = TOPIC_TEMPLATES[group]
        chosen = dict(template)
        chosen["trend_source_title"] = title
        chosen["trend_score"] = round(score, 2)
        chosen["trend_views"] = views
        chosen["trend_age_hours"] = round(age_hours, 1)
        selected.append(chosen)
        used_groups.add(group)
        print(
            f"TREND: {group} | {views:,} views | {age_hours:.1f}h | {title[:100]}"
        )
        if len(selected) == SHORT_COUNT:
            break

    if len(selected) < SHORT_COUNT:
        remaining = [x for k, x in TOPIC_TEMPLATES.items() if k not in used_groups]
        random.shuffle(remaining)
        selected.extend(remaining[: SHORT_COUNT - len(selected)])

    return selected[:SHORT_COUNT]

# ============================================================
# PEXELS
# ============================================================
def pexels_video(topic, destination):
    if not PEXELS_API_KEY:
        print("PEXELS_API_KEY not set. Using designed graphics only.")
        return None

    url = "https://api.pexels.com/v1/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": topic["search"],
        "orientation": "portrait",
        "size": "medium",
        "per_page": 8,
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print("Pexels search failed:", exc)
        return None

    videos = data.get("videos", [])
    random.shuffle(videos)
    for video in videos:
        files = video.get("video_files", [])
        portrait = [x for x in files if (x.get("height") or 0) >= (x.get("width") or 0)]
        files = portrait or files
        files = sorted(files, key=lambda x: abs((x.get("height") or 1080) - 1920))
        for vf in files:
            link = vf.get("link")
            if not link:
                continue
            try:
                rr = requests.get(link, timeout=60, stream=True)
                rr.raise_for_status()
                with open(destination, "wb") as f:
                    for chunk in rr.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                if destination.exists() and destination.stat().st_size > 10000:
                    return destination
            except Exception as exc:
                print("Pexels download failed:", exc)
    return None

# ============================================================
# TTS
# ============================================================
async def tts_async(text, output_file):
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed. Add edge-tts to requirements.txt.")
    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate=VOICE_RATE,
        pitch=VOICE_PITCH,
    )
    await communicate.save(str(output_file))


def make_voice(text, output_file):
    asyncio.run(tts_async(text, output_file))


def get_duration(media_file):
    result = run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            media_file,
        ],
        capture=True,
    )
    return float(result.stdout.strip())

# ============================================================
# VIDEO BUILD
# ============================================================
def make_scene_video(slide, voice, duration, output_file, pexels_bg=None):
    duration = max(1.8, duration)
    if pexels_bg and Path(pexels_bg).exists():
        filter_complex = (
            f"[0:v]scale=760:620:force_original_aspect_ratio=increase,crop=760:620,"
            f"setsar=1,boxblur=1:1,eq=brightness=-0.02:saturation=0.82[bg];"
            f"[1:v]format=rgba,fade=t=in:st=0:d=0.35:alpha=1,"
            f"fade=t=out:st={max(0.4,duration-0.35):.3f}:d=0.35:alpha=1[slide];"
            f"[bg]format=rgba,colorchannelmixer=aa=0.28[bg2];"
            f"[bg2][slide]overlay=160:980:format=auto,format=yuv420p[v]"
        )
        run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", pexels_bg,
            "-loop", "1", "-i", slide, "-i", voice,
            "-t", f"{duration:.3f}", "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "2:a:0", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "24", "-c:a", "aac",
            "-b:a", "128k", "-shortest", output_file,
        ])
    else:
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", slide, "-i", voice,
            "-t", f"{duration:.3f}", "-vf", "format=yuv420p",
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "24", "-c:a", "aac",
            "-b:a", "128k", "-shortest", output_file,
        ])


def concat_scenes(scene_files, output_file):
    list_file = output_file.parent / "concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in scene_files:
            f.write(f"file '{Path(p).resolve()}'\n")
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", output_file,
    ])

# ============================================================
# SCRIPT / METADATA
# ============================================================
def split_script_into_scene_text(topic):
    return [
        random.choice(topic["hooks"]),
        topic["steps"][0][2],
        topic["steps"][1][2],
        topic["steps"][2][2],
        "Save this tip and follow for more practical online earning ideas.",
    ]


def fit_scene_duration(voice_duration):
    return max(1.9, min(7.0, voice_duration + 0.35))


def write_metadata(topic, output_file, total_duration):
    title = f"{topic['title']}: practical online earning tip #shorts"
    trend = topic.get("trend_source_title", "")
    description = (
        f"A practical {topic['title']} tip explained simply.\n\n"
        "This video was created from current topic-interest signals and uses original narration. "
        "It does not copy another creator's script.\n\n"
        "Results vary by skill, effort, market, location and eligibility. No income is guaranteed.\n\n"
        "#shorts #onlineearning #sidehustle #makemoneyonline "
        f"#{clean_text_for_filename(topic['key'])}"
    )
    tags = [
        "online earning", "make money online", "side hustle", "online business",
        "earning online", "digital income", "freelancing", "online work",
        "money tips", "shorts", topic["key"],
    ]
    meta = {
        "title": title,
        "description": description,
        "tags": tags,
        "topic": topic["title"],
        "duration_seconds": round(total_duration, 2),
        "voice": VOICE,
        "trend_source_title": trend,
        "trend_views": topic.get("trend_views"),
        "trend_age_hours": topic.get("trend_age_hours"),
        "note": "Trend-inspired original educational content. Results vary; no income guaranteed.",
    }
    output_file.with_suffix(".txt").write_text(json.dumps(meta, indent=2), encoding="utf-8")

# ============================================================
# ONE SHORT
# ============================================================
def create_short(topic, number):
    folder = WORK_DIR / f"video_{number}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)

    slides = create_scene_slides(topic, folder)
    texts = split_script_into_scene_text(topic)
    scene_files = []

    bg_file = folder / "pexels.mp4"
    pexels_video(topic, bg_file)
    bg = bg_file if bg_file.exists() else None

    for i, (slide, text) in enumerate(zip(slides, texts), start=1):
        voice_file = folder / f"voice_{i}.mp3"
        scene_file = folder / f"scene_{i}.mp4"
        make_voice(text, voice_file)
        voice_duration = get_duration(voice_file)
        scene_duration = fit_scene_duration(voice_duration)
        make_scene_video(slide, voice_file, scene_duration, scene_file, pexels_bg=bg)
        scene_files.append(scene_file)

    joined = folder / "joined.mp4"
    concat_scenes(scene_files, joined)
    duration = get_duration(joined)

    # Keep the finished reel within the requested flexible range.
    if duration > MAX_SECONDS:
        factor = duration / MAX_SECONDS
        corrected = folder / "corrected.mp4"
        run([
            "ffmpeg", "-y", "-i", joined,
            "-filter_complex", f"[0:v]setpts=PTS/{factor}[v];[0:a]atempo={min(2.0,max(0.5,factor))}[a]",
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", corrected,
        ])
        shutil.copy2(corrected, joined)
        duration = get_duration(joined)

    output_file = OUTPUT_DIR / f"online_earning_short_{number}.mp4"
    shutil.copy2(joined, output_file)
    write_metadata(topic, output_file, duration)
    print(f"CREATED: {output_file} | {duration:.1f}s | {topic['title']}")
    return output_file

# ============================================================
# MAIN
# ============================================================
def main():
    require_program("ffmpeg")
    require_program("ffprobe")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Remove only this generator's previous outputs so the uploader does not
    # accidentally pick up yesterday's generated files.
    for p in OUTPUT_DIR.glob("online_earning_short_*.mp4"):
        p.unlink(missing_ok=True)
    for p in OUTPUT_DIR.glob("online_earning_short_*.txt"):
        p.unlink(missing_ok=True)

    selected = discover_trending_topics()
    print("\nSELECTED DAILY TOPICS:")
    for i, topic in enumerate(selected, 1):
        print(f"  {i}. {topic['title']} | trend: {topic.get('trend_source_title', 'fallback')}")

    created = []
    for number, topic in enumerate(selected, start=1):
        try:
            created.append(create_short(topic, number))
        except Exception as exc:
            print(f"ERROR creating video {number}: {exc}")

    print("\n" + "=" * 70)
    print(f"FINISHED: {len(created)}/{SHORT_COUNT} videos")
    print("=" * 70)
    for p in created:
        print(p)


if __name__ == "__main__":
    main()
