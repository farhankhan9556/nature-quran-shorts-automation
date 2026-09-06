import os
import re
import random
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# NATURE QURAN SHORTS - COMPLETE GENERATOR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
FONT_DIR = BASE_DIR / "fonts"

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

ARABIC_FONT = FONT_DIR / "NotoNaskhArabic-Regular.otf"
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

ARABIC_FONT_SIZE = 82
ENGLISH_FONT_SIZE = 40
REFERENCE_FONT_SIZE = 30

NATURE_AUDIO_VOLUME = 0.06
SHORT_COUNT = 3

WORDS_MIN = 3
WORDS_MAX = 4

# Only short surahs are used so the complete recitation fits in a YouTube Short.
SHORT_SURAHS = set(range(103, 109)) | set(range(110, 115))
MAX_SHORT_DURATION = 59.5

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

WIKIMEDIA_HEADERS = {
    "User-Agent": (
        "NatureQuranShortsBot/1.0 "
        "(https://github.com/farhankhan9556/"
        "nature-quran-shorts-automation) "
        "requests"
    ),
    "Accept": "application/json",
}

TOPICS = [
    "mountain sunrise",
    "ocean waves",
    "waterfall nature",
    "forest sunlight",
    "desert sunset",
    "snow mountain",
    "beautiful lake",
    "ocean sunset",
    "rain forest",
    "night sky stars",
    "river nature",
    "dramatic cliffs",
    "misty mountains",
    "peaceful ocean",
    "green valley",
    "water flowing nature",
    "calm sea",
    "mountain landscape",
    "forest waterfall",
    "sunrise landscape",
    "tropical beach",
    "clouds over mountains",
    "green forest",
    "peaceful river",
]

# These files are known CC0/public-domain ambience examples on Wikimedia.
# The generator also verifies the downloaded file is valid.
NATURE_SOUNDS = [
    {
        "name": "Ocean Waves on a Tropical Beach",
        "url": (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/"
            "Ocean_Waves_on_a_Tropical_Beach.ogg"
        ),
    },
    {
        "name": "Birds Chirping in a Garden",
        "url": (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/"
            "Birds_chirping_in_a_garden.ogg"
        ),
    },
    {
        "name": "Birds in Forest",
        "url": (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/Birds_forest.ogg"
        ),
    },
    {
        "name": "Birds Singing in Garden",
        "url": (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/"
            "Birds_singing_in_garden.ogg"
        ),
    },
]


# ============================================================
# BASIC HELPERS
# ============================================================

def run_cmd(command):
    print("RUN:", " ".join(str(x) for x in command))
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}"
        )
    return result.stdout.strip()


def request_json(url, params=None, timeout=60, headers=None):
    request_headers = dict(WIKIMEDIA_HEADERS)
    if headers:
        request_headers.update(headers)

    response = requests.get(
        url,
        params=params,
        timeout=timeout,
        headers=request_headers,
    )

    if response.status_code == 403:
        raise RuntimeError(
            "Wikimedia returned HTTP 403. "
            "The API request was blocked. "
            "The identifying User-Agent is already configured; "
            "please retry the workflow."
        )

    response.raise_for_status()
    return response.json()


def download_file(url, destination, headers=None):
    print(f"Downloading: {url}")

    request_headers = {
        "User-Agent": WIKIMEDIA_HEADERS["User-Agent"]
    }

    if headers:
        request_headers.update(headers)

    response = requests.get(
        url,
        timeout=180,
        headers=request_headers,
        allow_redirects=True,
    )
    response.raise_for_status()

    destination.write_bytes(response.content)

    if destination.stat().st_size < 1000:
        raise RuntimeError(
            f"Downloaded file is unexpectedly small: {destination}"
        )

    return destination


def get_duration(file_path):
    value = run_cmd([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ])
    return float(value)


def clean_filename(text):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


# ============================================================
# QURAN DATA
# ============================================================

def get_surah_data(surah_number):
    arabic_url = (
        f"https://api.alquran.cloud/v1/surah/"
        f"{surah_number}/quran-uthmani"
    )
    english_url = (
        f"https://api.alquran.cloud/v1/surah/"
        f"{surah_number}/en.pickthall"
    )

    arabic_response = requests.get(
        arabic_url,
        timeout=45,
    )
    arabic_response.raise_for_status()

    english_response = requests.get(
        english_url,
        timeout=45,
    )
    english_response.raise_for_status()

    arabic_data = arabic_response.json()["data"]
    english_data = english_response.json()["data"]

    arabic_ayahs = arabic_data["ayahs"]
    english_ayahs = english_data["ayahs"]

    if len(arabic_ayahs) != len(english_ayahs):
        raise RuntimeError(
            "Arabic and English ayah counts do not match."
        )

    ayahs = []

    for ar, en in zip(arabic_ayahs, english_ayahs):
        ayahs.append({
            "number": ar["numberInSurah"],
            "arabic": ar["text"],
            "english": en["text"],
        })

    return {
        "number": arabic_data["number"],
        "name_arabic": arabic_data["name"],
        "name_english": arabic_data["englishName"],
        "ayah_count": len(ayahs),
        "ayahs": ayahs,
    }


# ============================================================
# WIKIMEDIA CC0 RECITATIONS
# ============================================================

def get_category_files():
    params = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": (
            "Category:Recitations of the Qur'an by Aaqib Azeez"
        ),
        "cmlimit": "500",
        "cmtype": "file",
    }

    data = request_json(
        WIKIMEDIA_API,
        params=params,
        timeout=60,
    )

    return data.get("query", {}).get("categorymembers", [])


def parse_surah_number_from_title(title):
    match = re.search(
        r"File:Chapter\s+(\d+),",
        title,
        re.IGNORECASE,
    )
    if not match:
        return None
    return int(match.group(1))


def is_murattal_title(title):
    lower = title.lower()
    return (
        "murattal" in lower
        and lower.endswith(".mp3")
    )


def get_file_info(title):
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
    }

    data = request_json(
        WIKIMEDIA_API,
        params=params,
        timeout=60,
    )

    pages = data.get("query", {}).get("pages", {})

    for page in pages.values():
        imageinfo = page.get("imageinfo")
        if not imageinfo:
            continue

        info = imageinfo[0]
        metadata = info.get("extmetadata", {})

        license_name = (
            metadata.get("LicenseShortName", {}).get("value", "")
        )
        license_url = (
            metadata.get("LicenseUrl", {}).get("value", "")
        )

        allowed = (
            "CC0" in license_name.upper()
            or "CC ZERO" in license_name.upper()
            or "PUBLIC DOMAIN" in license_name.upper()
        )

        if not allowed:
            return None

        return {
            "title": title,
            "url": info["url"],
            "license": license_name,
            "license_url": license_url,
        }

    return None


def discover_cc0_short_surahs():
    print("Discovering CC0/public-domain short-surah recordings...")

    files = get_category_files()
    candidates = []

    for item in files:
        title = item.get("title", "")
        surah_number = parse_surah_number_from_title(title)

        if surah_number not in SHORT_SURAHS:
            continue

        if not is_murattal_title(title):
            continue

        print(f"Checking license: {title}")

        info = get_file_info(title)

        if not info:
            print("  Not explicitly CC0/Public Domain. Skipped.")
            continue

        print(
            f"  Accepted: {info['license']}"
        )

        info["surah_number"] = surah_number
        candidates.append(info)

    # Remove duplicate recordings for the same surah if several variants exist.
    unique = {}
    for item in candidates:
        number = item["surah_number"]
        if number not in unique:
            unique[number] = item

    result = list(unique.values())

    print(
        f"Found {len(result)} usable CC0 short-surah recordings."
    )

    if len(result) < SHORT_COUNT:
        raise RuntimeError(
            "Not enough CC0/public-domain short-surah recordings "
            f"available. Found {len(result)}, need {SHORT_COUNT}."
        )

    return result


# ============================================================
# NATURE VIDEO FROM PEXELS
# ============================================================

def search_pexels_video(topic):
    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY is missing."
        )

    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers={
            "Authorization": PEXELS_API_KEY,
        },
        params={
            "query": topic,
            "orientation": "portrait",
            "size": "large",
            "per_page": 15,
        },
        timeout=60,
    )
    response.raise_for_status()

    videos = response.json().get("videos", [])

    if not videos:
        raise RuntimeError(
            f"No Pexels video found for: {topic}"
        )

    usable = []

    for video in videos:
        for video_file in video.get("video_files", []):
            link = video_file.get("link")
            width = video_file.get("width") or 0
            height = video_file.get("height") or 0

            if not link:
                continue

            # Prefer vertical HD.
            if height >= width and height >= 1280:
                usable.append({
                    "url": link,
                    "width": width,
                    "height": height,
                })

    if not usable:
        for video in videos:
            for video_file in video.get("video_files", []):
                link = video_file.get("link")
                if link:
                    usable.append({
                        "url": link,
                        "width": video_file.get("width") or 1080,
                        "height": video_file.get("height") or 1920,
                    })

    if not usable:
        raise RuntimeError(
            f"No usable Pexels video found for: {topic}"
        )

    return random.choice(usable)


def download_nature_clip(topic, destination):
    selected = search_pexels_video(topic)

    download_file(
        selected["url"],
        destination,
        headers={
            "User-Agent": WIKIMEDIA_HEADERS["User-Agent"]
        },
    )


# ============================================================
# NATURE BACKGROUND
# ============================================================

def create_background_video(
    clip_files,
    duration,
    output_file,
):
    count = len(clip_files)
    segment_duration = duration / count

    inputs = []
    filters = []

    for i, clip in enumerate(clip_files):
        inputs.extend([
            "-stream_loop", "-1",
            "-i", str(clip),
        ])

        filters.append(
            f"[{i}:v]"
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            f"force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"setsar=1,"
            f"fps={VIDEO_FPS},"
            f"trim=duration={segment_duration},"
            f"setpts=PTS-STARTPTS"
            f"[v{i}]"
        )

    concat_inputs = "".join(
        f"[v{i}]" for i in range(count)
    )

    filters.append(
        f"{concat_inputs}"
        f"concat=n={count}:v=1:a=0,"
        f"trim=duration={duration},"
        f"setpts=PTS-STARTPTS,"
        f"eq=brightness=-0.05:saturation=0.88,"
        f"vignette[v]"
    )

    filter_complex = ";".join(filters)

    run_cmd([
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-t", str(duration),
        "-an",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        str(output_file),
    ])


# ============================================================
# TEXT HELPERS
# ============================================================

def get_english_font():
    candidates = [
        FONT_DIR / "NotoSans-Regular.ttf",
        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),
    ]

    for font in candidates:
        if font.exists():
            return str(font)

    raise RuntimeError(
        "No English font found."
    )


def split_arabic_words(text):
    punctuation = "،؛؟!.,:;!?()[]{}"
    return [
        word.strip(punctuation)
        for word in text.split()
        if word.strip(punctuation)
    ]


def split_english_words(text):
    return [
        word.strip(".,!?;:()[]{}\"'")
        for word in text.split()
        if word.strip()
    ]


def make_3_4_word_groups(words):
    if len(words) <= WORDS_MAX:
        return [words]

    groups = []
    index = 0
    remaining = len(words)

    while remaining:
        if remaining <= WORDS_MAX:
            size = remaining
        elif remaining == 5:
            size = 3
        elif remaining % 4 == 1:
            size = 3
        else:
            size = 4

        groups.append(words[index:index + size])
        index += size
        remaining -= size

    return groups


def proportional_translation_groups(
    arabic_groups,
    english_text,
):
    english = split_english_words(english_text)

    if not english:
        return [""] * len(arabic_groups)

    if len(arabic_groups) == 1:
        return [english_text]

    total_arabic = sum(
        len(group) for group in arabic_groups
    )

    result = []
    start = 0

    for i, group in enumerate(arabic_groups):
        if i == len(arabic_groups) - 1:
            end = len(english)
        else:
            target = round(
                len(english)
                * len(group)
                / total_arabic
            )
            end = max(
                start + 1,
                min(len(english), start + target),
            )

        part = " ".join(english[start:end])

        if not part:
            part = english[-1]

        result.append(part)
        start = end

    return result


def build_word_groups_for_surah(surah):
    all_groups = []

    for ayah in surah["ayahs"]:
        arabic_words = split_arabic_words(
            ayah["arabic"]
        )

        english_words = split_english_words(
            ayah["english"]
        )

        if not arabic_words:
            continue

        arabic_groups = make_3_4_word_groups(
            arabic_words
        )

        translation_groups = (
            proportional_translation_groups(
                arabic_groups,
                ayah["english"],
            )
        )

        for arabic_group, english_group in zip(
            arabic_groups,
            translation_groups,
        ):
            all_groups.append({
                "arabic": " ".join(arabic_group),
                "english": english_group,
                "ayah": ayah["number"],
                "word_count": len(arabic_group),
            })

    return all_groups


# ============================================================
# TEXT PNG
# ============================================================

def wrap_english(text, font, max_width):
    words = text.split()

    if not words:
        return [""]

    lines = []
    current = ""

    dummy = Image.new(
        "RGBA",
        (10, 10),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(dummy)

    for word in words:
        test = (
            word if not current
            else current + " " + word
        )

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=font,
        )

        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def create_overlay_png(
    arabic,
    english,
    reference,
    output_file,
):
    image = Image.new(
        "RGBA",
        (VIDEO_WIDTH, VIDEO_HEIGHT),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(image)

    arabic_font = ImageFont.truetype(
        str(ARABIC_FONT),
        ARABIC_FONT_SIZE,
    )

    english_font = ImageFont.truetype(
        get_english_font(),
        ENGLISH_FONT_SIZE,
    )

    reference_font = ImageFont.truetype(
        get_english_font(),
        REFERENCE_FONT_SIZE,
    )

    english_lines = wrap_english(
        english,
        english_font,
        VIDEO_WIDTH - 180,
    )

    arabic_box = draw.textbbox(
        (0, 0),
        arabic,
        font=arabic_font,
        direction="rtl",
        language="ar",
    )

    arabic_height = (
        arabic_box[3] - arabic_box[1]
    )

    english_height = (
        english_font.getbbox("Ag")[3]
        - english_font.getbbox("Ag")[1]
    )

    reference_height = (
        reference_font.getbbox("Ag")[3]
        - reference_font.getbbox("Ag")[1]
    )

    english_block_height = (
        len(english_lines) * english_height
        + max(0, len(english_lines) - 1) * 8
    )

    total_height = (
        arabic_height
        + 24
        + english_block_height
        + 22
        + reference_height
    )

    center_x = VIDEO_WIDTH // 2
    center_y = int(VIDEO_HEIGHT * 0.64)

    arabic_y = center_y - total_height // 2
    english_y = (
        arabic_y
        + arabic_height
        + 24
    )

    # Arabic shadow
    draw.text(
        (center_x + 3, arabic_y + 4),
        arabic,
        font=arabic_font,
        fill=(0, 0, 0, 210),
        anchor="ma",
        direction="rtl",
        language="ar",
    )

    # Arabic
    draw.text(
        (center_x, arabic_y),
        arabic,
        font=arabic_font,
        fill=(255, 255, 255, 255),
        anchor="ma",
        direction="rtl",
        language="ar",
    )

    current_y = english_y

    for line in english_lines:
        draw.text(
            (center_x + 2, current_y + 3),
            line,
            font=english_font,
            fill=(0, 0, 0, 185),
            anchor="ma",
        )

        draw.text(
            (center_x, current_y),
            line,
            font=english_font,
            fill=(245, 245, 245, 255),
            anchor="ma",
        )

        current_y += english_height + 8

    reference_y = (
        current_y + 22
    )

    draw.text(
        (center_x, reference_y),
        reference,
        font=reference_font,
        fill=(220, 220, 220, 230),
        anchor="ma",
    )

    image.save(output_file)


# ============================================================
# OVERLAY TIMELINE
# ============================================================

def create_overlay_timeline(
    surah,
    duration,
    overlay_dir,
):
    groups = build_word_groups_for_surah(
        surah
    )

    if not groups:
        raise RuntimeError(
            "No Quran word groups were created."
        )

    total_words = sum(
        group["word_count"]
        for group in groups
    )

    reference_name = surah["name_english"]

    timeline = []
    current = 0.0

    for index, group in enumerate(groups):
        if index == len(groups) - 1:
            end = duration
        else:
            share = (
                group["word_count"]
                / total_words
            )
            end = current + duration * share

        reference = (
            f"{reference_name} "
            f"• Ayah {group['ayah']}"
        )

        image_file = (
            overlay_dir
            / f"overlay_{index:04d}.png"
        )

        create_overlay_png(
            group["arabic"],
            group["english"],
            reference,
            image_file,
        )

        timeline.append({
            "start": current,
            "end": end,
            "image": image_file,
        })

        current = end

    return timeline


# ============================================================
# FINAL VIDEO
# ============================================================

def create_final_video(
    background,
    recitation,
    nature_sound,
    overlays,
    duration,
    output_file,
):
    # Input 0 = background
    # Input 1 = Quran recitation
    # Input 2 = nature ambience
    # Input 3+ = overlay PNGs

    overlay_inputs = []
    filter_parts = []

    previous = "[0:v]"

    for i, overlay in enumerate(overlays):
        input_index = i + 3
        next_label = f"[v{i}]"

        overlay_inputs.extend([
            "-loop", "1",
            "-i", str(overlay["image"]),
        ])

        filter_parts.append(
            f"{previous}"
            f"[{input_index}:v]"
            f"overlay=0:0:"
            f"enable='between(t,"
            f"{overlay['start']:.3f},"
            f"{overlay['end']:.3f})'"
            f"{next_label}"
        )

        previous = next_label

    filter_parts.append(
        "[1:a]"
        "aresample=48000,"
        "volume=1.0"
        "[quran]"
    )

    filter_parts.append(
        "[2:a]"
        "aresample=48000,"
        f"volume={NATURE_AUDIO_VOLUME},"
        f"atrim=duration={duration},"
        "asetpts=PTS-STARTPTS"
        "[nature]"
    )

    filter_parts.append(
        "[quran][nature]"
        "amix=inputs=2:"
        "duration=first:"
        "dropout_transition=0"
        "[audio]"
    )

    filter_complex = ";".join(filter_parts)

    run_cmd([
        "ffmpeg",
        "-y",
        "-i", str(background),
        "-i", str(recitation),
        "-stream_loop", "-1",
        "-i", str(nature_sound),
        *overlay_inputs,
        "-filter_complex", filter_complex,
        "-map", previous,
        "-map", "[audio]",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_file),
    ])


# ============================================================
# METADATA
# ============================================================

def create_metadata(
    index,
    surah,
    recording,
    nature_sound,
    nature_topics,
):
    title = (
        f"Surah {surah['name_english']} "
        f"— Quran Recitation & English Meaning"
    )

    description = f"""Listen, reflect, and remember.

Surah {surah['name_english']} ({surah['number']})

Arabic Qur'an text:
Tanzil Quran Text
License: CC BY 3.0
https://tanzil.net

English translation:
Marmaduke Pickthall (1930)
Public-domain translation.

Qur'an recitation:
{recording['title']}
License: {recording['license']}
Wikimedia Commons:
https://commons.wikimedia.org/wiki/{recording['title'].replace(' ', '_')}

Nature background:
Pexels.

Nature ambience:
{nature_sound['name']}
Wikimedia Commons CC0/public-domain source.

Nature scenes:
{", ".join(nature_topics)}

The Arabic words and English meaning are displayed in short
3–4-word groups throughout the recitation.

#Quran #QuranShorts #QuranRecitation #Islam #IslamicReminder #Allah #Muslim #IslamicShorts #Ayah #Nature
"""

    metadata_file = (
        OUTPUT_DIR
        / f"metadata_{index}.txt"
    )

    metadata_file.write_text(
        f"TITLE:\n{title}\n\n"
        f"DESCRIPTION:\n{description}\n",
        encoding="utf-8",
    )


# ============================================================
# CREATE ONE SHORT
# ============================================================

def create_short(
    index,
    candidate,
):
    print()
    print("=" * 70)
    print(f"CREATING SHORT {index}")
    print("=" * 70)

    surah_number = candidate["surah_number"]

    print(
        f"Loading Surah {surah_number}..."
    )

    surah = get_surah_data(
        surah_number
    )

    print(
        f"Surah: {surah['name_english']} "
        f"({surah['number']})"
    )

    # --------------------------------------------------------
    # Download CC0 full-surah recitation.
    # --------------------------------------------------------

    recitation = (
        TEMP_DIR
        / f"recitation_{index}.mp3"
    )

    download_file(
        candidate["url"],
        recitation,
        headers=WIKIMEDIA_HEADERS,
    )

    duration = get_duration(
        recitation
    )

    print(
        f"Recitation duration: "
        f"{duration:.2f} seconds"
    )

    if duration > MAX_SHORT_DURATION:
        raise RuntimeError(
            f"Selected surah is {duration:.2f}s, "
            "which is too long for this Short."
        )

    # --------------------------------------------------------
    # Nature ambience.
    # --------------------------------------------------------

    nature_sound = random.choice(
        NATURE_SOUNDS
    )

    nature_audio = (
        TEMP_DIR
        / f"nature_sound_{index}.ogg"
    )

    download_file(
        nature_sound["url"],
        nature_audio,
        headers=WIKIMEDIA_HEADERS,
    )

    # --------------------------------------------------------
    # Nature video clips.
    # --------------------------------------------------------

    clip_count = (
        2 if duration <= 30 else 3
    )

    nature_topics = random.sample(
        TOPICS,
        clip_count,
    )

    clip_files = []

    for clip_number, topic in enumerate(
        nature_topics,
        start=1,
    ):
        clip_file = (
            TEMP_DIR
            / f"nature_{index}_{clip_number}.mp4"
        )

        download_nature_clip(
            topic,
            clip_file,
        )

        clip_files.append(
            clip_file
        )

    # --------------------------------------------------------
    # Background.
    # --------------------------------------------------------

    background = (
        TEMP_DIR
        / f"background_{index}.mp4"
    )

    create_background_video(
        clip_files,
        duration,
        background,
    )

    # --------------------------------------------------------
    # Arabic + English word overlays.
    #
    # Timing is proportional to Arabic word count because the
    # CC0 recording does not provide usable word-level timestamps.
    # This removes the TimedText dependency that caused the
    # previous workflow to fail.
    # --------------------------------------------------------

    overlay_dir = (
        TEMP_DIR
        / f"overlays_{index}"
    )

    overlay_dir.mkdir(
        exist_ok=True
    )

    overlays = create_overlay_timeline(
        surah,
        duration,
        overlay_dir,
    )

    # --------------------------------------------------------
    # Final video.
    # --------------------------------------------------------

    output_file = (
        OUTPUT_DIR
        / f"nature_quran_short_{index}.mp4"
    )

    create_final_video(
        background,
        recitation,
        nature_audio,
        overlays,
        duration,
        output_file,
    )

    # --------------------------------------------------------
    # Metadata.
    # --------------------------------------------------------

    create_metadata(
        index,
        surah,
        candidate,
        nature_sound,
        nature_topics,
    )

    print(
        f"SUCCESS: {output_file}"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("NATURE QURAN SHORTS GENERATOR")
    print("CC0 RECITATION + ENGLISH TRANSLATION + NATURE")
    print("=" * 70)

    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY GitHub Secret is missing."
        )

    if not ARABIC_FONT.exists():
        raise RuntimeError(
            "Noto Naskh Arabic font is missing: "
            f"{ARABIC_FONT}"
        )

    # Discover CC0 recordings.
    candidates = (
        discover_cc0_short_surahs()
    )

    # Prefer 3 different surahs.
    selected = random.sample(
        candidates,
        SHORT_COUNT,
    )

    print()
    print("Selected surahs:")

    for candidate in selected:
        print(
            f"- {candidate['surah_number']}: "
            f"{candidate['title']}"
        )

    # Create all three.
    for index, candidate in enumerate(
        selected,
        start=1,
    ):
        create_short(
            index,
            candidate,
        )

    print()
    print("=" * 70)
    print("ALL 3 NATURE QURAN SHORTS CREATED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
