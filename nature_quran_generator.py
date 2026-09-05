import os
import random
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ============================================================
# SETTINGS
# ============================================================

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

WIDTH = 1080
HEIGHT = 1920
VIDEO_SECONDS = 20

BASE = Path(".")
ASSETS = BASE / "assets"
OUTPUT = BASE / "output"
FONTS = BASE / "fonts"

ASSETS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

ARABIC_FONT = FONTS / "NotoNaskhArabic-Regular.otf"

# Nature topics
TOPICS = [
    "mountain sunrise",
    "ocean waves",
    "forest",
    "waterfall",
    "desert",
    "snow mountains",
    "lake",
    "ocean sunset",
    "rain forest",
    "night sky",
    "river",
    "cliffs"
]

# Short Quran verses suitable for Shorts
# Global Quran ayah numbers
QURAN_AYAHS = [
    171,   # 2:164
    1911,  # 16:10
    1914,  # 16:13
    1919,  # 16:18
    2834,  # 24:43
    3429,  # 30:20
    4079,  # 39:21
    4914,  # 55:13
    5244,  # 67:3
    5984   # 88:17
]

# ============================================================
# HELPERS
# ============================================================

def run(cmd):
    print("Running:", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def download_file(url, path):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    path.write_bytes(r.content)
    print("Downloaded:", path)


def get_json(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    if data.get("code") != 200:
        raise RuntimeError(f"API error: {data}")

    return data["data"]


# ============================================================
# PEXELS
# ============================================================

def get_pexels_video(topic, number):
    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": topic,
        "orientation": "portrait",
        "size": "large",
        "per_page": 20
    }

    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers=headers,
        params=params,
        timeout=60
    )

    r.raise_for_status()

    videos = r.json().get("videos", [])

    if not videos:
        raise RuntimeError(f"No Pexels videos found for: {topic}")

    # Prefer portrait/high-resolution videos
    candidates = []

    for video in videos:
        for vf in video.get("video_files", []):
            width = vf.get("width") or 0
            height = vf.get("height") or 0
            link = vf.get("link")

            if not link:
                continue

            if height >= width:
                score = width * height
                candidates.append((score, link, width, height))

    if not candidates:
        raise RuntimeError(f"No suitable portrait video for {topic}")

    candidates.sort(reverse=True)

    _, link, width, height = candidates[0]

    path = ASSETS / f"nature_{number}.mp4"

    print(
        f"Selected Pexels video: {topic} "
        f"{width}x{height}"
    )

    download_file(link, path)

    return path


# ============================================================
# QURAN
# ============================================================

def get_quran_ayah(global_number):
    arabic = get_json(
        f"https://api.alquran.cloud/v1/ayah/"
        f"{global_number}/quran-uthmani-quran-academy"
    )

    english = get_json(
        f"https://api.alquran.cloud/v1/ayah/"
        f"{global_number}/en.sahih"
    )

    audio = get_json(
        f"https://api.alquran.cloud/v1/ayah/"
        f"{global_number}/ar.alafasy"
    )

    return {
        "arabic": arabic["text"],
        "english": english["text"],
        "surah": arabic["surah"]["englishName"],
        "surah_number": arabic["surah"]["number"],
        "ayah": arabic["numberInSurah"],
        "audio": audio.get("audio")
    }


# ============================================================
# TEXT IMAGE
# ============================================================

def create_text_overlay(quran, output_path):

    image = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(image)

    # Fonts
    if not ARABIC_FONT.exists():
        raise FileNotFoundError(
            f"Arabic font not found: {ARABIC_FONT}"
        )

    arabic_font = ImageFont.truetype(
        str(ARABIC_FONT),
        68
    )

    english_font = ImageFont.truetype(
        "DejaVuSans.ttf",
        38
    )

    reference_font = ImageFont.truetype(
        "DejaVuSans.ttf",
        28
    )

    # Dark transparent panel
    panel_top = 560
    panel_bottom = 1430

    draw.rounded_rectangle(
        (55, panel_top, WIDTH - 55, panel_bottom),
        radius=35,
        fill=(0, 0, 0, 145)
    )

    # Arabic shaping
    reshaped = arabic_reshaper.reshape(quran["arabic"])
    arabic_text = get_display(reshaped)

    # Arabic wrapping
    words = arabic_text.split()
    arabic_lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=arabic_font
        )

        if bbox[2] - bbox[0] <= 900:
            current = test
        else:
            if current:
                arabic_lines.append(current)
            current = word

    if current:
        arabic_lines.append(current)

    y = 650

    for line in arabic_lines:
        bbox = draw.textbbox(
            (0, 0),
            line,
            font=arabic_font
        )

        text_width = bbox[2] - bbox[0]

        x = (WIDTH - text_width) // 2

        draw.text(
            (x, y),
            line,
            font=arabic_font,
            fill=(255, 255, 255, 255)
        )

        y += 90

    # English translation
    english_words = quran["english"].split()
    english_lines = []
    current = ""

    for word in english_words:
        test = f"{current} {word}".strip()

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=english_font
        )

        if bbox[2] - bbox[0] <= 850:
            current = test
        else:
            if current:
                english_lines.append(current)
            current = word

    if current:
        english_lines.append(current)

    y += 35

    for line in english_lines[:5]:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=english_font
        )

        text_width = bbox[2] - bbox[0]

        x = (WIDTH - text_width) // 2

        draw.text(
            (x, y),
            line,
            font=english_font,
            fill=(235, 235, 235, 255)
        )

        y += 55

    # Reference
    reference = (
        f"Qur'an {quran['surah']} "
        f"{quran['surah_number']}:{quran['ayah']}"
    )

    bbox = draw.textbbox(
        (0, 0),
        reference,
        font=reference_font
    )

    x = (WIDTH - (bbox[2] - bbox[0])) // 2

    draw.text(
        (x, 1350),
        reference,
        font=reference_font,
        fill=(210, 210, 210, 255)
    )

    image.save(output_path)

    print("Created text overlay:", output_path)


# ============================================================
# CREATE SHORT
# ============================================================

def create_short(video_path, overlay_path, audio_url, output_path):

    audio_path = ASSETS / "quran_audio.mp3"

    if audio_url:
        download_file(audio_url, audio_path)

    # 9:16 cinematic video
    video_input = [
        "-stream_loop",
        "-1",
        "-i",
        str(video_path)
    ]

    inputs = video_input

    if audio_url:
        inputs += [
            "-i",
            str(audio_path)
        ]

    inputs += [
        "-i",
        str(overlay_path)
    ]

    if audio_url:
        filter_complex = (
            "[0:v]"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1,"
            "eq=brightness=-0.03:saturation=1.08,"
            "format=yuv420p"
            "[bg];"
            "[2:v]"
            "format=rgba"
            "[txt];"
            "[bg][txt]"
            "overlay=0:0"
            "[v]"
        )
    else:
        filter_complex = (
            "[0:v]"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1,"
            "eq=brightness=-0.03:saturation=1.08,"
            "format=yuv420p"
            "[bg];"
            "[1:v]"
            "format=rgba"
            "[txt];"
            "[bg][txt]"
            "overlay=0:0"
            "[v]"
        )

    cmd = [
        "ffmpeg",
        "-y"
    ]

    cmd += inputs

    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]"
    ]

    if audio_url:
        cmd += [
            "-map",
            "1:a:0",
            "-t",
            str(VIDEO_SECONDS),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest"
        ]
    else:
        cmd += [
            "-t",
            str(VIDEO_SECONDS),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20"
        ]

    cmd += [
        "-movflags",
        "+faststart",
        str(output_path)
    ]

    run(cmd)

    print("Created:", output_path)


# ============================================================
# MAIN
# ============================================================

def main():

    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY is missing"
        )

    if not ARABIC_FONT.exists():
        raise RuntimeError(
            "Arabic font missing. "
            "Check fonts/NotoNaskhArabic-Regular.otf"
        )

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Different 3 topics every day
    random.seed(today)

    topics = random.sample(TOPICS, 3)

    print("Today's topics:")
    for topic in topics:
        print("-", topic)

    # Pick 3 different Quran verses
    ayahs = random.sample(QURAN_AYAHS, 3)

    metadata = []

    for i in range(3):

        print("\n==============================")
        print(f"CREATING SHORT {i + 1}")
        print("==============================")

        topic = topics[i]
        global_ayah = ayahs[i]

        # Nature video
        nature_video = get_pexels_video(
            topic,
            i + 1
        )

        # Quran
        quran = get_quran_ayah(
            global_ayah
        )

        print(
            f"Quran: {quran['surah']} "
            f"{quran['surah_number']}:{quran['ayah']}"
        )

        # Overlay
        overlay = ASSETS / f"text_{i + 1}.png"

        create_text_overlay(
            quran,
            overlay
        )

        # Output
        output = OUTPUT / (
            f"nature_quran_short_{i + 1}.mp4"
        )

        create_short(
            nature_video,
            overlay,
            quran["audio"],
            output
        )

        metadata.append(
            f"""
SHORT {i + 1}
Nature: {topic}
Quran: {quran['surah']} {quran['surah_number']}:{quran['ayah']}

Arabic:
{quran['arabic']}

English:
{quran['english']}

Suggested hashtags:
#Quran #QuranRecitation #Islam #Allah
#IslamicReminder #Nature #QuranShorts #Shorts

Nature footage source:
Pexels

Quran text/translation:
Al Quran Cloud / Saheeh International

Recitation:
Alafasy via Al Quran Cloud
"""
        )

    metadata_path = OUTPUT / "metadata.txt"

    metadata_path.write_text(
        "\n".join(metadata),
        encoding="utf-8"
    )

    print("\n================================")
    print("ALL 3 SHORTS CREATED SUCCESSFULLY")
    print("================================")


if __name__ == "__main__":
    main()
