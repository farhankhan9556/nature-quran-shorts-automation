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
# HTTP
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
# DOWNLOAD
# ============================================================

def download_file(url, path):

    print(f"Downloading: {url}")

    response = requests.get(
        url,
        timeout=120
    )

    response.raise_for_status()

    with open(path, "wb") as f:
        f.write(response.content)

    print(f"Saved: {path}")


# ============================================================
# FONT
# ============================================================

def font(size):

    return ImageFont.truetype(
        str(ARABIC_FONT),
        size
    )


# ============================================================
# PEXELS
# ============================================================

def get_nature_video(topic, index):

    url = (
        "https://api.pexels.com/v1/videos/search"
    )

    headers = {
        "Authorization": PEXELS_API_KEY
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

    videos = data.get("videos", [])

    if not videos:
        raise RuntimeError(
            f"No videos found for {topic}"
        )

    candidates = []

    for video in videos:

        for vf in video.get(
            "video_files",
            []
        ):

            width = vf.get("width") or 0
            height = vf.get("height") or 0

            if height > width and width >= 720:
                candidates.append(vf)

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
            f"No usable video found for {topic}"
        )

    candidates.sort(
        key=lambda x:
        (x.get("width") or 0) *
        (x.get("height") or 0),
        reverse=True
    )

    selected = candidates[0]

    output = (
        ASSETS /
        f"nature_source_{index}.mp4"
    )

    print()
    print(
        f"Nature {index}: {topic}"
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
# QURAN DATA
# ============================================================

def get_quran_data(global_ayah):

    arabic_url = (
        "https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/quran-uthmani"
    )

    english_url = (
        "https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/en.sahih"
    )

    audio_url = (
        "https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/ar.alafasy"
    )

    arabic = get_json(
        arabic_url
    )["data"]

    english = get_json(
        english_url
    )["data"]

    audio = get_json(
        audio_url
    )["data"]

    return {
        "arabic": arabic["text"],
        "english": english["text"],
        "surah": arabic["surah"]["englishName"],
        "surah_arabic": arabic["surah"]["name"],
        "ayah": arabic["numberInSurah"],
        "audio": audio["audio"]
    }


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_english(
    draw,
    text,
    text_font,
    max_width
):

    words = text.split()

    lines = []
    current = ""

    for word in words:

        test = (
            word
            if not current
            else current + " " + word
        )

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=text_font
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
# ARABIC WRAPPING
#
# IMPORTANT:
# Pillow + libraqm handles Arabic shaping and RTL.
# We DO NOT reverse the Arabic manually.
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

        test = (
            word
            if not current
            else current + " " + word
        )

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=text_font,
            direction="rtl",
            language="ar"
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
# FIND ARABIC SIZE
# ============================================================

def get_arabic_layout(
    draw,
    text,
    max_width
):

    for size in range(
        100,
        55,
        -2
    ):

        f = font(size)

        lines = wrap_arabic(
            draw,
            text,
            f,
            max_width
        )

        if len(lines) <= 4:

            return f, lines

    f = font(56)

    return (
        f,
        wrap_arabic(
            draw,
            text,
            f,
            max_width
        )
    )


# ============================================================
# QURAN OVERLAY
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

    draw = ImageDraw.Draw(image)

    center_x = WIDTH // 2

    # ========================================================
    # MAIN PANEL
    # ========================================================

    panel_left = 55
    panel_right = WIDTH - 55
    panel_top = 420
    panel_bottom = 1535

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
            165
        ),
        outline=(
            255,
            255,
            255,
            70
        ),
        width=2
    )

    # ========================================================
    # TOP DECORATION
    # ========================================================

    decoration_y = (
        panel_top + 60
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
            130
        ),
        width=2
    )

    # ========================================================
    # SURAH ARABIC NAME
    # ========================================================

    surah_font = font(38)

    draw.text(
        (
            center_x,
            panel_top + 108
        ),
        quran["surah_arabic"],
        font=surah_font,
        fill=(
            255,
            255,
            255,
            245
        ),
        anchor="mm",
        direction="rtl",
        language="ar"
    )

    # ========================================================
    # SURAH / VERSE
    # ========================================================

    reference_font = font(24)

    reference = (
        f"{quran['surah']}  •  "
        f"Verse {quran['ayah']}"
    )

    draw.text(
        (
            center_x,
            panel_top + 157
        ),
        reference,
        font=reference_font,
        fill=(
            255,
            255,
            255,
            180
        ),
        anchor="mm"
    )

    # ========================================================
    # ARABIC AYAH
    # ========================================================

    arabic_font, arabic_lines = (
        get_arabic_layout(
            draw,
            quran["arabic"],
            860
        )
    )

    arabic_y = (
        panel_top + 225
    )

    arabic_spacing = 18

    for line in arabic_lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=arabic_font,
            direction="rtl",
            language="ar"
        )

        text_height = (
            bbox[3] - bbox[1]
        )

        draw.text(
            (
                center_x,
                arabic_y
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

        arabic_y += (
            text_height +
            arabic_spacing
        )

    # ========================================================
    # SEPARATOR
    # ========================================================

    separator_y = (
        arabic_y + 22
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
            80
        ),
        width=2
    )

    # ========================================================
    # ENGLISH TRANSLATION
    # ========================================================

    english_font = font(29)

    english_lines = wrap_english(
        draw,
        quran["english"],
        english_font,
        820
    )

    english_y = (
        separator_y + 38
    )

    for line in english_lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=english_font
        )

        text_height = (
            bbox[3] - bbox[1]
        )

        draw.text(
            (
                center_x,
                english_y
            ),
            line,
            font=english_font,
            fill=(
                245,
                245,
                245,
                235
            ),
            anchor="ma"
        )

        english_y += (
            text_height + 7
        )

    # ========================================================
    # TRANSLATION CREDIT
    # ========================================================

    credit_font = font(20)

    credit = (
        "Translation: Saheeh International"
    )

    draw.text(
        (
            center_x,
            panel_bottom - 62
        ),
        credit,
        font=credit_font,
        fill=(
            255,
            255,
            255,
            145
        ),
        anchor="mm"
    )

    # ========================================================
    # SAVE
    # ========================================================

    image.save(
        output_path
    )

    print(
        f"Overlay created: {output_path}"
    )


# ============================================================
# CREATE SHORT
# ============================================================

def create_short(
    index,
    topic,
    ayah_number
):

    print()
    print(
        "=========================================="
    )

    print(
        f"Creating Short {index}"
    )

    print(
        f"Nature: {topic}"
    )

    # --------------------------------------------------------
    # Nature
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
    # FFMPEG FILTER
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
        str(video),

        # Transparent overlay
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

        # Video
        "-map",
        "[v]",

        # Audio
        "-map",
        "2:a:0",

        # Duration
        "-t",
        str(VIDEO_SECONDS),

        # Video encoding
        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        # Audio encoding
        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "44100",

        # YouTube
        "-movflags",
        "+faststart",

        str(output)
    ]

    print()
    print(
        "Running FFmpeg..."
    )

    # ========================================================
    # RUN FFMPEG
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
            f"Video not created: {output}"
        )

    size = (
        output.stat().st_size
    )

    if size < 10000:

        raise RuntimeError(
            "Generated video is too small"
        )

    print()
    print(
        f"SUCCESS: {output}"
    )

    print(
        f"Size: "
        f"{size / 1024 / 1024:.2f} MB"
    )

    return quran


# ============================================================
# DAILY SELECTION
# ============================================================

today = int(
    datetime.now().strftime(
        "%Y%m%d"
    )
)

random.seed(today)

selected_topics = random.sample(
    TOPICS,
    3
)

selected_ayahs = random.sample(
    QURAN_AYAHS,
    3
)


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

    metadata.append(quran)


# ============================================================
# METADATA
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

    for i, (
        topic,
        quran
    ) in enumerate(
        zip(
            selected_topics,
            metadata
        ),
        start=1
    ):

        title = (
            f"{topic.title()} "
            f"and a Beautiful Qur'an Verse "
            f"| Short {i}"
        )

        description = (
            "Reflect on the beauty of Allah's "
            "creation through nature and the "
            "words of the Holy Qur'an.\n\n"

            f"Qur'an: {quran['surah']} "
            f"Verse {quran['ayah']}\n\n"

            "Translation: Saheeh International\n"

            "Recitation: Mishary Rashid Alafasy\n\n"

            "Nature footage: Pexels\n"

            "Qur'an data and recitation: "
            "Al Quran Cloud\n\n"

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
            f"TOPIC:\n{topic}\n\n"
        )

        file.write(
            f"TITLE:\n{title}\n\n"
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
            f"{quran['arabic']}\n\n"
        )

        file.write(
            f"ENGLISH TRANSLATION:\n"
            f"{quran['english']}\n\n"
        )

        file.write(
            f"DESCRIPTION:\n"
            f"{description}\n\n"
        )


# ============================================================
# COMPLETE
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
