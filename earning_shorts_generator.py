import os
import json
import math
import random
import shutil
import subprocess
import textwrap
from pathlib import Path
from datetime import datetime, timezone

import requests
import edge_tts

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# CONFIGURATION
# ============================================================

WIDTH = 1080
HEIGHT = 1920
FPS = 30

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
TEMP = ROOT / "temp"
FONTS = ROOT / "fonts"

TOPICS_FILE = ROOT / "earning_topics.json"

VOICE = "en-US-GuyNeural"

VIDEO_COUNT = 3

# Background video/image source.
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()

RANDOM_SEED = int(datetime.now(timezone.utc).strftime("%Y%m%d"))

random.seed(RANDOM_SEED)


# ============================================================
# DIRECTORIES
# ============================================================

OUTPUT.mkdir(exist_ok=True)
TEMP.mkdir(exist_ok=True)
FONTS.mkdir(exist_ok=True)


# ============================================================
# FONTS
# ============================================================

REGULAR_FONT = FONTS / "NotoSans-Regular.ttf"
BOLD_FONT = FONTS / "NotoSans-Bold.ttf"


def get_font(size, bold=False):
    path = BOLD_FONT if bold else REGULAR_FONT

    if path.exists():
        return ImageFont.truetype(str(path), size)

    return ImageFont.truetype(
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        size
    )


# ============================================================
# LOAD TOPICS
# ============================================================

def load_topics():
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# CLEAN OUTPUT
# ============================================================

def clean_previous_output():
    for item in OUTPUT.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

    for item in TEMP.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


# ============================================================
# WEBSITE CHECK
# ============================================================

def check_website(url):
    try:
        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/140 Safari/537.36"
            }
        )

        return {
            "status": response.status_code,
            "ok": response.ok,
            "url": response.url
        }

    except Exception as e:
        return {
            "status": 0,
            "ok": False,
            "url": url,
            "error": str(e)
        }


# ============================================================
# PLAYWRIGHT WEBSITE SCREENSHOT
# ============================================================

def capture_website(url, filename):
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            page = browser.new_page(
                viewport={
                    "width": 1280,
                    "height": 720
                },
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/140.0 Safari/537.36"
                )
            )

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(4000)

            page.screenshot(
                path=str(filename),
                full_page=False
            )

            browser.close()

            return True

    except Exception as e:
        print(f"Website screenshot failed: {e}")
        return False


# ============================================================
# PEXELS BACKGROUND
# ============================================================

def download_pexels_background(query, filename):
    if not PEXELS_API_KEY:
        return False

    try:

        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={
                "Authorization": PEXELS_API_KEY
            },
            params={
                "query": query,
                "per_page": 10,
                "orientation": "portrait"
            },
            timeout=30
        )

        if not response.ok:
            return False

        data = response.json()

        photos = data.get("photos", [])

        if not photos:
            return False

        photo = random.choice(photos)

        url = photo["src"]["portrait"]

        image_response = requests.get(
            url,
            timeout=60
        )

        if not image_response.ok:
            return False

        filename.write_bytes(image_response.content)

        return True

    except Exception as e:
        print(f"Pexels error: {e}")
        return False


# ============================================================
# FALLBACK BACKGROUND
# ============================================================

def create_gradient_background(filename):
    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (20, 24, 32)
    )

    draw = ImageDraw.Draw(image)

    for y in range(HEIGHT):

        ratio = y / HEIGHT

        r = int(18 + ratio * 15)
        g = int(22 + ratio * 18)
        b = int(32 + ratio * 25)

        draw.line(
            [(0, y), (WIDTH, y)],
            fill=(r, g, b)
        )

    image = image.filter(
        ImageFilter.GaussianBlur(1)
    )

    image.save(filename)


# ============================================================
# IMAGE PREPARATION
# ============================================================

def fit_image(image, width, height):

    image = image.convert("RGB")

    source_ratio = image.width / image.height
    target_ratio = width / height

    if source_ratio > target_ratio:

        new_height = height

        new_width = int(
            height * source_ratio
        )

    else:

        new_width = width

        new_height = int(
            width / source_ratio
        )

    image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )

    left = (new_width - width) // 2
    top = (new_height - height) // 2

    image = image.crop(
        (
            left,
            top,
            left + width,
            top + height
        )
    )

    return image


# ============================================================
# CREATE SCRIPT
# ============================================================

def create_script(topic):

    lines = []

    lines.append(topic["hook"])
    lines.append(
        "Let's go through the process step by step."
    )

    for index, step in enumerate(topic["steps"], 1):
        lines.append(
            f"Step {index}. {step}"
        )

    lines.append(topic["calculation"])
    lines.append(topic["warning"])

    lines.append(
        "Follow for more practical online earning guides."
    )

    return " ".join(lines)


# ============================================================
# CREATE VOICE
# ============================================================

async def create_voice(text, filename):

    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate="+3%",
        pitch="+1Hz"
    )

    await communicate.save(str(filename))


def generate_voice(text, filename):

    import asyncio

    asyncio.run(
        create_voice(
            text,
            filename
        )
    )


# ============================================================
# GET AUDIO DURATION
# ============================================================

def get_audio_duration(filename):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(filename)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    try:
        return float(result.stdout.strip())
    except Exception:
        return 45.0


# ============================================================
# WRAP TEXT
# ============================================================

def wrap_text(draw, text, font, max_width):

    words = text.split()

    lines = []
    current = ""

    for word in words:

        test = (
            current + " " + word
        ).strip()

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        width = bbox[2] - bbox[0]

        if width <= max_width:
            current = test
        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


# ============================================================
# DRAW CENTERED TEXT
# ============================================================

def draw_centered_text(
    image,
    text,
    y,
    font,
    max_width,
    box=True
):

    draw = ImageDraw.Draw(image)

    lines = wrap_text(
        draw,
        text,
        font,
        max_width
    )

    line_height = int(
        font.size * 1.25
    )

    total_height = (
        line_height * len(lines)
    )

    padding = 35

    if box:

        box_height = (
            total_height +
            padding * 2
        )

        box_y1 = y - padding

        box_y2 = (
            y +
            box_height -
            padding
        )

        draw.rounded_rectangle(
            (
                55,
                box_y1,
                WIDTH - 55,
                box_y2
            ),
            radius=35,
            fill=(0, 0, 0, 190)
        )

    current_y = y

    for line in lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        text_width = (
            bbox[2] - bbox[0]
        )

        x = (
            WIDTH -
            text_width
        ) // 2

        draw.text(
            (
                x + 3,
                current_y + 3
            ),
            line,
            font=font,
            fill=(0, 0, 0)
        )

        draw.text(
            (
                x,
                current_y
            ),
            line,
            font=font,
            fill=(255, 255, 255)
        )

        current_y += line_height

    return current_y


# ============================================================
# CREATE VIDEO FRAMES
# ============================================================

def create_frames(
    topic,
    duration,
    background_path,
    website_path,
    video_number
):

    frame_dir = TEMP / f"frames_{video_number}"

    if frame_dir.exists():
        shutil.rmtree(frame_dir)

    frame_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    background = Image.open(
        background_path
    )

    background = fit_image(
        background,
        WIDTH,
        HEIGHT
    )

    website = None

    if website_path and website_path.exists():

        website = Image.open(
            website_path
        ).convert("RGB")

    total_frames = int(
        duration * FPS
    )

    steps = topic["steps"]

    hook_duration = min(
        4.0,
        duration * 0.09
    )

    intro_duration = min(
        2.5,
        duration * 0.06
    )

    remaining = max(
        1,
        duration -
        hook_duration -
        intro_duration
    )

    step_duration = remaining / (
        len(steps) + 2
    )

    for frame_no in range(total_frames):

        time_sec = (
            frame_no / FPS
        )

        image = background.copy()

        # Dark overlay
        overlay = Image.new(
            "RGBA",
            image.size,
            (0, 0, 0, 75)
        )

        image = Image.alpha_composite(
            image.convert("RGBA"),
            overlay
        ).convert("RGB")

        draw = ImageDraw.Draw(image)

        # ---------------------------------
        # TOP BRAND
        # ---------------------------------

        brand_font = get_font(
            42,
            bold=True
        )

        draw.rounded_rectangle(
            (45, 45, 470, 120),
            radius=30,
            fill=(0, 0, 0)
        )

        draw.text(
            (75, 62),
            "ONLINE EARNING",
            font=brand_font,
            fill=(255, 255, 255)
        )

        # ---------------------------------
        # HOOK
        # ---------------------------------

        if time_sec < hook_duration:

            hook_font = get_font(
                72,
                bold=True
            )

            draw_centered_text(
                image,
                topic["hook"],
                520,
                hook_font,
                WIDTH - 140
            )

        # ---------------------------------
        # INTRO
        # ---------------------------------

        elif time_sec < (
            hook_duration +
            intro_duration
        ):

            font = get_font(
                68,
                bold=True
            )

            draw_centered_text(
                image,
                "REAL WEBSITE • STEP BY STEP",
                600,
                font,
                WIDTH - 120
            )

        # ---------------------------------
        # STEPS
        # ---------------------------------

        else:

            step_time = (
                time_sec -
                hook_duration -
                intro_duration
            )

            step_index = int(
                step_time //
                step_duration
            )

            # Last stages
            if step_index >= len(steps):

                # Calculation / warning section

                final_index = (
                    step_index -
                    len(steps)
                )

                if final_index == 0:

                    font = get_font(
                        65,
                        bold=True
                    )

                    draw_centered_text(
                        image,
                        topic["calculation"],
                        580,
                        font,
                        WIDTH - 120
                    )

                else:

                    font = get_font(
                        52,
                        bold=True
                    )

                    draw_centered_text(
                        image,
                        topic["warning"],
                        560,
                        font,
                        WIDTH - 120
                    )

            else:

                step = steps[
                    step_index
                ]

                # Website demonstration panel

                if website is not None:

                    website_copy = website.copy()

                    website_copy.thumbnail(
                        (920, 700),
                        Image.Resampling.LANCZOS
                    )

                    wx = (
                        WIDTH -
                        website_copy.width
                    ) // 2

                    wy = 280

                    image.paste(
                        website_copy,
                        (
                            wx,
                            wy
                        )
                    )

                    # border

                    draw = ImageDraw.Draw(
                        image
                    )

                    draw.rounded_rectangle(
                        (
                            wx - 8,
                            wy - 8,
                            wx +
                            website_copy.width +
                            8,
                            wy +
                            website_copy.height +
                            8
                        ),
                        radius=18,
                        outline=(255, 255, 255),
                        width=5
                    )

                number_font = get_font(
                    70,
                    bold=True
                )

                draw.ellipse(
                    (
                        55,
                        1070,
                        175,
                        1190
                    ),
                    fill=(0, 0, 0)
                )

                draw.text(
                    (
                        91,
                        1090
                    ),
                    str(step_index + 1),
                    font=number_font,
                    fill=(255, 255, 255)
                )

                step_font = get_font(
                    54,
                    bold=True
                )

                draw_centered_text(
                    image,
                    step,
                    1260,
                    step_font,
                    WIDTH - 160
                )

        # ---------------------------------
        # FOOTER
        # ---------------------------------

        footer_font = get_font(
            35,
            bold=False
        )

        footer = (
            "Research • Learn • Test • Build"
        )

        draw.text(
            (
                60,
                HEIGHT - 100
            ),
            footer,
            font=footer_font,
            fill=(235, 235, 235)
        )

        frame_file = (
            frame_dir /
            f"frame_{frame_no:06d}.jpg"
        )

        image.save(
            frame_file,
            quality=92
        )

    return frame_dir


# ============================================================
# BUILD MP4
# ============================================================

def build_video(
    frame_dir,
    audio_file,
    output_file
):

    silent_video = (
        TEMP /
        f"{output_file.stem}_silent.mp4"
    )

    # Create video from JPEG sequence
    command = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(frame_dir / "frame_%06d.jpg"),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(silent_video)
    ]

    subprocess.run(
        command,
        check=True
    )

    # Add voice
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(silent_video),
        "-i",
        str(audio_file),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_file)
    ]

    subprocess.run(
        command,
        check=True
    )


# ============================================================
# METADATA
# ============================================================

def create_metadata(topic, video_number):

    title_templates = [
        "How to Build Toward $500/Month with {name}",
        "{name}: Step-by-Step Beginner Guide",
        "How {name} Works for Online Income",
        "Start {name} the Right Way",
        "{name} Explained in Simple Steps"
    ]

    title = random.choice(
        title_templates
    ).format(
        name=topic["name"]
    )

    hashtags = (
        "#OnlineEarning "
        "#MakeMoneyOnline "
        "#SideHustle "
        "#MoneyTips "
        "#EarnOnline "
        "#Shorts"
    )

    description = f"""
{topic["name"]} — practical step-by-step guide.

Website:
{topic["website"]}

Important:
This video is for educational purposes. Income is not guaranteed. Results depend on eligibility, skills, demand, platform rules, competition and other factors.

Official information:
{topic["source"]}

Video {video_number} of today's online earning series.

{hashtags}
""".strip()

    metadata_file = (
        OUTPUT /
        f"short_{video_number}_metadata.txt"
    )

    metadata_file.write_text(
        f"TITLE:\n{title}\n\n"
        f"DESCRIPTION:\n{description}\n\n"
        f"TAGS:\n"
        f"online earning, make money online, "
        f"side hustle, earning money, "
        f"work from home, online income, "
        f"money tips, {topic['category']}",
        encoding="utf-8"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ONLINE EARNING SHORTS GENERATOR")
    print("=" * 70)

    clean_previous_output()

    topics = load_topics()

    if len(topics) < VIDEO_COUNT:
        raise RuntimeError(
            "Not enough topics in earning_topics.json"
        )

    # Randomly choose 3 topics every day
    selected_topics = random.sample(
        topics,
        VIDEO_COUNT
    )

    for video_number, topic in enumerate(
        selected_topics,
        start=1
    ):

        print()
        print(
            f"===== VIDEO {video_number}: "
            f"{topic['name']} ====="
        )

        website_status = check_website(
            topic["website"]
        )

        print(
            "Website status:",
            website_status
        )

        website_file = (
            TEMP /
            f"website_{video_number}.png"
        )

        screenshot_ok = capture_website(
            topic["website"],
            website_file
        )

        if not screenshot_ok:

            print(
                "Website screenshot unavailable."
            )

            website_file = None

        background_file = (
            TEMP /
            f"background_{video_number}.jpg"
        )

        background_ok = (
            download_pexels_background(
                (
                    topic["category"] +
                    " business online money"
                ),
                background_file
            )
        )

        if not background_ok:

            print(
                "Using generated background."
            )

            create_gradient_background(
                background_file
            )

        script = create_script(
            topic
        )

        print()
        print("SCRIPT:")
        print(script)

        voice_file = (
            TEMP /
            f"voice_{video_number}.mp3"
        )

        print(
            "Generating voice..."
        )

        generate_voice(
            script,
            voice_file
        )

        duration = get_audio_duration(
            voice_file
        )

        # Keep Shorts practical
        duration = max(
            30,
            min(duration, 60)
        )

        print(
            f"Audio duration: {duration:.2f}s"
        )

        frame_dir = create_frames(
            topic,
            duration,
            background_file,
            website_file,
            video_number
        )

        output_video = (
            OUTPUT /
            f"online_earning_short_{video_number}.mp4"
        )

        print(
            "Building video..."
        )

        build_video(
            frame_dir,
            voice_file,
            output_video
        )

        create_metadata(
            topic,
            video_number
        )

        print(
            f"Created: {output_video}"
        )

    print()
    print("=" * 70)
    print("3 SHORTS COMPLETED")
    print("=" * 70)

    # Save daily selection
    selected_file = (
        OUTPUT /
        "daily_topics.txt"
    )

    selected_file.write_text(
        "\n".join(
            topic["name"]
            for topic in selected_topics
        ),
        encoding="utf-8"
    )


if __name__ == "__main__":
    main()
