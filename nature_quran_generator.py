#!/usr/bin/env python3
"""
Online Earning Shorts Generator
Design direction:
- Clean editorial/social-media explainer look
- Light background
- Blue/cyan geometric accents
- Large bold typography
- Animated cards, arrows and check marks
- Small practical video card instead of generic full-screen AI stock footage
- Natural voiceover
- Flexible short length (roughly 12–30 seconds)
- Generates 3 different Shorts per run

Keep this filename as nature_quran_generator.py so the existing GitHub workflow
does not need to be renamed.
"""

import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import textwrap
import time
from pathlib import Path

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

VOICE = "en-US-GuyNeural"
VOICE_RATE = "+8%"
VOICE_PITCH = "+0Hz"

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "_work_online_earning"
FONTS_DIR = ROOT / "fonts"

REGULAR_FONT = FONTS_DIR / "NotoSans-Regular.ttf"
BOLD_FONT = FONTS_DIR / "NotoSans-Bold.ttf"

# Fallback fonts available on GitHub Actions Ubuntu.
SYSTEM_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
SYSTEM_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# Brand/design colors.
BG = (248, 250, 252, 255)
BLUE = (18, 115, 232, 255)
DARK = (22, 28, 38, 255)
MUTED = (93, 103, 118, 255)
WHITE = (255, 255, 255, 255)
PALE_BLUE = (228, 241, 255, 255)
GREEN = (24, 155, 91, 255)

TOPICS = [
    {
        "key": "affiliate",
        "search": "affiliate marketing laptop online shopping",
        "title": "Affiliate marketing",
        "hook": "Want to earn online?",
        "steps": [
            ("1", "Pick a product", "Choose something people already want."),
            ("2", "Get your link", "Use an affiliate program."),
            ("3", "Share useful content", "Recommend it with an honest reason."),
        ],
        "script": (
            "Want to earn online? Try affiliate marketing. "
            "Pick a useful product, get your affiliate link, and make helpful content around it. "
            "You earn a commission when your content leads to a qualifying purchase."
        ),
        "caption": "Affiliate marketing • useful content • honest recommendations",
    },
    {
        "key": "tiktok",
        "search": "TikTok creator smartphone social media",
        "title": "TikTok income",
        "hook": "TikTok can be more than views.",
        "steps": [
            ("1", "Build a niche", "Choose one topic people follow."),
            ("2", "Post useful videos", "Teach, compare or demonstrate."),
            ("3", "Monetize", "Use eligible features, affiliates or services."),
        ],
        "script": (
            "TikTok can be more than views. Pick one useful niche, post practical videos consistently, "
            "and build trust. Depending on your location and eligibility, you can monetize through "
            "platform features, affiliates, or your own services."
        ),
        "caption": "Views are attention. Trust is what you build.",
    },
    {
        "key": "ai-freelance",
        "search": "AI freelancer laptop desk artificial intelligence",
        "title": "AI freelancing",
        "hook": "Use AI as a work tool.",
        "steps": [
            ("1", "Choose one service", "Writing, research, design or admin."),
            ("2", "Use AI to speed up", "Edit and check everything yourself."),
            ("3", "Sell the result", "Show samples and solve a real problem."),
        ],
        "script": (
            "Use AI as a work tool, not a magic money button. Pick one service, "
            "use AI to speed up the work, check the final result yourself, and sell a clear outcome "
            "to clients who actually need it."
        ),
        "caption": "Skill + AI + a real client problem",
    },
    {
        "key": "youtube",
        "search": "YouTube creator smartphone video editing",
        "title": "YouTube Shorts",
        "hook": "Small videos can build a channel.",
        "steps": [
            ("1", "Solve one problem", "Give one useful answer."),
            ("2", "Hook fast", "Make the first seconds clear."),
            ("3", "Stay original", "Add your own explanation and examples."),
        ],
        "script": (
            "Small videos can build a channel. Solve one simple problem, make the opening clear, "
            "and keep the video useful. Your own explanation and examples are more valuable than "
            "copying someone else's content."
        ),
        "caption": "Useful + original + consistent beats empty hype.",
    },
    {
        "key": "digital-products",
        "search": "digital product laptop template creator",
        "title": "Digital products",
        "hook": "Create once. Improve over time.",
        "steps": [
            ("1", "Find a problem", "Look for something people repeatedly need."),
            ("2", "Make a simple solution", "Template, checklist or guide."),
            ("3", "Improve it", "Use customer feedback to make it better."),
        ],
        "script": (
            "Digital products can be simple. Find a problem people repeatedly have, "
            "turn your solution into a template, checklist or guide, and improve it from real feedback. "
            "The goal is usefulness, not a get-rich-quick promise."
        ),
        "caption": "Template • checklist • guide • useful resource",
    },
    {
        "key": "freelancing",
        "search": "freelancer laptop desk client work",
        "title": "Freelancing",
        "hook": "Don't sell 'anything'. Sell one result.",
        "steps": [
            ("1", "Pick one skill", "Start with something you can actually do."),
            ("2", "Package it", "Make the offer easy to understand."),
            ("3", "Show proof", "Create samples before chasing clients."),
        ],
        "script": (
            "Don't sell everything. Start with one skill you can actually do. "
            "Package it as one clear service, create a few strong samples, and show clients the result "
            "you can help them achieve."
        ),
        "caption": "One skill • one offer • clear proof",
    },
    {
        "key": "online-selling",
        "search": "online store ecommerce laptop smartphone",
        "title": "Online selling",
        "hook": "Before you buy stock, test demand.",
        "steps": [
            ("1", "Choose a problem", "Find something customers want solved."),
            ("2", "Test interest", "Use content or a small listing."),
            ("3", "Track the numbers", "Watch costs, sales and profit."),
        ],
        "script": (
            "Before buying lots of stock, test demand. Choose a product that solves a real problem, "
            "start small, and track your selling costs, fees, returns and actual profit. "
            "Sales are not the same thing as profit."
        ),
        "caption": "Revenue is not profit.",
    },
    {
        "key": "remote-work",
        "search": "remote work laptop home office",
        "title": "Remote work",
        "hook": "Want a remote income?",
        "steps": [
            ("1", "Build a useful skill", "Focus on a skill employers need."),
            ("2", "Make a simple CV", "Show results, not just duties."),
            ("3", "Apply consistently", "Use legitimate job platforms and company sites."),
        ],
        "script": (
            "Want a remote income? Build a skill employers actually need, make a simple CV that shows "
            "results, and apply consistently through legitimate job platforms or company career pages. "
            "Never pay someone just to get a job."
        ),
        "caption": "Never pay a stranger for a promised job.",
    },
    {
        "key": "print-on-demand",
        "search": "print on demand t shirt ecommerce laptop",
        "title": "Print on demand",
        "hook": "You can test designs without holding stock.",
        "steps": [
            ("1", "Choose a niche", "Make designs for a specific audience."),
            ("2", "Create original designs", "Avoid copyrighted characters and brands."),
            ("3", "Test demand", "Keep improving what people respond to."),
        ],
        "script": (
            "Print on demand lets you test original designs without storing inventory yourself. "
            "Choose a clear niche, create your own designs, and test demand. "
            "Avoid copyrighted characters, logos and artwork you do not have permission to use."
        ),
        "caption": "Original designs only.",
    },
    {
        "key": "online-course",
        "search": "online course laptop education creator",
        "title": "Online courses",
        "hook": "Know something useful? Teach it clearly.",
        "steps": [
            ("1", "Choose one outcome", "Teach one specific result."),
            ("2", "Break it down", "Use short practical lessons."),
            ("3", "Add examples", "Show exactly how to apply it."),
        ],
        "script": (
            "If you know something useful, you can turn it into a simple course. "
            "Choose one specific outcome, break it into short lessons, and use real examples. "
            "A clear result is more useful than a course packed with random information."
        ),
        "caption": "Teach one clear outcome.",
    },
    {
        "key": "ai-tools",
        "search": "AI tools laptop productivity",
        "title": "AI tools",
        "hook": "The tool isn't the business.",
        "steps": [
            ("1", "Find a boring task", "Look for work that takes too long."),
            ("2", "Use AI to speed it up", "Keep human review in the process."),
            ("3", "Sell the result", "Charge for useful work, not hype."),
        ],
        "script": (
            "The AI tool is not the business. Find a boring task that takes too long, "
            "use AI to speed up part of the workflow, review the result, and offer the finished service "
            "to someone who needs it."
        ),
        "caption": "Sell useful results, not AI hype.",
    },
    {
        "key": "side-hustle",
        "search": "side hustle laptop smartphone creator",
        "title": "Side hustle",
        "hook": "Start smaller than you think.",
        "steps": [
            ("1", "Choose one idea", "Don't start five things at once."),
            ("2", "Test it cheaply", "Get your first real feedback."),
            ("3", "Improve from evidence", "Keep what works and remove what doesn't."),
        ],
        "script": (
            "Starting a side hustle? Start smaller than you think. Pick one idea, test it cheaply, "
            "get real feedback, and improve from the results. You do not need a huge investment "
            "to learn whether an idea has demand."
        ),
        "caption": "Test first. Scale later.",
    },
]


# ============================================================
# HELPERS
# ============================================================

def run(cmd, check=True, capture=False):
    print(">", " ".join(str(x) for x in cmd))
    return subprocess.run(
        [str(x) for x in cmd],
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def require_program(name):
    if shutil.which(name) is None:
        raise RuntimeError(f"Required program not found: {name}")


def font_path(bold=False):
    candidates = [BOLD_FONT if bold else REGULAR_FONT,
                  SYSTEM_BOLD if bold else SYSTEM_REGULAR]
    for p in candidates:
        if p and p.exists():
            return p
    raise FileNotFoundError(
        "NotoSans fonts were not found. Put NotoSans-Regular.ttf and "
        "NotoSans-Bold.ttf inside the fonts/ folder."
    )


def F(size, bold=False):
    return ImageFont.truetype(str(font_path(bold)), size=size)


def text_width(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = word if not current else current + " " + word
        if text_width(draw, test, font) <= max_width:
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
    heights = []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        heights.append(box[3] - box[1])
    total = sum(heights) + spacing * (len(lines) - 1)
    yy = y - total / 2
    for line, h in zip(lines, heights):
        w = text_width(draw, line, font)
        draw.text(((VIDEO_WIDTH - w) / 2, yy), line, font=font, fill=fill)
        yy += h + spacing


def make_slide_base():
    img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), BG)
    d = ImageDraw.Draw(img)

    # Reference-style side geometry.
    d.polygon(
        [(0, 0), (145, 0), (95, 470), (0, 590)],
        fill=PALE_BLUE,
    )
    d.polygon(
        [(VIDEO_WIDTH, VIDEO_HEIGHT), (VIDEO_WIDTH - 155, VIDEO_HEIGHT),
         (VIDEO_WIDTH - 90, VIDEO_HEIGHT - 500), (VIDEO_WIDTH, VIDEO_HEIGHT - 600)],
        fill=PALE_BLUE,
    )

    # Small blue accent bars.
    d.rounded_rectangle((55, 92, 170, 112), 10, fill=BLUE)
    d.rounded_rectangle((910, 1780, 1025, 1800), 10, fill=BLUE)

    return img, d


def add_brand(d, title):
    # Small top brand line.
    f = F(28, bold=True)
    d.text((68, 142), "ONLINE EARNING", font=f, fill=BLUE)

    # Topic badge.
    badge_font = F(26, bold=True)
    tw = text_width(d, title.upper(), badge_font)
    x1 = VIDEO_WIDTH - 70 - tw - 44
    rounded_rect(d, (x1, 130, VIDEO_WIDTH - 70, 184), 20, fill=WHITE, outline=(220, 226, 234, 255), width=2)
    d.text((x1 + 22, 143), title.upper(), font=badge_font, fill=DARK)


def add_footer(d, text="FOLLOW FOR PRACTICAL ONLINE EARNING TIPS"):
    f = F(24, bold=True)
    tw = text_width(d, text, f)
    rounded_rect(
        d,
        ((VIDEO_WIDTH - tw) / 2 - 28, VIDEO_HEIGHT - 145,
         (VIDEO_WIDTH + tw) / 2 + 28, VIDEO_HEIGHT - 92),
        18,
        fill=DARK,
    )
    d.text(((VIDEO_WIDTH - tw) / 2, VIDEO_HEIGHT - 134), text, font=f, fill=WHITE)


def make_hook_slide(topic):
    img, d = make_slide_base()
    add_brand(d, topic["title"])

    # Number marker.
    rounded_rect(d, (75, 300, 205, 430), 34, fill=BLUE)
    d.text((111, 340), "01", font=F(54, bold=True), fill=WHITE)

    hook_font = F(78, bold=True)
    lines = wrap_text(d, topic["hook"], hook_font, 820)
    y = 500
    for line in lines:
        w = text_width(d, line, hook_font)
        d.text(((VIDEO_WIDTH - w) / 2, y), line, font=hook_font, fill=DARK)
        y += 98

    # Practical mini-card.
    rounded_rect(d, (120, 940, 960, 1390), 42, fill=WHITE, outline=(221, 227, 235, 255), width=3)
    d.ellipse((180, 1035, 280, 1135), fill=PALE_BLUE)
    d.text((210, 1045), "✓", font=F(52, bold=True), fill=BLUE)
    d.text((320, 1020), "PRACTICAL, NOT HYPE", font=F(30, bold=True), fill=BLUE)
    mini = "One clear idea • one useful action • realistic expectations"
    for i, line in enumerate(wrap_text(d, mini, F(34), 560)):
        d.text((320, 1080 + i * 52), line, font=F(34), fill=DARK)

    # Arrow.
    d.line((540, 1450, 540, 1550), fill=BLUE, width=12)
    d.polygon([(510, 1525), (570, 1525), (540, 1580)], fill=BLUE)

    add_footer(d)
    return img


def make_step_slide(topic, step_index):
    img, d = make_slide_base()
    add_brand(d, topic["title"])

    num, heading, body = topic["steps"][step_index]

    # Big number.
    rounded_rect(d, (76, 315, 240, 479), 44, fill=BLUE)
    nw = text_width(d, num, F(70, bold=True))
    d.text(((76 + 240 - nw) / 2, 345), num, font=F(70, bold=True), fill=WHITE)

    # Step heading.
    heading_font = F(62, bold=True)
    heading_lines = wrap_text(d, heading, heading_font, 700)
    y = 350
    for line in heading_lines:
        d.text((285, y), line, font=heading_font, fill=DARK)
        y += 78

    # Body card.
    rounded_rect(d, (95, 650, 985, 1080), 45, fill=WHITE, outline=(220, 226, 234, 255), width=3)
    body_font = F(40)
    body_lines = wrap_text(d, body, body_font, 760)
    y = 755
    for line in body_lines:
        d.text((160, y), line, font=body_font, fill=MUTED)
        y += 58

    # Check line.
    d.ellipse((125, 1155, 215, 1245), fill=PALE_BLUE)
    d.text((148, 1164), "✓", font=F(46, bold=True), fill=BLUE)
    d.text((250, 1172), "Keep it simple and useful.", font=F(34, bold=True), fill=DARK)

    # Decorative arrow.
    d.line((810, 1280, 930, 1390), fill=BLUE, width=10)
    d.polygon([(900, 1370), (945, 1405), (905, 1418)], fill=BLUE)

    add_footer(d)
    return img


def make_end_slide(topic):
    img, d = make_slide_base()
    add_brand(d, topic["title"])

    # Main CTA card.
    rounded_rect(d, (90, 390, 990, 1160), 52, fill=DARK)

    d.text((155, 505), "THE TAKEAWAY", font=F(30, bold=True), fill=PALE_BLUE)

    takeaway = topic["caption"]
    tf = F(60, bold=True)
    lines = wrap_text(d, takeaway, tf, 730)
    y = 600
    for line in lines:
        d.text((155, y), line, font=tf, fill=WHITE)
        y += 82

    # Blue CTA button.
    button_text = "FOLLOW FOR MORE"
    bf = F(32, bold=True)
    bw = text_width(d, button_text, bf)
    rounded_rect(d, ((VIDEO_WIDTH - bw) / 2 - 45, 1300,
                     (VIDEO_WIDTH + bw) / 2 + 45, 1390),
                 28, fill=BLUE)
    d.text(((VIDEO_WIDTH - bw) / 2, 1322), button_text, font=bf, fill=WHITE)

    # Disclaimer.
    disclaimer = "Results vary. No income is guaranteed."
    df = F(25)
    dw = text_width(d, disclaimer, df)
    d.text(((VIDEO_WIDTH - dw) / 2, 1480), disclaimer, font=df, fill=MUTED)

    add_footer(d, "SAVE THIS TIP • FOLLOW FOR MORE")
    return img


def create_scene_slides(topic, folder):
    slides = []
    slides.append(make_hook_slide(topic))

    # Use two practical steps to keep the Short moving.
    slides.append(make_step_slide(topic, 0))
    slides.append(make_step_slide(topic, 1))
    slides.append(make_step_slide(topic, 2))
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
# PEXELS
# ============================================================

def pexels_video(topic, destination):
    if not PEXELS_API_KEY:
        print("PEXELS_API_KEY not set. Using generated graphic background.")
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
    if not videos:
        return None

    random.shuffle(videos)

    for video in videos:
        files = video.get("video_files", [])
        files = sorted(
            files,
            key=lambda x: (
                0 if x.get("width", 0) >= x.get("height", 0) else 1,
                abs((x.get("height") or 1080) - 1920),
            ),
        )
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
                    print("Downloaded Pexels background:", destination)
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

def make_silent_background(output_file, duration):
    # Light background matching the reference design.
    run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0xF8FAFC:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={FPS}",
        "-t", f"{duration:.3f}",
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_file,
    ])


def make_scene_video(slide, voice, duration, output_file, pexels_bg=None):
    """
    Creates one scene. The designed slide is always on top.
    A small moving Pexels strip can be used as a subtle practical visual.
    """
    duration = max(1.8, duration)

    if pexels_bg and Path(pexels_bg).exists():
        # Put the Pexels clip into a modest card behind the graphic.
        # The card is intentionally not full-screen so the result feels edited,
        # not like a generic stock-video Short.
        filter_complex = (
            f"[0:v]scale=760:620:force_original_aspect_ratio=increase,"
            f"crop=760:620,setsar=1,"
            f"boxblur=1:1[bg];"
            f"[bg]eq=brightness=-0.02:saturation=0.82[bg2];"
            f"[bg2]format=rgba,colorchannelmixer=aa=0.26[bg3];"
            f"[1:v]format=rgba,"
            f"fade=t=in:st=0:d=0.35:alpha=1,"
            f"fade=t=out:st={max(0.4, duration-0.35):.3f}:d=0.35:alpha=1[slide];"
            f"[bg3][slide]overlay=160:980:format=auto,"
            f"format=yuv420p[v]"
        )

        # The slide itself has a solid background, so the subtle Pexels layer
        # is mainly visible in the designed card area through its alpha.
        run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", pexels_bg,
            "-loop", "1", "-i", slide,
            "-i", voice,
            "-t", f"{duration:.3f}",
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "2:a:0",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "24",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            output_file,
        ])
    else:
        filter_complex = (
            f"[0:v]format=rgba,"
            f"fade=t=in:st=0:d=0.35:alpha=1,"
            f"fade=t=out:st={max(0.4, duration-0.35):.3f}:d=0.35:alpha=1[slide]"
        )
        run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", slide,
            "-i", voice,
            "-t", f"{duration:.3f}",
            "-filter_complex", filter_complex,
            "-map", "[slide]",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "24",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            output_file,
        ])


def concat_scenes(scene_files, output_file):
    list_file = output_file.parent / "concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in scene_files:
            f.write(f"file '{Path(p).resolve()}'\n")

    run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_file,
    ])


# ============================================================
# SCRIPT / TIMING
# ============================================================

def split_script_into_scene_text(topic):
    # The narration is deliberately divided into natural chunks.
    # This is not word-by-word captioning; the graphic cards carry the key points.
    return [
        topic["hook"],
        topic["steps"][0][2],
        topic["steps"][1][2],
        topic["steps"][2][2],
        "Save this tip and follow for more practical online earning ideas.",
    ]


def fit_scene_duration(voice_duration):
    # Give the voice a little breathing room, but keep the video short.
    return max(1.9, min(7.0, voice_duration + 0.35))


def write_metadata(topic, output_file, total_duration):
    title = f"{topic['title']}: a practical online earning tip #shorts"

    description = (
        f"{topic['title']} explained simply. "
        f"This Short focuses on practical steps rather than unrealistic income promises.\n\n"
        "Results vary depending on skills, effort, market, location and eligibility. "
        "No income is guaranteed.\n\n"
        "#shorts #onlineearning #sidehustle #makemoneyonline "
        f"#{clean_text_for_filename(topic['key'])}"
    )

    tags = [
        "online earning",
        "make money online",
        "side hustle",
        "online business",
        "earning online",
        "digital income",
        "freelancing",
        "online work",
        "shorts",
        topic["key"],
    ]

    meta = {
        "title": title,
        "description": description,
        "tags": tags,
        "topic": topic["title"],
        "duration_seconds": round(total_duration, 2),
        "note": "Educational content. Results vary; no income guaranteed.",
    }

    meta_file = output_file.with_suffix(".txt")
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")


# ============================================================
# ONE SHORT
# ============================================================

def create_short(topic, number):
    folder = WORK_DIR / f"video_{number}"
    folder.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print(f"CREATING VIDEO {number}: {topic['title']}")
    print("=" * 70)

    slides = create_scene_slides(topic, folder)
    scene_texts = split_script_into_scene_text(topic)

    scene_files = []

    for i, (slide, text) in enumerate(zip(slides, scene_texts), start=1):
        voice_file = folder / f"voice_{i}.mp3"
        scene_file = folder / f"scene_{i}.mp4"

        print(f"Scene {i}: {text}")
        make_voice(text, voice_file)

        voice_duration = get_duration(voice_file)
        scene_duration = fit_scene_duration(voice_duration)

        if scene_duration < MIN_SECONDS and i == len(slides):
            scene_duration = MIN_SECONDS

        bg_file = folder / "pexels.mp4"
        if i == 1 and not bg_file.exists():
            pexels_video(topic, bg_file)

        bg = bg_file if bg_file.exists() else None

        make_scene_video(
            slide,
            voice_file,
            scene_duration,
            scene_file,
            pexels_bg=bg,
        )
        scene_files.append(scene_file)

    temp_final = folder / "joined.mp4"
    concat_scenes(scene_files, temp_final)

    duration = get_duration(temp_final)

    # If a rare long voiceover pushes it beyond the maximum, speed the audio/video
    # slightly. This preserves the complete narration better than hard-cutting it.
    if duration > MAX_SECONDS:
        factor = duration / MAX_SECONDS
        corrected = folder / "corrected.mp4"
        atempo = min(2.0, max(0.5, factor))
        run([
            "ffmpeg", "-y",
            "-i", temp_final,
            "-filter_complex",
            f"[0:v]setpts=PTS/{factor}[v];[0:a]atempo={atempo}[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            corrected,
        ])
        shutil.copy2(corrected, temp_final)
        duration = get_duration(temp_final)

    output_file = OUTPUT_DIR / f"online_earning_short_{number}.mp4"
    shutil.copy2(temp_final, output_file)

    write_metadata(topic, output_file, duration)

    print(f"Created: {output_file}")
    print(f"Duration: {duration:.2f} seconds")
    return output_file


# ============================================================
# MAIN
# ============================================================

def main():
    require_program("ffmpeg")
    require_program("ffprobe")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old generated videos from this run so the uploader does not
    # accidentally pick up stale files.
    for p in OUTPUT_DIR.glob("online_earning_short_*.mp4"):
        p.unlink(missing_ok=True)
    for p in OUTPUT_DIR.glob("online_earning_short_*.txt"):
        p.unlink(missing_ok=True)

    if not REGULAR_FONT.exists() or not BOLD_FONT.exists():
        print("WARNING: NotoSans fonts are missing from fonts/.")
        print("Expected:")
        print("  fonts/NotoSans-Regular.ttf")
        print("  fonts/NotoSans-Bold.ttf")

    selected = random.sample(TOPICS, SHORT_COUNT)

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
