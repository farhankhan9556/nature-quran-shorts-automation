import os
import random
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display


# =========================
# SETTINGS
# =========================

WIDTH = 1080
HEIGHT = 1920
VIDEO_SECONDS = 20

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
OUTPUT = BASE / "output"
FONTS = BASE / "fonts"

ASSETS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

ARABIC_FONT = FONTS / "NotoNaskhArabic-Regular.otf"

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

if not PEXELS_API_KEY:
    raise RuntimeError("PEXELS_API_KEY is missing")

if not ARABIC_FONT.exists():
    raise RuntimeError(
        f"Arabic font not found: {ARABIC_FONT}"
    )


# =========================
# NATURE TOPICS
# =========================

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


# =========================
# QURAN AYAHS
# =========================

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


# =========================
# HELPERS
# =========================

def request_json(url, **kwargs):
    response = requests.get(url, timeout=60, **kwargs)
    response.raise_for_status()
    return response.json()


def download_file(url, path):
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    with open(path, "wb") as f:
        f.write(response.content)


def get_font(size):
    return ImageFont.truetype(str(ARABIC_FONT), size)


def shape_arabic(text):
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def wrap_arabic(text, font, max_width):
    """
    Wrap Arabic while keeping proper RTL shaping.
    """

    words = text.split()
    lines = []
    current = ""

    for word in words:

        test = word if not current else current + " " + word
        shaped = shape_arabic(test)

        bbox = ImageDraw.Draw(
            Image.new("RGBA", (10, 10))
        ).textbbox(
            (0, 0),
            shaped,
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

    return [shape_arabic(line) for line in lines]


def fit_arabic_text(text, max_width):
    """
    Find a large Qur'an-style Arabic font size
    that fits inside the panel.
    """

    for size in range(100, 55, -2):

        font = get_font(size)

        lines = wrap_arabic(
            text,
            font,
            max_width
        )

        if len(lines) <= 4:
            return font, lines

    font = get_font(56)

    return font, wrap_arabic(
        text,
        font,
        max_width
    )


# =========================
# SELECT DAILY CONTENT
# =========================

day_number = int(
    __import__("datetime").datetime.now().strftime("%Y%m%d")
)

random.seed(day_number)

selected_topics = random.sample(TOPICS, 3)

selected_ayahs = random.sample(
    QURAN_AYAHS,
    3
)

print("Today's nature topics:")
for topic in selected_topics:
    print("-", topic)


# =========================
# PEXELS VIDEO
# =========================

def get_nature_video(topic, index):

    url = "https://api.pexels.com/v1/videos/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": topic,
        "orientation": "portrait",
        "size": "large",
        "per_page": 20
    }

    data = request_json(
        url,
        headers=headers,
        params=params
    )

    videos = data.get("videos", [])

    if not videos:
        raise RuntimeError(
            f"No Pexels videos found for {topic}"
        )

    # Prefer high-resolution portrait video
    candidates = []

    for video in videos:

        for file in video.get("video_files", []):

            width = file.get("width") or 0
            height = file.get("height") or 0

            if height > width and width >= 720:
                candidates.append(file)

    if not candidates:

        for video in videos:
            candidates.extend(
                video.get("video_files", [])
            )

    if not candidates:
        raise RuntimeError(
            f"No usable video files for {topic}"
        )

    candidates.sort(
        key=lambda x: (
            (x.get("width") or 0) *
            (x.get("height") or 0)
        ),
        reverse=True
    )

    selected = candidates[0]

    video_url = selected["link"]

    output = ASSETS / f"nature_source_{index}.mp4"

    print(
        f"Downloading {topic}: "
        f"{selected.get('width')}x{selected.get('height')}"
    )

    download_file(
        video_url,
        output
    )

    return output


# =========================
# QURAN DATA
# =========================

def get_quran_data(global_ayah):

    arabic_url = (
        f"https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/quran-uthmani"
    )

    english_url = (
        f"https://api.alquran.cloud/v1/ayah/"
        f"{global_ayah}/en.sahih"
    )

    audio_url = (
        f"https://api.alquran.cloud/v1/ayah/"
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
        "arabic": arabic_data["text"],
        "english": english_data["text"],
        "surah": arabic_data["surah"]["englishName"],
        "surah_arabic": arabic_data["surah"]["name"],
        "ayah": arabic_data["numberInSurah"],
        "audio": audio_data["audio"],
    }


# =========================
# QURAN OVERLAY
# =========================

def create_quran_overlay(
    quran,
    output_path
):

    image = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(image)

    # Main elegant panel
    panel_left = 55
    panel_right = WIDTH - 55
    panel_top = 470
    panel_bottom = 1510

    draw.rounded_rectangle(
        (
            panel_left,
            panel_top,
            panel_right,
            panel_bottom
        ),
        radius=35,
        fill=(0, 0, 0, 155),
        outline=(255, 255, 255, 65),
        width=2
    )

    # Decorative top separator
    center_x = WIDTH // 2

    draw.line(
        (
            center_x - 180,
            panel_top + 75,
            center_x - 45,
            panel_top + 75
        ),
        fill=(255, 255, 255, 100),
        width=2
    )

    draw.line(
        (
            center_x + 45,
            panel_top + 75,
            center_x + 180,
            panel_top + 75
        ),
        fill=(255, 255, 255, 100),
        width=2
    )

    draw.ellipse(
        (
            center_x - 10,
            panel_top + 65,
            center_x + 10,
            panel_top + 85
        ),
        outline=(255, 255, 255, 130),
        width=2
    )

    # =========================
    # SURAH REFERENCE
    # =========================

    reference_font = ImageFont.truetype(
        str(ARABIC_FONT),
        31
    )

    reference = (
        f"{quran['surah']}  •  "
        f"Surah {quran['surah']}  •  "
        f"Verse {quran['ayah']}"
    )

    bbox = draw.textbbox(
        (0, 0),
        reference,
        font=reference_font
    )

    ref_width = bbox[2] - bbox[0]

    draw.text(
        (
            center_x - ref_width / 2,
            panel_top + 105
        ),
        reference,
        font=reference_font,
        fill=(255, 255, 255, 210)
    )

    # =========================
    # ARABIC AYAH
    # =========================

    arabic_font, arabic_lines = fit_arabic_text(
        quran["arabic"],
        850
    )

    line_spacing = 22

    arabic_y = panel_top + 175

    for line in arabic_lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=arabic_font
        )

        text_width = bbox[2] - bbox[0]

        draw.text(
            (
                center_x - text_width / 2,
                arabic_y
            ),
            line,
            font=arabic_font,
            fill=(255, 255, 255, 255)
        )

        arabic_y += (
            bbox[3] - bbox[1]
        ) + line_spacing

    # =========================
    # MIDDLE SEPARATOR
    # =========================

    separator_y = arabic_y + 20

    draw.line(
        (
            center_x - 220,
            separator_y,
            center_x + 220,
            separator_y
        ),
        fill=(255, 255, 255, 75),
        width=2
    )

    # =========================
    # ENGLISH TRANSLATION
    # =========================

    english_font = ImageFont.truetype(
        str(ARABIC_FONT),
        30
    )

    english = quran["english"]

    # Simple English wrapping
    words = english.split()

    english_lines = []
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
            font=english_font
        )

        if bbox[2] - bbox[0] <= 820:
            current = test
        else:
            if current:
                english_lines.append(current)

            current = word

    if current:
        english_lines.append(current)

    english_y = separator_y + 40

    for line in english_lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=english_font
        )

        text_width = bbox[2] - bbox[0]

        draw.text(
            (
                center_x - text_width / 2,
                english_y
            ),
            line,
            font=english_font,
            fill=(245, 245, 245, 235)
        )

        english_y += 44

    # =========================
    # TRANSLATION CREDIT
    # =========================

    credit_font = ImageFont.truetype(
        str(ARABIC_FONT),
        21
    )

    credit = "Saheeh International"

    bbox = draw.textbbox(
        (0, 0),
        credit,
        font=credit_font
    )

    draw.text(
        (
            center_x -
            (bbox[2] - bbox[0]) / 2,
            panel_bottom - 60
        ),
        credit,
        font=credit_font,
        fill=(255, 255, 255, 150)
    )

    image.save(
        output_path
    )


# =========================
# CREATE SHORT
# =========================

def create_short(
    index,
    topic,
    ayah_number
):

    print()
    print(
        f"Creating Short {index}: "
        f"{topic}"
    )

    video = get_nature_video(
        topic,
        index
    )

    quran = get_quran_data(
        ayah_number
    )

    print(
        f"Qur'an: "
        f"{quran['surah']} "
        f"Verse {quran['ayah']}"
    )

    overlay = ASSETS / (
        f"quran_overlay_{index}.png"
    )

    audio = ASSETS / (
        f"quran_audio_{index}.mp3"
    )

    output = OUTPUT / (
        f"nature_quran_short_{index}.mp4"
    )

    # Create Qur'an layout
    create_quran_overlay(
        quran,
        overlay
    )

    # Download recitation
    download_file(
        quran["audio"],
        audio
    )

    # =========================
    # FFMPEG
    # =========================

    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "setsar=1,"
        "fps=30,"
        "format=yuv420p"
        "[bg];"

        "[bg][1:v]"
        "overlay=0:0:"
        "format=yuv420p"
        "[v]"
    )

    command = [
        "ffmpeg",
        "-y",

        "-stream_loop",
        "-1",
        "-i",
        str(video),

        "-loop",
        "1",
        "-i",
        str(overlay),

        "-i",
        str(audio),

        "-filter_complex",
        filter_complex,

        "-map",
        "[v]",

        "-map",
        "2:a",

        "-t",
        str(VIDEO_SECONDS),

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-shortest",

        "-movflags",
        "+faststart",

        str(output)
    ]

    subprocess.run(
        command,
        check=True
    )

    print(
        f"Created: {output}"
    )

    return quran


# =========================
# CREATE 3 SHORTS
# =========================

metadata = []

for index, (topic, ayah) in enumerate(
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
            "topic": topic,
            "surah": quran["surah"],
            "ayah": quran["ayah"],
            "english": quran["english"]
        }
    )


# =========================
# METADATA
# =========================

metadata_file = OUTPUT / "metadata.txt"

with open(
    metadata_file,
    "w",
    encoding="utf-8"
) as f:

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
            f"Reflect on the beauty of Allah's creation "
            f"through {item['topic']} and the words of "
            f"the Holy Qur'an.\n\n"
            f"Qur'an: {item['surah']} "
            f"Verse {item['ayah']}\n"
            f"Translation: Saheeh International\n\n"
            f"Nature footage: Pexels\n"
            f"Qur'an data and recitation: Al Quran Cloud\n"
            f"Recitation: Mishary Rashid Alafasy\n\n"
            f"#Quran #QuranRecitation #Islam #Allah "
            f"#IslamicShorts #Nature #NatureShorts "
            f"#QuranVerses #Reminder #Muslim"
        )

        f.write(
            f"SHORT {i}\n"
            f"====================\n"
            f"Title:\n{title}\n\n"
            f"Description:\n{description}\n\n"
        )


print()
print("================================")
print("3 Nature Qur'an Shorts created")
print("================================")
