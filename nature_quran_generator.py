import os
import random
import subprocess
from pathlib import Path
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display


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
        f"Arabic font not found: {ARABIC_FONT}"
    )


# ============================================================
# NATURE TOPICS
# ============================================================

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
    "cliffs",
]


# ============================================================
# QURAN VERSES
# Global Ayah Numbers from Al Quran Cloud
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
# HTTP HELPER
# ============================================================

def request_json(url, **kwargs):

    response = requests.get(
        url,
        timeout=60,
        **kwargs
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# DOWNLOAD HELPER
# ============================================================

def download_file(url, path):

    print(f"Downloading: {url}")

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    with open(path, "wb") as file:
        file.write(response.content)

    print(f"Saved: {path}")


# ============================================================
# FONT
# ============================================================

def get_font(size):

    return ImageFont.truetype(
        str(ARABIC_FONT),
        size
    )


# ============================================================
# ARABIC SHAPING
# ============================================================

def shape_arabic(text):

    reshaped = arabic_reshaper.reshape(text)

    return get_display(reshaped)


# ============================================================
# ARABIC TEXT WRAPPING
# ============================================================

def wrap_arabic(
    text,
    font,
    max_width
):

    words = text.split()

    lines = []

    current = ""

    test_image = Image.new(
        "RGBA",
        (10, 10)
    )

    draw = ImageDraw.Draw(
        test_image
    )

    for word in words:

        if current:

            test = (
                current +
                " " +
                word
            )

        else:

            test = word

        shaped = shape_arabic(
            test
        )

        bbox = draw.textbbox(
            (0, 0),
            shaped,
            font=font
        )

        text_width = (
            bbox[2] -
            bbox[0]
        )

        if text_width <= max_width:

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

    return [
        shape_arabic(line)
        for line in lines
    ]


# ============================================================
# FIND BEST ARABIC FONT SIZE
# ============================================================

def fit_arabic_text(
    text,
    max_width
):

    for size in range(
        100,
        54,
        -2
    ):

        font = get_font(
            size
        )

        lines = wrap_arabic(
            text,
            font,
            max_width
        )

        if len(lines) <= 4:

            return (
                font,
                lines
            )

    font = get_font(
        54
    )

    lines = wrap_arabic(
        text,
        font,
        max_width
    )

    return (
        font,
        lines
    )


# ============================================================
# SELECT TODAY'S CONTENT
# ============================================================

day_number = int(
    datetime.now().strftime(
        "%Y%m%d"
    )
)

random.seed(
    day_number
)

selected_topics = random.sample(
    TOPICS,
    3
)

selected_ayahs = random.sample(
    QURAN_AYAHS,
    3
)

print()
print(
    "========================================"
)
print(
    "Today's Nature Qur'an Shorts"
)
print(
    "========================================"
)

for i in range(3):

    print(
        f"Short {i + 1}: "
        f"{selected_topics[i]} "
        f"| Ayah {selected_ayahs[i]}"
    )


# ============================================================
# PEXELS VIDEO SEARCH
# ============================================================

def get_nature_video(
    topic,
    index
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

        "orientation":
        "portrait",

        "size":
        "large",

        "per_page":
        20
    }

    data = request_json(
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
            f"No Pexels videos found "
            f"for: {topic}"
        )

    candidates = []

    # --------------------------------------------------------
    # Prefer portrait HD videos
    # --------------------------------------------------------

    for video in videos:

        for video_file in video.get(
            "video_files",
            []
        ):

            width = (
                video_file.get(
                    "width"
                ) or 0
            )

            height = (
                video_file.get(
                    "height"
                ) or 0
            )

            if (
                height > width
                and width >= 720
            ):

                candidates.append(
                    video_file
                )

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

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
            f"No usable Pexels video "
            f"found for: {topic}"
        )

    # --------------------------------------------------------
    # Highest resolution first
    # --------------------------------------------------------

    candidates.sort(
        key=lambda x:
        (
            (x.get("width") or 0)
            *
            (x.get("height") or 0)
        ),
        reverse=True
    )

    selected = candidates[0]

    video_url = selected["link"]

    output_file = (
        ASSETS /
        f"nature_source_{index}.mp4"
    )

    print()
    print(
        f"Nature video {index}: "
        f"{topic}"
    )

    print(
        "Resolution:",
        selected.get("width"),
        "x",
        selected.get("height")
    )

    download_file(
        video_url,
        output_file
    )

    return output_file


# ============================================================
# GET QURAN DATA
# ============================================================

def get_quran_data(
    global_ayah
):

    # --------------------------------------------------------
    # Arabic
    # --------------------------------------------------------

    arabic_url = (
        "https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/quran-uthmani"
    )

    # --------------------------------------------------------
    # English
    # --------------------------------------------------------

    english_url = (
        "https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/en.sahih"
    )

    # --------------------------------------------------------
    # Recitation
    # --------------------------------------------------------

    audio_url = (
        "https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/ar.alafasy"
    )

    arabic_data = request_json(
        arabic_url
    )["data"]

    english_data = request_json(
        english_url
    )["data"]

    audio_data = request_json(
        audio_url
    )["data"]

    return {

        "arabic":
        arabic_data["text"],

        "english":
        english_data["text"],

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
# CREATE ENGLISH WRAPPED TEXT
# ============================================================

def wrap_english(
    text,
    font,
    max_width
):

    words = text.split()

    lines = []

    current = ""

    test_image = Image.new(
        "RGBA",
        (10, 10)
    )

    draw = ImageDraw.Draw(
        test_image
    )

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
            font=font
        )

        text_width = (
            bbox[2] -
            bbox[0]
        )

        if text_width <= max_width:

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
# CREATE QURAN OVERLAY
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

    # ========================================================
    # MAIN QURAN PANEL
    # ========================================================

    panel_left = 55
    panel_right = WIDTH - 55

    panel_top = 450
    panel_bottom = 1530

    draw.rounded_rectangle(
        (
            panel_left,
            panel_top,
            panel_right,
            panel_bottom
        ),
        radius=38,
        fill=(
            0,
            0,
            0,
            160
        ),
        outline=(
            255,
            255,
            255,
            70
        ),
        width=2
    )

    center_x = WIDTH // 2

    # ========================================================
    # DECORATIVE TOP DESIGN
    # ========================================================

    decoration_y = (
        panel_top +
        65
    )

    draw.line(
        (
            center_x - 190,
            decoration_y,
            center_x - 45,
            decoration_y
        ),
        fill=(
            255,
            255,
            255,
            100
        ),
        width=2
    )

    draw.line(
        (
            center_x + 45,
            decoration_y,
            center_x + 190,
            decoration_y
        ),
        fill=(
            255,
            255,
            255,
            100
        ),
        width=2
    )

    draw.ellipse(
        (
            center_x - 10,
            decoration_y - 10,
            center_x + 10,
            decoration_y + 10
        ),
        outline=(
            255,
            255,
            255,
            140
        ),
        width=2
    )

    # ========================================================
    # SURAH NAME
    # ========================================================

    surah_font = get_font(
        34
    )

    surah_text = (
        quran["surah_arabic"]
    )

    bbox = draw.textbbox(
        (0, 0),
        surah_text,
        font=surah_font
    )

    surah_width = (
        bbox[2] -
        bbox[0]
    )

    draw.text(
        (
            center_x -
            surah_width / 2,
            panel_top + 105
        ),
        surah_text,
        font=surah_font,
        fill=(
            255,
            255,
            255,
            235
        )
    )

    # ========================================================
    # ENGLISH SURAH + VERSE
    # ========================================================

    reference_font = get_font(
        24
    )

    reference_text = (
        f"{quran['surah']}  •  "
        f"Verse {quran['ayah']}"
    )

    bbox = draw.textbbox(
        (0, 0),
        reference_text,
        font=reference_font
    )

    reference_width = (
        bbox[2] -
        bbox[0]
    )

    draw.text(
        (
            center_x -
            reference_width / 2,
            panel_top + 150
        ),
        reference_text,
        font=reference_font,
        fill=(
            255,
            255,
            255,
            175
        )
    )

    # ========================================================
    # ARABIC AYAH
    # ========================================================

    arabic_font, arabic_lines = (
        fit_arabic_text(
            quran["arabic"],
            850
        )
    )

    arabic_y = (
        panel_top +
        215
    )

    line_spacing = 24

    for line in arabic_lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=arabic_font
        )

        text_width = (
            bbox[2] -
            bbox[0]
        )

        text_height = (
            bbox[3] -
            bbox[1]
        )

        draw.text(
            (
                center_x -
                text_width / 2,
                arabic_y
            ),
            line,
            font=arabic_font,
            fill=(
                255,
                255,
                255,
                255
            )
        )

        arabic_y += (
            text_height +
            line_spacing
        )

    # ========================================================
    # SEPARATOR
    # ========================================================

    separator_y = (
        arabic_y +
        18
    )

    draw.line(
        (
            center_x - 210,
            separator_y,
            center_x + 210,
            separator_y
        ),
        fill=(
            255,
            255,
            255,
            75
        ),
        width=2
    )

    # ========================================================
    # ENGLISH TRANSLATION
    # ========================================================

    english_font = get_font(
        29
    )

    english_lines = wrap_english(
        quran["english"],
        english_font,
        820
    )

    english_y = (
        separator_y +
        35
    )

    for line in english_lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=english_font
        )

        text_width = (
            bbox[2] -
            bbox[0]
        )

        text_height = (
            bbox[3] -
            bbox[1]
        )

        draw.text(
            (
                center_x -
                text_width / 2,
                english_y
            ),
            line,
            font=english_font,
            fill=(
                245,
                245,
                245,
                235
            )
        )

        english_y += (
            text_height +
            8
        )

    # ========================================================
    # TRANSLATION CREDIT
    # ========================================================

    credit_font = get_font(
        20
    )

    credit = (
        "Translation: Saheeh International"
    )

    bbox = draw.textbbox(
        (0, 0),
        credit,
        font=credit_font
    )

    credit_width = (
        bbox[2] -
        bbox[0]
    )

    draw.text(
        (
            center_x -
            credit_width / 2,
            panel_bottom - 65
        ),
        credit,
        font=credit_font,
        fill=(
            255,
            255,
            255,
            145
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    image.save(
        output_path
    )

    print(
        f"Qur'an overlay created: "
        f"{output_path}"
    )


# ============================================================
# CREATE VIDEO
# ============================================================

def create_short(
    index,
    topic,
    ayah_number
):

    print()
    print(
        "========================================"
    )

    print(
        f"Creating Short {index}"
    )

    print(
        f"Nature: {topic}"
    )

    # --------------------------------------------------------
    # Nature video
    # --------------------------------------------------------

    video = get_nature_video(
        topic,
        index
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
        f"quran_overlay_{index}.png"
    )

    audio = (
        ASSETS /
        f"quran_audio_{index}.mp3"
    )

    output = (
        OUTPUT /
        f"nature_quran_short_{index}.mp4"
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
    # FFMPEG
    # ========================================================

    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fps=30,"
        "setsar=1"
        "[bg];"

        "[bg][1:v]"
        "overlay=0:0:"
        "shortest=1"
        "[v]"
    )

    command = [

        "ffmpeg",

        "-y",

        # ----------------------------------------------------
        # Nature video
        # ----------------------------------------------------

        "-stream_loop",
        "-1",

        "-i",
        str(video),

        # ----------------------------------------------------
        # Quran overlay
        # ----------------------------------------------------

        "-loop",
        "1",

        "-i",
        str(overlay),

        # ----------------------------------------------------
        # Quran audio
        # ----------------------------------------------------

        "-i",
        str(audio),

        # ----------------------------------------------------
        # Video filter
        # ----------------------------------------------------

        "-filter_complex",
        filter_complex,

        # ----------------------------------------------------
        # Select streams
        # ----------------------------------------------------

        "-map",
        "[v]",

        "-map",
        "2:a:0",

        # ----------------------------------------------------
        # Duration
        # ----------------------------------------------------

        "-t",
        str(VIDEO_SECONDS),

        # ----------------------------------------------------
        # Video encoding
        # ----------------------------------------------------

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        # ----------------------------------------------------
        # Audio encoding
        # ----------------------------------------------------

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "44100",

        # ----------------------------------------------------
        # YouTube compatibility
        # ----------------------------------------------------

        "-movflags",
        "+faststart",

        str(output)
    ]

    print()
    print(
        "Running FFmpeg..."
    )

    # ========================================================
    # RUN FFMPEG WITH FULL ERROR OUTPUT
    # ========================================================

    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:

        print()
        print(
            "========================================"
        )

        print(
            "FFMPEG ERROR"
        )

        print(
            "========================================"
        )

        print(
            result.stderr
        )

        print(
            "========================================"
        )

        raise RuntimeError(
            "FFmpeg failed with exit code "
            f"{result.returncode}"
        )

    # ========================================================
    # CHECK OUTPUT
    # ========================================================

    if not output.exists():

        raise RuntimeError(
            f"Video was not created: "
            f"{output}"
        )

    file_size = (
        output.stat().st_size
    )

    if file_size < 10000:

        raise RuntimeError(
            f"Output video is too small: "
            f"{file_size} bytes"
        )

    print()
    print(
        f"SUCCESS: {output}"
    )

    print(
        f"File size: "
        f"{file_size / 1024 / 1024:.2f} MB"
    )

    return quran


# ============================================================
# CREATE 3 SHORTS
# ============================================================

metadata = []

for index, (
    topic,
    ayah
) in enumerate(
    zip(
        selected_topics,
        selected_ayahs
    ),
    start=1
):

    quran = create_short(
        index,
        topic,
        ayah
    )

    metadata.append(
        {
            "topic":
            topic,

            "surah":
            quran["surah"],

            "surah_arabic":
            quran["surah_arabic"],

            "ayah":
            quran["ayah"],

            "arabic":
            quran["arabic"],

            "english":
            quran["english"]
        }
    )


# ============================================================
# CREATE METADATA FILE
# ============================================================

metadata_file = (
    OUTPUT /
    "metadata.txt"
)

with open(
    metadata_file,
    "w",
    encoding="utf-8"
) as file:

    for i, item in enumerate(
        metadata,
        start=1
    ):

        title = (
            f"{item['topic'].title()} "
            f"and a Beautiful Qur'an Verse "
            f"| Short {i}"
        )

        description = (
            "Reflect on the beauty of Allah's "
            "creation through nature and the "
            "words of the Holy Qur'an.\n\n"

            f"Qur'an: "
            f"{item['surah']} "
            f"Verse {item['ayah']}\n\n"

            f"Translation: "
            f"Saheeh International\n\n"

            "Nature footage: Pexels\n"

            "Qur'an text and recitation "
            "provided through Al Quran Cloud.\n"

            "Recitation: Mishary Rashid Alafasy\n\n"

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

        file.write(
            "\n"
            "==================================================\n"
        )

        file.write(
            f"SHORT {i}\n"
        )

        file.write(
            "==================================================\n\n"
        )

        file.write(
            "TOPIC:\n"
        )

        file.write(
            f"{item['topic']}\n\n"
        )

        file.write(
            "TITLE:\n"
        )

        file.write(
            f"{title}\n\n"
        )

        file.write(
            "SURAH:\n"
        )

        file.write(
            f"{item['surah']} "
            f"({item['surah_arabic']})\n\n"
        )

        file.write(
            "VERSE:\n"
        )

        file.write(
            f"{item['ayah']}\n\n"
        )

        file.write(
            "ARABIC:\n"
        )

        file.write(
            f"{item['arabic']}\n\n"
        )

        file.write(
            "ENGLISH TRANSLATION:\n"
        )

        file.write(
            f"{item['english']}\n\n"
        )

        file.write(
            "DESCRIPTION:\n"
        )

        file.write(
            f"{description}\n\n"
        )


# ============================================================
# FINAL RESULT
# ============================================================

print()
print(
    "=================================================="
)

print(
    "SUCCESS!"
)

print(
    "3 Nature Qur'an Shorts created."
)

print(
    "=================================================="
)

print(
    f"Output folder: {OUTPUT}"
)

print(
    f"Metadata: {metadata_file}"
)

print(
    "=================================================="
)
