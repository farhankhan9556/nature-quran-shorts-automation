import os
import re
import random
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# SETTINGS
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

ARABIC_FONT_SIZE = 86
ENGLISH_FONT_SIZE = 42
REFERENCE_FONT_SIZE = 32

NATURE_AUDIO_VOLUME = 0.08
SHORT_COUNT = 3

WORDS_PER_SCREEN_MIN = 3
WORDS_PER_SCREEN_MAX = 4

# Wikimedia requires an identifying User-Agent.
WIKIMEDIA_HEADERS = {
    "User-Agent": (
        "NatureQuranShortsBot/1.0 "
        "(https://github.com/farhankhan9556/"
        "nature-quran-shorts-automation) "
        "requests"
    ),
    "Accept": "application/json",
}


# ============================================================
# NATURE TOPICS
# ============================================================

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
    "beautiful nature",
]


# ============================================================
# CC0 / PUBLIC-DOMAIN NATURE SOUNDS
# ============================================================

NATURE_SOUNDS = [
    {
        "name": "Ocean Waves",
        "url": (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/"
            "Ocean_Waves_on_a_Tropical_Beach.ogg"
        ),
    },
    {
        "name": "Birds in Garden",
        "url": (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/"
            "Birds_chirping_in_a_garden.ogg"
        ),
    },
    {
        "name": "Forest Birds",
        "url": (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/Birds_forest.ogg"
        ),
    },
    {
        "name": "Birds Singing",
        "url": (
            "https://commons.wikimedia.org/wiki/"
            "Special:Redirect/file/"
            "Birds_singing_in_garden.ogg"
        ),
    },
]


# ============================================================
# SURAH NAME MAP
# ============================================================

SURAH_NAME_MAP = {
    "Baqara": 2, "Baqarah": 2, "Imran": 3, "Nisa": 4,
    "An-Nisa": 4, "Maida": 5, "Anam": 6, "Araf": 7,
    "Anfal": 8, "Tawbah": 9, "Yunus": 10, "Hud": 11,
    "Yusuf": 12, "Ibrahim": 14, "Kahf": 18, "Maryam": 19,
    "Taha": 20, "Anbiya": 21, "Hajj": 22, "Muminun": 23,
    "Furqan": 25, "Shuara": 26, "Naml": 27, "Qasas": 28,
    "Ankabut": 29, "Rum": 30, "Luqman": 31, "Sajda": 32,
    "Ahzab": 33, "Saba": 34, "Fatir": 35, "Yasin": 36,
    "Saffat": 37, "Sad": 38, "Zumar": 39, "Ghafir": 40,
    "Fussilat": 41, "Shura": 42, "Zukhruf": 43, "Dukhan": 44,
    "Jathiya": 45, "Ahqaf": 46, "Muhammad": 47, "Fath": 48,
    "Hujurat": 49, "Qaf": 50, "Dhariyat": 51, "Najm": 53,
    "Rahman": 55, "Waqia": 56, "Hadid": 57, "Mujadila": 58,
    "Hashr": 59, "Mumtahina": 60, "Saff": 61, "Jumua": 62,
    "Munafiqun": 63, "Taghabun": 64, "Talaq": 65, "Tahrim": 66,
    "Mulk": 67, "Qalam": 68, "Haqqah": 69, "Maarij": 70,
    "Nuh": 71, "Jinn": 72, "Muzzammil": 73, "Muddaththir": 74,
    "Qiyamah": 75, "Insan": 76, "Mursalat": 77, "Naba": 78,
    "Naziat": 79, "Abasa": 80, "Takwir": 81, "Infitar": 82,
    "Mutaffifin": 83, "Inshiqaq": 84, "Buruj": 85, "Tariq": 86,
    "Ala": 87, "Ghashiyah": 88, "Fajr": 89, "Balad": 90,
    "Shams": 91, "Layl": 92, "Duha": 93, "Sharh": 94,
    "Tin": 95, "Alaq": 96, "Qadr": 97, "Bayyinah": 98,
    "Zalzalah": 99, "Adiyat": 100, "Qariah": 101, "Takathur": 102,
    "Asr": 103, "Humazah": 104, "Fil": 105, "Quraysh": 106,
    "Maun": 107, "Kawthar": 108, "Kafirun": 109, "Nasr": 110,
    "Masad": 111, "Ikhlas": 112, "Falaq": 113, "Nas": 114,
}


# ============================================================
# HELPERS
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


def download_file(url, destination, headers=None):
    print(f"Downloading: {url}")

    request_headers = {
        "User-Agent": (
            "NatureQuranShortsBot/1.0 "
            "(https://github.com/farhankhan9556/"
            "nature-quran-shorts-automation)"
        )
    }
    if headers:
        request_headers.update(headers)

    response = requests.get(
        url,
        timeout=120,
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
    output = run_cmd([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ])
    return float(output)


def request_json(url, params=None, timeout=60, headers=None):
    response = requests.get(
        url,
        params=params,
        timeout=timeout,
        headers=headers or {},
    )

    if response.status_code == 403:
        raise RuntimeError(
            "Wikimedia returned HTTP 403. "
            "The request was blocked. Check the identifying "
            "Wikimedia User-Agent in this file."
        )

    response.raise_for_status()
    return response.json()


# ============================================================
# QURAN TEXT + ENGLISH TRANSLATION
# ============================================================

def get_quran_data(surah_number, ayah_number):
    identifier = f"{surah_number}:{ayah_number}"

    arabic_url = (
        f"https://api.alquran.cloud/v1/ayah/"
        f"{identifier}/quran-uthmani"
    )
    english_url = (
        f"https://api.alquran.cloud/v1/ayah/"
        f"{identifier}/en.pickthall"
    )

    arabic_response = requests.get(
        arabic_url, timeout=30
    )
    arabic_response.raise_for_status()

    english_response = requests.get(
        english_url, timeout=30
    )
    english_response.raise_for_status()

    arabic_data = arabic_response.json()["data"]
    english_data = english_response.json()["data"]

    return {
        "arabic": arabic_data["text"],
        "english": english_data["text"],
        "surah_number": arabic_data["surah"]["number"],
        "surah_name": arabic_data["surah"]["englishName"],
        "ayah_number": arabic_data["numberInSurah"],
        "global_number": arabic_data["number"],
    }


# ============================================================
# WIKIMEDIA COMMONS - CC0 QURAN RECITATION
# ============================================================

def commons_category_files():
    api_url = "https://commons.wikimedia.org/w/api.php"

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
        api_url,
        params=params,
        timeout=60,
        headers=WIKIMEDIA_HEADERS,
    )

    return data.get("query", {}).get("categorymembers", [])


def parse_verse_filename(title):
    clean = title.replace("File:", "")

    match = re.search(
        r"Verse\s+(\d+),\s+([A-Za-z-]+)",
        clean,
        re.IGNORECASE,
    )
    if not match:
        return None

    ayah = int(match.group(1))
    surah_name = match.group(2)
    surah_number = SURAH_NAME_MAP.get(surah_name)

    if not surah_number:
        return None

    return surah_number, ayah


def get_cc0_verse_audio_candidates():
    files = commons_category_files()
    candidates = []

    for item in files:
        title = item.get("title", "")
        parsed = parse_verse_filename(title)

        if not parsed:
            continue

        candidates.append({
            "title": title,
            "surah_number": parsed[0],
            "ayah_number": parsed[1],
        })

    print(
        f"Found {len(candidates)} individual verse "
        "recordings in Wikimedia Commons category."
    )

    return candidates


def get_commons_audio_url(title):
    api_url = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
    }

    data = request_json(
        api_url,
        params=params,
        timeout=60,
        headers=WIKIMEDIA_HEADERS,
    )

    pages = data.get("query", {}).get("pages", {})

    for page in pages.values():
        imageinfo = page.get("imageinfo")
        if not imageinfo:
            continue

        info = imageinfo[0]
        metadata = info.get("extmetadata", {})

        license_name = (
            metadata.get("LicenseShortName", {})
            .get("value", "")
        )
        license_url = (
            metadata.get("LicenseUrl", {})
            .get("value", "")
        )

        print(f"Audio license: {license_name}")

        allowed = (
            "CC0" in license_name
            or "CC Zero" in license_name
            or "Public domain" in license_name
            or "public domain" in license_name
        )

        if not allowed:
            raise RuntimeError(
                "Audio is not explicitly CC0/public domain: "
                f"{license_name}"
            )

        return (
            info["url"],
            license_name,
            license_url,
        )

    raise RuntimeError(
        f"Could not resolve Wikimedia audio: {title}"
    )


# ============================================================
# WORD GROUPING
# ============================================================

ARABIC_PUNCTUATION = "،؛؟!.,:;!?()[]{}"


def clean_arabic_word(word):
    return word.strip(ARABIC_PUNCTUATION)


def arabic_words(text):
    return [
        clean_arabic_word(x)
        for x in text.split()
        if clean_arabic_word(x)
    ]


def english_words(text):
    return [
        x.strip(".,!?;:()[]{}\"'")
        for x in text.split()
        if x.strip()
    ]


def make_word_groups(words, min_words=3, max_words=4):
    n = len(words)

    if n <= max_words:
        return [words]

    groups = []
    remaining = n
    index = 0

    while remaining > 0:
        if remaining <= max_words:
            size = remaining
        elif remaining == max_words + 1:
            size = min_words
        else:
            size = 3 if remaining % 4 in (1, 2) else 4
            if remaining - size in (1, 2):
                size = 4 if size == 3 else 3

        groups.append(words[index:index + size])
        index += size
        remaining -= size

    return groups


def make_translation_groups(arabic_word_groups, english_text):
    english = english_words(english_text)

    if not english:
        return [""] * len(arabic_word_groups)

    group_count = len(arabic_word_groups)

    if group_count == 1:
        return [english_text]

    total_arabic_words = sum(
        len(group) for group in arabic_word_groups
    )

    result = []
    start = 0

    for i, group in enumerate(arabic_word_groups):
        if i == group_count - 1:
            end = len(english)
        else:
            proportion = (
                len(group) / total_arabic_words
            )
            count = max(
                1,
                round(len(english) * proportion),
            )
            end = min(
                len(english),
                start + count,
            )

        part = english[start:end]

        if not part:
            part = english[
                max(0, start - 1):start + 1
            ]

        result.append(" ".join(part))
        start = end

    return result


# ============================================================
# PEXELS
# ============================================================

def search_pexels_video(topic):
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY is missing.")

    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_API_KEY},
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

    return videos


def choose_pexels_video(videos):
    usable = []

    for video in videos:
        for video_file in video.get("video_files", []):
            width = video_file.get("width") or 0
            height = video_file.get("height") or 0
            link = video_file.get("link")

            if not link or height <= width or height < 1280:
                continue

            usable.append({
                "url": link,
                "width": width,
                "height": height,
                "duration": video.get("duration", 10),
            })

    if not usable:
        for video in videos:
            for video_file in video.get("video_files", []):
                link = video_file.get("link")
                if not link:
                    continue

                usable.append({
                    "url": link,
                    "width": video_file.get(
                        "width", 1080
                    ),
                    "height": video_file.get(
                        "height", 1920
                    ),
                    "duration": video.get("duration", 10),
                })

    if not usable:
        raise RuntimeError(
            "No usable Pexels video file found."
        )

    return random.choice(usable)


def download_nature_video(topic, destination):
    selected = choose_pexels_video(
        search_pexels_video(topic)
    )
    download_file(
        selected["url"],
        destination,
    )
    return selected


# ============================================================
# BACKGROUND VIDEO
# ============================================================

def prepare_nature_background(
    source_files,
    duration,
    output_file,
):
    clip_count = len(source_files)

    if clip_count < 1:
        raise RuntimeError("No nature clips supplied.")

    per_clip = duration / clip_count

    input_args = []
    filters = []

    for index, file_path in enumerate(source_files):
        input_args.extend([
            "-stream_loop", "-1",
            "-i", str(file_path),
        ])

        filters.append(
            f"[{index}:v]"
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            f"force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"setsar=1,"
            f"fps={VIDEO_FPS},"
            f"trim=duration={per_clip},"
            f"setpts=PTS-STARTPTS"
            f"[v{index}]"
        )

    concat_inputs = "".join(
        f"[v{i}]" for i in range(clip_count)
    )

    filter_complex = ";".join(filters)
    filter_complex += (
        f";{concat_inputs}"
        f"concat=n={clip_count}:v=1:a=0,"
        f"trim=duration={duration},"
        f"setpts=PTS-STARTPTS,"
        f"eq=brightness=-0.04:saturation=0.88,"
        f"vignette[v]"
    )

    run_cmd([
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-t", str(duration),
        "-an",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_file),
    ])


# ============================================================
# NATURE SOUND
# ============================================================

def download_nature_sound(sound_info, destination):
    download_file(
        sound_info["url"],
        destination,
    )
    return sound_info


# ============================================================
# TEXT OVERLAY
# ============================================================

def get_english_font():
    local_font = FONT_DIR / "NotoSans-Regular.ttf"

    if local_font.exists():
        return str(local_font)

    return (
        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans.ttf"
    )


def create_text_image(
    arabic_text,
    english_text,
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

    arabic_bbox = draw.textbbox(
        (0, 0),
        arabic_text,
        font=arabic_font,
        direction="rtl",
        language="ar",
    )
    arabic_height = (
        arabic_bbox[3] - arabic_bbox[1]
    )

    english_bbox = draw.textbbox(
        (0, 0),
        english_text,
        font=english_font,
    )
    english_height = (
        english_bbox[3] - english_bbox[1]
    )

    reference_bbox = draw.textbbox(
        (0, 0),
        reference,
        font=reference_font,
    )
    reference_height = (
        reference_bbox[3] - reference_bbox[1]
    )

    total_height = (
        arabic_height
        + 25
        + english_height
        + 25
        + reference_height
    )

    center_y = int(VIDEO_HEIGHT * 0.62)
    arabic_y = center_y - total_height // 2
    english_y = arabic_y + arabic_height + 25
    reference_y = english_y + english_height + 25
    center_x = VIDEO_WIDTH // 2

    # Arabic shadow
    draw.text(
        (center_x + 3, arabic_y + 4),
        arabic_text,
        font=arabic_font,
        fill=(0, 0, 0, 210),
        anchor="ma",
        direction="rtl",
        language="ar",
    )

    # Arabic
    draw.text(
        (center_x, arabic_y),
        arabic_text,
        font=arabic_font,
        fill=(255, 255, 255, 255),
        anchor="ma",
        direction="rtl",
        language="ar",
    )

    # English shadow
    draw.text(
        (center_x + 2, english_y + 3),
        english_text,
        font=english_font,
        fill=(0, 0, 0, 190),
        anchor="ma",
    )

    # English
    draw.text(
        (center_x, english_y),
        english_text,
        font=english_font,
        fill=(245, 245, 245, 255),
        anchor="ma",
    )

    # Reference
    draw.text(
        (center_x, reference_y),
        reference,
        font=reference_font,
        fill=(220, 220, 220, 230),
        anchor="ma",
    )

    image.save(output_file)


# ============================================================
# WORD-GROUP TIMELINE
# ============================================================

def create_overlay_segments(
    arabic_text,
    english_text,
    reference,
    audio_duration,
    output_dir,
):
    arabic = arabic_words(arabic_text)

    if not arabic:
        raise RuntimeError(
            "Arabic Qur'an text contains no words."
        )

    arabic_groups = make_word_groups(
        arabic,
        WORDS_PER_SCREEN_MIN,
        WORDS_PER_SCREEN_MAX,
    )

    english_groups = make_translation_groups(
        arabic_groups,
        english_text,
    )

    segment_duration = (
        audio_duration / len(arabic_groups)
    )

    segments = []
    current_time = 0.0

    for i, arabic_group in enumerate(arabic_groups):
        start = current_time
        end = (
            audio_duration
            if i == len(arabic_groups) - 1
            else current_time + segment_duration
        )

        arabic_segment = " ".join(arabic_group)
        english_segment = (
            english_groups[i]
            if i < len(english_groups)
            else english_text
        )

        image_file = (
            output_dir / f"overlay_{i:03d}.png"
        )

        create_text_image(
            arabic_segment,
            english_segment,
            reference,
            image_file,
        )

        segments.append({
            "start": start,
            "end": end,
            "image": image_file,
        })

        current_time = end

    return segments


# ============================================================
# FINAL VIDEO
# ============================================================

def create_final_video(
    background,
    audio,
    nature_audio,
    overlays,
    duration,
    output_file,
):
    overlay_inputs = []
    filter_parts = []

    previous = "[0:v]"

    # 0 = background
    # 1 = Qur'an recitation
    # 2 = nature ambience
    # 3+ = overlay PNGs
    for index, overlay in enumerate(overlays):
        input_index = index + 3
        output_label = f"[ov{index}]"

        overlay_inputs.extend([
            "-loop", "1",
            "-i", str(overlay["image"]),
        ])

        filter_parts.append(
            f"{previous}"
            f"[{input_index}:v]"
            f"overlay=0:0:"
            f"enable='between(t,"
            f"{overlay['start']},"
            f"{overlay['end']})'"
            f"{output_label}"
        )

        previous = output_label

    filter_parts.append(
        "[1:a]"
        "aresample=48000,"
        "volume=1.0"
        "[recitation]"
    )

    filter_parts.append(
        "[2:a]"
        "aresample=48000,"
        f"volume={NATURE_AUDIO_VOLUME},"
        f"atrim=duration={duration}"
        "[nature]"
    )

    filter_parts.append(
        "[recitation][nature]"
        "amix=inputs=2:"
        "duration=first:"
        "dropout_transition=0"
        "[audio]"
    )

    filter_complex = ";".join(filter_parts)

    run_cmd([
        "ffmpeg", "-y",
        "-i", str(background),
        "-i", str(audio),
        "-stream_loop", "-1",
        "-i", str(nature_audio),
        *overlay_inputs,
        "-filter_complex", filter_complex,
        "-map", previous,
        "-map", "[audio]",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
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
    quran,
    topic,
    audio_license,
    audio_license_url,
    nature_sound_name,
):
    title = (
        f"{quran['surah_name']} "
        f"{quran['surah_number']}:{quran['ayah_number']} "
        "— A Reminder for the Heart"
    )

    description = f"""Listen, reflect, and remember.

Qur'an — Surah {quran['surah_name']} ({quran['surah_number']}:{quran['ayah_number']})

Arabic Qur'an text:
Source: Tanzil Quran Text
License: CC BY 3.0
https://tanzil.net

English translation:
Marmaduke Pickthall (1930)
Public domain.

Qur'an recitation:
CC0/public-domain recording from Wikimedia Commons.
License: {audio_license}
License information: {audio_license_url}

Background footage:
Pexels.

Nature ambience:
{nature_sound_name}
CC0/public-domain Wikimedia Commons recording.

Nature theme:
{topic}

This video is created for reflection, remembrance and learning.

#Quran #QuranShorts #Islam #Allah #IslamicReminder #QuranRecitation #Ayah #Muslim #IslamicShorts #Nature
"""

    metadata_file = (
        OUTPUT_DIR / f"metadata_{index}.txt"
    )

    metadata_file.write_text(
        f"TITLE:\n{title}\n\n"
        f"DESCRIPTION:\n{description}\n",
        encoding="utf-8",
    )

    return title, description


# ============================================================
# CREATE ONE SHORT
# ============================================================

def create_short(
    index,
    topic,
    quran_audio_info,
):
    print()
    print("=" * 70)
    print(f"CREATING SHORT {index}")
    print("=" * 70)

    surah = quran_audio_info["surah_number"]
    ayah = quran_audio_info["ayah_number"]

    quran = get_quran_data(
        surah,
        ayah,
    )

    print(
        "Qur'an: "
        f"{quran['surah_name']} "
        f"{quran['surah_number']}:{quran['ayah_number']}"
    )

    # --------------------------------------------------------
    # CC0/public-domain Qur'an recitation
    # --------------------------------------------------------

    audio_file = (
        TEMP_DIR / f"recitation_{index}.mp3"
    )

    download_file(
        quran_audio_info["url"],
        audio_file,
    )

    audio_duration = get_duration(
        audio_file
    )

    print(
        f"Recitation duration: "
        f"{audio_duration:.2f} seconds"
    )

    # --------------------------------------------------------
    # CC0/public-domain nature ambience
    # --------------------------------------------------------

    sound_info = random.choice(NATURE_SOUNDS)

    nature_audio = (
        TEMP_DIR / f"nature_sound_{index}.ogg"
    )

    download_nature_sound(
        sound_info,
        nature_audio,
    )

    # --------------------------------------------------------
    # Nature clips
    # --------------------------------------------------------

    clip_count = (
        2 if audio_duration <= 12 else 3
    )

    selected_topics = random.sample(
        TOPICS,
        clip_count,
    )

    nature_clips = []

    for clip_number, clip_topic in enumerate(
        selected_topics,
        start=1,
    ):
        clip_file = (
            TEMP_DIR
            / f"nature_{index}_{clip_number}.mp4"
        )

        download_nature_video(
            clip_topic,
            clip_file,
        )

        nature_clips.append(clip_file)

    # --------------------------------------------------------
    # Background
    # --------------------------------------------------------

    background = (
        TEMP_DIR / f"background_{index}.mp4"
    )

    prepare_nature_background(
        nature_clips,
        audio_duration,
        background,
    )

    # --------------------------------------------------------
    # Arabic + English word groups
    # --------------------------------------------------------

    reference = (
        f"{quran['surah_name']} "
        f"• {quran['surah_number']}:{quran['ayah_number']}"
    )

    overlay_dir = (
        TEMP_DIR / f"overlays_{index}"
    )
    overlay_dir.mkdir(exist_ok=True)

    overlays = create_overlay_segments(
        quran["arabic"],
        quran["english"],
        reference,
        audio_duration,
        overlay_dir,
    )

    # --------------------------------------------------------
    # Final video
    # --------------------------------------------------------

    output_file = (
        OUTPUT_DIR
        / f"nature_quran_short_{index}.mp4"
    )

    create_final_video(
        background,
        audio_file,
        nature_audio,
        overlays,
        audio_duration,
        output_file,
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    create_metadata(
        index,
        quran,
        topic,
        quran_audio_info["license"],
        quran_audio_info["license_url"],
        sound_info["name"],
    )

    print(f"Created: {output_file}")
    return output_file


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("NATURE QURAN SHORTS GENERATOR")
    print("=" * 70)

    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY is missing."
        )

    if not ARABIC_FONT.exists():
        raise RuntimeError(
            f"Arabic font missing: {ARABIC_FONT}"
        )

    # Discover individual CC0/public-domain recordings.
    candidates = (
        get_cc0_verse_audio_candidates()
    )

    if len(candidates) < SHORT_COUNT:
        raise RuntimeError(
            "Not enough individual CC0/public-domain "
            "verse recordings available."
        )

    # Three different verses each day.
    selected = random.sample(
        candidates,
        SHORT_COUNT,
    )

    for index, candidate in enumerate(
        selected,
        start=1,
    ):
        print()
        print(
            f"SHORT {index}: "
            f"Surah {candidate['surah_number']}, "
            f"Ayah {candidate['ayah_number']}"
        )

        (
            audio_url,
            license_name,
            license_url,
        ) = get_commons_audio_url(
            candidate["title"]
        )

        audio_info = {
            "title": candidate["title"],
            "url": audio_url,
            "license": license_name,
            "license_url": license_url,
            "surah_number": candidate["surah_number"],
            "ayah_number": candidate["ayah_number"],
        }

        topic = random.choice(TOPICS)

        create_short(
            index,
            topic,
            audio_info,
        )

    print()
    print("=" * 70)
    print("ALL 3 SHORTS CREATED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
