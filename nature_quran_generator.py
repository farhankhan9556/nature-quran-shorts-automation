import os
import random
import subprocess
from pathlib import Path
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# SETTINGS
# ============================================================

WIDTH = 1080
HEIGHT = 1920
VIDEO_SECONDS = 20

BASE = Path(__file__).resolve().parent

ASSETS = BASE / "assets"
OUTPUT = BASE / "output"
FONTS = BASE / "fonts"

ASSETS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)
FONTS.mkdir(exist_ok=True)

ARABIC_FONT = FONTS / "NotoNaskhArabic-Regular.otf"

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

if not PEXELS_API_KEY:
    raise RuntimeError("PEXELS_API_KEY is missing")

if not ARABIC_FONT.exists():
    raise RuntimeError(
        f"Font not found: {ARABIC_FONT}"
    )


# ============================================================
# NATURE TOPICS
# ============================================================

TOPICS = [
    "mountain sunrise",
    "ocean waves",
    "waterfall",
    "forest sunlight",
    "desert sunset",
    "snow mountain",
    "beautiful lake",
    "ocean sunset",
    "rain forest",
    "night sky stars",
    "river nature",
    "dramatic cliffs",
]


# ============================================================
# QURAN VERSES
# ============================================================

QURAN_AYAHS = [
    171,
    1911,
    1914,
    1919,
    2834,
    3429,
    4079,
    4914,
    5244,
    5984,
]


# ============================================================
# HTTP REQUEST
# ============================================================

def get_json(url, **kwargs):

    response = requests.get(
        url,
        timeout=60,
        **kwargs
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# DOWNLOAD FILE
# ============================================================

def download_file(url, path):

    print(
        f"Downloading: {url}"
    )

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    with open(
        path,
        "wb"
    ) as f:

        f.write(
            response.content
        )

    print(
        f"Saved: {path}"
    )


# ============================================================
# FONT
# ============================================================

def get_font(size):

    return ImageFont.truetype(
        str(ARABIC_FONT),
        size
    )


# ============================================================
# GET NATURE VIDEO
# ============================================================

def get_nature_video(
    topic
):

    url = (
        "https://api.pexels.com/v1/videos/search"
    )

    headers = {
        "Authorization":
        PEXELS_API_KEY
    }

    params = {
        "query": topic,
        "orientation": "portrait",
        "size": "large",
        "per_page": 20
    }

    data = get_json(
        url,
        headers=headers,
        params=params
    )

    videos = data.get(
        "videos",
        []
    )

    if not videos:

        raise RuntimeError(
            f"No Pexels videos found for: "
            f"{topic}"
        )

    candidates = []

    # Prefer portrait HD
    for video in videos:

        for vf in video.get(
            "video_files",
            []
        ):

            width = (
                vf.get("width") or 0
            )

            height = (
                vf.get("height") or 0
            )

            if (
                height > width
                and width >= 720
            ):

                candidates.append(
                    vf
                )

    # Fallback
    if not candidates:

        for video in videos:

            candidates.extend(
                video.get(
                    "video_files",
                    []
                )
            )

    if not candidates:

        raise RuntimeError(
            "No usable Pexels video found"
        )

    # Highest resolution
    candidates.sort(
        key=lambda x:
        (x.get("width") or 0)
        *
        (x.get("height") or 0),
        reverse=True
    )

    selected = candidates[0]

    output = (
        ASSETS /
        "nature_source_1.mp4"
    )

    print()
    print(
        f"Nature video: {topic}"
    )

    print(
        "Resolution:",
        selected.get("width"),
        "x",
        selected.get("height")
    )

    download_file(
        selected["link"],
        output
    )

    return output


# ============================================================
# GET QURAN DATA
# ============================================================

def get_quran_data(
    global_ayah
):

    # Arabic Qur'an text
    arabic_url = (
        "https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/quran-uthmani"
    )

    # Alafasy recitation
    audio_url = (
        "https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/ar.alafasy"
    )

    arabic_data = get_json(
        arabic_url
    )["data"]

    audio_data = get_json(
        audio_url
    )["data"]

    return {
        "arabic":
        arabic_data["text"],

        "surah":
        arabic_data["surah"]["englishName"],

        "surah_arabic":
        arabic_data["surah"]["name"],

        "ayah":
        arabic_data["numberInSurah"],

        "audio":
        audio_data["audio"]
    }


# ============================================================
# ARABIC TEXT WRAPPING
#
# IMPORTANT:
# We DO NOT reverse or reshape the Arabic manually.
# Pillow + libraqm handles Arabic RTL rendering.
# ============================================================

def wrap_arabic(
    draw,
    text,
    text_font,
    max_width
):

    words = text.split()

    lines = []

    current = ""

    for word in words:

        if current:

            test = (
                current +
                " " +
                word
            )

        else:

            test = word

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=text_font,
            direction="rtl",
            language="ar"
        )

        width = (
            bbox[2] -
            bbox[0]
        )

        if width <= max_width:

            current = test

        else:

            if current:
                lines.append(
                    current
                )

            current = word

    if current:
        lines.append(
            current
        )

    return lines


# ============================================================
# FIND BEST ARABIC FONT SIZE
# ============================================================

def fit_arabic(
    draw,
    text,
    max_width
):

    for size in range(
        105,
        55,
        -2
    ):

        text_font = get_font(
            size
        )

        lines = wrap_arabic(
            draw,
            text,
            text_font,
            max_width
        )

        if len(lines) <= 3:

            return (
                text_font,
                lines
            )

    text_font = get_font(
        56
    )

    return (
        text_font,
        wrap_arabic(
            draw,
            text,
            text_font,
            max_width
        )
    )


# ============================================================
# CREATE CLEAN QURAN TEXT OVERLAY
# ============================================================

def create_quran_overlay(
    quran,
    output_path
):

    image = Image.new(
        "RGBA",
        (
            WIDTH,
            HEIGHT
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    draw = ImageDraw.Draw(
        image
    )

    center_x = WIDTH // 2

    # ========================================================
    # ARABIC VERSE
    # ========================================================

    arabic_font, lines = fit_arabic(
        draw,
        quran["arabic"],
        900
    )

    # Similar position to reference video
    start_y = 1060

    line_spacing = 18

    for line in lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=arabic_font,
            direction="rtl",
            language="ar"
        )

        text_height = (
            bbox[3] -
            bbox[1]
        )

        # ----------------------------------------------------
        # Dark shadow
        # ----------------------------------------------------

        draw.text(
            (
                center_x + 4,
                start_y + 5
            ),
            line,
            font=arabic_font,
            fill=(
                0,
                0,
                0,
                230
            ),
            anchor="ma",
            direction="rtl",
            language="ar"
        )

        # ----------------------------------------------------
        # Soft shadow
        # ----------------------------------------------------

        draw.text(
            (
                center_x + 2,
                start_y + 2
            ),
            line,
            font=arabic_font,
            fill=(
                0,
                0,
                0,
                160
            ),
            anchor="ma",
            direction="rtl",
            language="ar"
        )

        # ----------------------------------------------------
        # White Arabic
        # ----------------------------------------------------

        draw.text(
            (
                center_x,
                start_y
            ),
            line,
            font=arabic_font,
            fill=(
                255,
                255,
                255,
                255
            ),
            anchor="ma",
            direction="rtl",
            language="ar"
        )

        start_y += (
            text_height +
            line_spacing
        )

    # ========================================================
    # SURAH + VERSE
    # ========================================================

    reference_font = get_font(
        27
    )

    reference = (
        f"{quran['surah']}  •  "
        f"Verse {quran['ayah']}"
    )

    draw.text(
        (
            center_x,
            start_y + 38
        ),
        reference,
        font=reference_font,
        fill=(
            255,
            255,
            255,
            215
        ),
        anchor="ma"
    )

    # ========================================================
    # SAVE OVERLAY
    # ========================================================

    image.save(
        output_path
    )

    print(
        f"Overlay created: {output_path}"
    )


# ============================================================
# CREATE THE VIDEO
# ============================================================

def create_video(
    topic,
    ayah_number
):

    print()
    print(
        "=========================================="
    )

    print(
        "Creating ONE test Short"
    )

    print(
        f"Nature: {topic}"
    )

    # --------------------------------------------------------
    # Nature
    # --------------------------------------------------------

    nature_video = get_nature_video(
        topic
    )

    # --------------------------------------------------------
    # Quran
    # --------------------------------------------------------

    quran = get_quran_data(
        ayah_number
    )

    print(
        f"Qur'an: "
        f"{quran['surah']} "
        f"Verse {quran['ayah']}"
    )

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    overlay = (
        ASSETS /
        "quran_overlay_1.png"
    )

    audio = (
        ASSETS /
        "quran_audio_1.mp3"
    )

    output = (
        OUTPUT /
        "nature_quran_short_1.mp4"
    )

    # --------------------------------------------------------
    # Create overlay
    # --------------------------------------------------------

    create_quran_overlay(
        quran,
        overlay
    )

    # --------------------------------------------------------
    # Download recitation
    # --------------------------------------------------------

    download_file(
        quran["audio"],
        audio
    )

    # ========================================================
    # CINEMATIC FILTER
    # ========================================================

    filter_complex = (

        # ----------------------------------------------------
        # Scale to 9:16
        # ----------------------------------------------------

        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fps=30"

        "[base];"

        # ----------------------------------------------------
        # Cinematic color
        # ----------------------------------------------------

        "[base]"
        "eq="
        "brightness=-0.07:"
        "contrast=1.08:"
        "saturation=0.92"

        "[dark];"

        # ----------------------------------------------------
        # Soft vignette
        # ----------------------------------------------------

        "[dark]"
        "vignette=PI/5"

        "[cinematic];"

        # ----------------------------------------------------
        # Add Arabic
        # ----------------------------------------------------

        "[cinematic][1:v]"
        "overlay=0:0"

        "[v]"
    )

    # ========================================================
    # FFMPEG COMMAND
    # ========================================================

    command = [

        "ffmpeg",

        "-y",

        # Nature video
        "-stream_loop",
        "-1",

        "-i",
        str(nature_video),

        # Transparent text overlay
        "-loop",
        "1",

        "-i",
        str(overlay),

        # Quran audio
        "-i",
        str(audio),

        # Filter
        "-filter_complex",
        filter_complex,

        # Video stream
        "-map",
        "[v]",

        # Audio stream
        "-map",
        "2:a:0",

        # Exactly 20 seconds
        "-t",
        str(VIDEO_SECONDS),

        # Video encoding
        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "19",

        "-pix_fmt",
        "yuv420p",

        # Audio encoding
        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "44100",

        # YouTube compatibility
        "-movflags",
        "+faststart",

        str(output)
    ]

    print()
    print(
        "Rendering video..."
    )

    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # ========================================================
    # FFMPEG ERROR
    # ========================================================

    if result.returncode != 0:

        print()
        print(
            "=========================================="
        )

        print(
            "FFMPEG ERROR"
        )

        print(
            "=========================================="
        )

        print(
            result.stderr
        )

        print(
            "=========================================="
        )

        raise RuntimeError(
            "FFmpeg failed with exit code "
            f"{result.returncode}"
        )

    # ========================================================
    # CHECK VIDEO
    # ========================================================

    if not output.exists():

        raise RuntimeError(
            "Output video was not created"
        )

    file_size = output.stat().st_size

    if file_size < 10000:

        raise RuntimeError(
            "Output video is too small"
        )

    print()
    print(
        "=========================================="
    )

    print(
        "SUCCESS!"
    )

    print(
        f"Video: {output}"
    )

    print(
        f"Size: "
        f"{file_size / 1024 / 1024:.2f} MB"
    )

    print(
        "=========================================="
    )

    return quran


# ============================================================
# SELECT ONE TOPIC + ONE AYAH
# ============================================================

today = int(
    datetime.now().strftime(
        "%Y%m%d"
    )
)

random.seed(
    today
)

selected_topic = random.choice(
    TOPICS
)

selected_ayah = random.choice(
    QURAN_AYAHS
)


# ============================================================
# CREATE ONE VIDEO
# ============================================================

quran = create_video(
    selected_topic,
    selected_ayah
)


# ============================================================
# CREATE METADATA
# ============================================================

metadata_file = (
    OUTPUT /
    "metadata.txt"
)

title = (
    f"{selected_topic.title()} "
    f"| Beautiful Qur'an Reminder"
)

description = (
    "A peaceful reflection on the beauty "
    "of Allah's creation and the Holy Qur'an.\n\n"

    f"Qur'an: {quran['surah']} "
    f"Verse {quran['ayah']}\n\n"

    "Recitation: Mishary Rashid Alafasy\n"

    "Qur'an data and recitation: "
    "Al Quran Cloud\n\n"

    "Nature footage: Pexels\n\n"

    "#Quran "
    "#QuranRecitation "
    "#Islam "
    "#Allah "
    "#IslamicShorts "
    "#Nature "
    "#NatureShorts "
    "#QuranVerses "
    "#IslamicReminder "
    "#Muslim"
)

with open(
    metadata_file,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        "NATURE QURAN SHORT\n"
        "============================\n\n"
    )

    file.write(
        f"TITLE:\n{title}\n\n"
    )

    file.write(
        f"DESCRIPTION:\n{description}\n\n"
    )

    file.write(
        f"SURAH:\n"
        f"{quran['surah']} "
        f"({quran['surah_arabic']})\n\n"
    )

    file.write(
        f"VERSE:\n"
        f"{quran['ayah']}\n\n"
    )

    file.write(
        f"ARABIC:\n"
        f"{quran['arabic']}\n"
    )


print()
print(
    "=========================================="
)

print(
    "ONE TEST VIDEO COMPLETED"
)

print(
    "=========================================="
)
