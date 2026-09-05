import os
import random
import subprocess
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# SETTINGS
# ============================================================

WIDTH = 1080
HEIGHT = 1920

VIDEO_COUNT = 3

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"
FONT_DIR = BASE_DIR / "fonts"

ASSETS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ARABIC_FONT = FONT_DIR / "NotoNaskhArabic-Regular.otf"

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

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
    "beautiful nature"
]

# ============================================================
# COMPLETE AYAH NUMBERS
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
    5984
]

# ============================================================
# HELPERS
# ============================================================

def download_file(url, destination):

    print(f"Downloading: {url}")

    response = requests.get(
        url,
        timeout=60,
        stream=True
    )

    response.raise_for_status()

    with open(destination, "wb") as f:
        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):
            if chunk:
                f.write(chunk)

    return destination


# ============================================================
# SEARCH AND DOWNLOAD ONE PEXELS NATURE CLIP
# ============================================================

def get_pexels_video(topic, index, clip_number):

    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY is missing."
        )

    print()
    print(
        f"Searching Pexels: "
        f"{topic} | Clip {clip_number}"
    )

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": topic,
        "orientation": "portrait",
        "size": "large",
        "per_page": 30
    }

    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers=headers,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    videos = response.json().get(
        "videos",
        []
    )

    if not videos:
        raise RuntimeError(
            f"No Pexels videos found for: {topic}"
        )

    candidates = []

    for video in videos:

        for file_info in video.get(
            "video_files",
            []
        ):

            width = file_info.get(
                "width"
            ) or 0

            height = file_info.get(
                "height"
            ) or 0

            link = file_info.get("link")

            if not link:
                continue

            # Prefer portrait
            if height <= width:
                continue

            # Prefer good resolution
            if width < 720:
                continue

            candidates.append({
                "width": width,
                "height": height,
                "link": link
            })

    # Fallback
    if not candidates:

        for video in videos:

            for file_info in video.get(
                "video_files",
                []
            ):

                link = file_info.get("link")

                width = file_info.get(
                    "width"
                ) or 0

                height = file_info.get(
                    "height"
                ) or 0

                if link:

                    candidates.append({
                        "width": width,
                        "height": height,
                        "link": link
                    })

    if not candidates:
        raise RuntimeError(
            f"No downloadable video found for {topic}"
        )

    candidates.sort(
        key=lambda x:
        x["width"] * x["height"],
        reverse=True
    )

    # Pick randomly from the best videos
    top_candidates = candidates[
        :min(8, len(candidates))
    ]

    selected = random.choice(
        top_candidates
    )

    print(
        f"Selected: "
        f"{selected['width']}x"
        f"{selected['height']}"
    )

    destination = (
        ASSETS_DIR /
        f"nature_{index}_{clip_number}.mp4"
    )

    download_file(
        selected["link"],
        destination
    )

    return destination


# ============================================================
# GET COMPLETE QURAN AYAH
# ============================================================

def get_quran_ayah(global_ayah):

    url = (
        f"https://api.alquran.cloud/v1/"
        f"ayah/{global_ayah}/quran-uthmani"
    )

    print()
    print(
        f"Getting complete Quran Ayah: "
        f"{global_ayah}"
    )

    response = requests.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "OK":
        raise RuntimeError(
            f"Quran API error: {global_ayah}"
        )

    ayah = data["data"]

    return {
        "global_number": global_ayah,
        "arabic": ayah["text"],
        "surah_name": ayah["surah"]["englishName"],
        "surah_number": ayah["surah"]["number"],
        "ayah_number": ayah["numberInSurah"]
    }


# ============================================================
# GET COMPLETE ALAFASY RECITATION
# ============================================================

def get_quran_audio(
    global_ayah,
    index
):

    url = (
        f"https://cdn.islamic.network/"
        f"quran/audio/192/ar.alafasy/"
        f"{global_ayah}.mp3"
    )

    destination = (
        ASSETS_DIR /
        f"quran_{index}.mp3"
    )

    print()
    print(
        f"Downloading complete recitation "
        f"for Ayah {global_ayah}"
    )

    download_file(
        url,
        destination
    )

    return destination


# ============================================================
# GET AUDIO DURATION
# ============================================================

def get_audio_duration(audio_file):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_file)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    duration = float(
        result.stdout.strip()
    )

    print(
        f"Complete recitation: "
        f"{duration:.2f} seconds"
    )

    return duration


# ============================================================
# ARABIC TEXT WRAPPING
# ============================================================

def wrap_arabic_text(
    draw,
    text,
    font,
    max_width
):

    words = text.split()

    lines = []
    current_line = ""

    for word in words:

        test_line = (
            word
            if not current_line
            else current_line + " " + word
        )

        bbox = draw.textbbox(
            (0, 0),
            test_line,
            font=font,
            direction="rtl",
            language="ar"
        )

        width = bbox[2] - bbox[0]

        if width <= max_width:

            current_line = test_line

        else:

            if current_line:
                lines.append(
                    current_line
                )

            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


# ============================================================
# CREATE ARABIC OVERLAY
# ============================================================

def create_text_overlay(
    quran,
    index
):

    if not ARABIC_FONT.exists():
        raise RuntimeError(
            f"Missing font: {ARABIC_FONT}"
        )

    overlay = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(
        overlay
    )

    arabic_text = quran["arabic"]

    # Start large and reduce if necessary
    font_size = 110

    while font_size >= 54:

        font = ImageFont.truetype(
            str(ARABIC_FONT),
            font_size
        )

        lines = wrap_arabic_text(
            draw,
            arabic_text,
            font,
            900
        )

        if len(lines) <= 4:
            break

        font_size -= 4

    line_spacing = int(
        font_size * 0.35
    )

    line_heights = []

    for line in lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font,
            direction="rtl",
            language="ar"
        )

        line_heights.append(
            bbox[3] - bbox[1]
        )

    total_height = (
        sum(line_heights)
        + line_spacing *
        (len(lines) - 1)
    )

    # Lower-middle position
    center_y = 1070

    start_y = (
        center_y -
        total_height // 2
    )

    y = start_y

    # --------------------------------------------------------
    # Arabic
    # --------------------------------------------------------

    for line, line_height in zip(
        lines,
        line_heights
    ):

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font,
            direction="rtl",
            language="ar"
        )

        text_width = (
            bbox[2] - bbox[0]
        )

        x = (
            WIDTH -
            text_width
        ) // 2

        # Subtle shadow
        draw.text(
            (x + 3, y + 5),
            line,
            font=font,
            fill=(0, 0, 0, 190),
            direction="rtl",
            language="ar"
        )

        # White Arabic
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            direction="rtl",
            language="ar"
        )

        y += (
            line_height +
            line_spacing
        )

    # --------------------------------------------------------
    # Surah / Verse
    # --------------------------------------------------------

    reference_font = ImageFont.truetype(
        str(ARABIC_FONT),
        42
    )

    reference = (
        f"{quran['surah_name']} • "
        f"Verse {quran['ayah_number']}"
    )

    bbox = draw.textbbox(
        (0, 0),
        reference,
        font=reference_font
    )

    reference_width = (
        bbox[2] - bbox[0]
    )

    reference_x = (
        WIDTH -
        reference_width
    ) // 2

    reference_y = (
        start_y +
        total_height +
        35
    )

    draw.text(
        (
            reference_x + 2,
            reference_y + 3
        ),
        reference,
        font=reference_font,
        fill=(0, 0, 0, 170)
    )

    draw.text(
        (
            reference_x,
            reference_y
        ),
        reference,
        font=reference_font,
        fill=(235, 235, 235, 230)
    )

    overlay_path = (
        ASSETS_DIR /
        f"overlay_{index}.png"
    )

    overlay.save(
        overlay_path
    )

    return overlay_path


# ============================================================
# CREATE PROFESSIONAL METADATA
# ============================================================

def create_metadata(
    quran,
    topic,
    index
):

    surah = quran["surah_name"]
    verse = quran["ayah_number"]

    titles = [

        f"Let This Quran Verse Bring Peace to Your Heart | {surah} {verse} #Shorts",

        f"A Beautiful Reminder From the Quran | {surah} {verse} #Shorts",

        f"Listen to This Powerful Quran Reminder | {surah} {verse} #Shorts",

        f"One Quran Verse to Reflect On Today | {surah} {verse} #Shorts",

        f"Find Peace in the Words of Allah | {surah} {verse} #Shorts",

        f"A Moment of Peace With the Quran | {surah} {verse} #Shorts"
    ]

    title = random.choice(
        titles
    )

    if len(title) > 95:
        title = (
            f"Quran Reminder | "
            f"{surah} {verse} #Shorts"
        )

    description = f"""Listen to a beautiful complete recitation from the Holy Quran — {surah}, Verse {verse}.

Take a quiet moment to listen, reflect and remember Allah.

May the words of the Quran bring peace, guidance and strength to your heart.

📖 Surah: {surah}
🔢 Verse: {verse}

🎙️ Recitation: Mishary Rashid Alafasy
📜 Arabic Quran text: Al Quran Cloud / Uthmani text
🌿 Nature footage: Pexels

Created for peaceful Quran listening, reflection and Islamic reminders.

#Quran #QuranRecitation #IslamicShorts #QuranShorts #Islam #Allah #IslamicReminder #Shorts
"""

    tags = [
        "Quran",
        "Quran recitation",
        "Quran Shorts",
        "Quran short",
        "Islamic Shorts",
        "Islam",
        "Allah",
        "Holy Quran",
        "Quran reminder",
        "Islamic reminder",
        "beautiful Quran recitation",
        "Alafasy",
        "Mishary Alafasy",
        surah,
        f"{surah} {verse}",
        topic
    ]

    metadata_path = (
        OUTPUT_DIR /
        f"metadata_{index}.txt"
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("TITLE\n")
        f.write("=====\n")
        f.write(title)
        f.write("\n\n")

        f.write("DESCRIPTION\n")
        f.write("===========\n")
        f.write(description)
        f.write("\n")

        f.write("TAGS\n")
        f.write("====\n")
        f.write(", ".join(tags))
        f.write("\n\n")

        f.write("SURAH\n")
        f.write("=====\n")
        f.write(surah)
        f.write("\n\n")

        f.write("VERSE\n")
        f.write("=====\n")
        f.write(str(verse))
        f.write("\n\n")

        f.write("ARABIC AYAH\n")
        f.write("===========\n")
        f.write(quran["arabic"])
        f.write("\n\n")

        f.write("NATURE TOPIC\n")
        f.write("============\n")
        f.write(topic)
        f.write("\n")

    return title


# ============================================================
# CREATE MULTI-CLIP VIDEO
# ============================================================

def create_video(
    nature_clips,
    audio_file,
    overlay_file,
    output_file,
    duration
):

    clip_count = len(
        nature_clips
    )

    print()
    print("=" * 70)
    print(f"CREATING {clip_count}-CLIP QURAN SHORT")
    print(f"TOTAL DURATION: {duration:.2f} seconds")
    print("=" * 70)

    # Small safety margin.
    final_duration = duration + 0.20

    # --------------------------------------------------------
    # Divide the video duration between clips
    # --------------------------------------------------------

    segment_duration = (
        duration / clip_count
    )

    filter_parts = []

    for i in range(clip_count):

        # Last clip receives any tiny remaining duration
        if i == clip_count - 1:

            current_duration = (
                duration -
                segment_duration *
                (clip_count - 1)
            )

        else:

            current_duration = (
                segment_duration
            )

        filter_parts.append(
            f"[{i}:v]"
            f"scale={WIDTH}:{HEIGHT}:"
            f"force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"fps=30,"
            f"eq=brightness=-0.07:"
            f"contrast=1.08:"
            f"saturation=0.92,"
            f"vignette,"
            f"trim=duration={current_duration:.3f},"
            f"setpts=PTS-STARTPTS"
            f"[clip{i}]"
        )

    # --------------------------------------------------------
    # Join nature clips
    # --------------------------------------------------------

    concat_inputs = ""

    for i in range(clip_count):
        concat_inputs += (
            f"[clip{i}]"
        )

    concat_filter = (
        concat_inputs +
        f"concat=n={clip_count}:"
        f"v=1:a=0,"
        f"setpts=PTS-STARTPTS"
        f"[nature]"
    )

    # --------------------------------------------------------
    # Add Arabic overlay
    # --------------------------------------------------------

    overlay_filter = (
        "[nature]["
        f"{clip_count}:v"
        "]overlay=0:0:"
        "format=auto,"
        "format=yuv420p"
        "[v]"
    )

    filter_complex = (
        ";".join(filter_parts)
        + ";"
        + concat_filter
        + ";"
        + overlay_filter
    )

    # --------------------------------------------------------
    # FFmpeg inputs
    # --------------------------------------------------------

    command = [
        "ffmpeg",
        "-y"
    ]

    # Nature clips
    for clip in nature_clips:

        command += [
            "-stream_loop",
            "-1",
            "-i",
            str(clip)
        ]

    # Quran audio
    command += [
        "-i",
        str(audio_file)
    ]

    # Arabic overlay
    command += [
        "-i",
        str(overlay_file)
    ]

    # --------------------------------------------------------
    # Filters
    # --------------------------------------------------------

    command += [
        "-filter_complex",
        filter_complex,

        "-map",
        "[v]",

        # Audio input comes after all nature videos
        "-map",
        f"{clip_count}:a:0",

        "-t",
        f"{final_duration:.3f}",

        # Video encoding
        "-c:v",
        "libx264",

        "-preset",
        "medium",

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
        "48000",

        # YouTube-friendly MP4
        "-movflags",
        "+faststart",

        str(output_file)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print()
        print("FFMPEG ERROR")
        print("=" * 70)
        print(result.stderr)

        raise RuntimeError(
            "FFmpeg failed."
        )

    print(
        f"Video created successfully: "
        f"{output_file}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("NATURE + QURAN SHORTS AUTOMATION")
    print("3 PROFESSIONAL SHORTS")
    print("=" * 70)

    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY is missing."
        )

    if not ARABIC_FONT.exists():
        raise RuntimeError(
            f"Missing font: {ARABIC_FONT}"
        )

    # --------------------------------------------------------
    # Clean previous output
    # --------------------------------------------------------

    for file in OUTPUT_DIR.glob("*"):

        if file.is_file():
            file.unlink()

    # --------------------------------------------------------
    # Select 3 different Ayahs
    # --------------------------------------------------------

    selected_ayahs = random.sample(
        QURAN_AYAHS,
        VIDEO_COUNT
    )

    # --------------------------------------------------------
    # Select 3 different primary nature themes
    # --------------------------------------------------------

    selected_topics = random.sample(
        TOPICS,
        VIDEO_COUNT
    )

    print()
    print("TODAY'S 3 SHORTS")
    print("-" * 70)

    for i in range(VIDEO_COUNT):

        print(
            f"{i + 1}. "
            f"{selected_topics[i]} | "
            f"Ayah {selected_ayahs[i]}"
        )

    # --------------------------------------------------------
    # Create each Short
    # --------------------------------------------------------

    for index in range(
        1,
        VIDEO_COUNT + 1
    ):

        topic = selected_topics[
            index - 1
        ]

        global_ayah = selected_ayahs[
            index - 1
        ]

        print()
        print()
        print("#" * 70)
        print(
            f"SHORT {index} / {VIDEO_COUNT}"
        )
        print("#" * 70)

        # ----------------------------------------------------
        # 1. Complete Ayah
        # ----------------------------------------------------

        quran = get_quran_ayah(
            global_ayah
        )

        # ----------------------------------------------------
        # 2. Complete recitation
        # ----------------------------------------------------

        audio_file = get_quran_audio(
            global_ayah,
            index
        )

        # ----------------------------------------------------
        # 3. Measure actual recitation
        # ----------------------------------------------------

        duration = get_audio_duration(
            audio_file
        )

        # ----------------------------------------------------
        # 4. Decide 2 or 3 nature clips
        #
        # Shorter Ayahs:
        # 2 clips
        #
        # Longer Ayahs:
        # 3 clips
        # ----------------------------------------------------

        if duration <= 12:
            clip_count = 2
        else:
            clip_count = 3

        print(
            f"Nature clips required: "
            f"{clip_count}"
        )

        # ----------------------------------------------------
        # 5. Select DIFFERENT nature topics
        # ----------------------------------------------------

        remaining_topics = [
            x for x in TOPICS
            if x != topic
        ]

        clip_topics = [
            topic
        ]

        clip_topics += random.sample(
            remaining_topics,
            clip_count - 1
        )

        print()
        print("Nature sequence:")

        for number, clip_topic in enumerate(
            clip_topics,
            start=1
        ):

            print(
                f"Clip {number}: "
                f"{clip_topic}"
            )

        # ----------------------------------------------------
        # 6. Download nature clips
        # ----------------------------------------------------

        nature_clips = []

        for clip_number, clip_topic in enumerate(
            clip_topics,
            start=1
        ):

            clip = get_pexels_video(
                clip_topic,
                index,
                clip_number
            )

            nature_clips.append(
                clip
            )

        # ----------------------------------------------------
        # 7. Create Arabic overlay
        # ----------------------------------------------------

        overlay_file = create_text_overlay(
            quran,
            index
        )

        # ----------------------------------------------------
        # 8. Create metadata
        # ----------------------------------------------------

        title = create_metadata(
            quran,
            topic,
            index
        )

        # ----------------------------------------------------
        # 9. Create final Short
        # ----------------------------------------------------

        output_file = (
            OUTPUT_DIR /
            f"nature_quran_short_{index}.mp4"
        )

        create_video(
            nature_clips,
            audio_file,
            overlay_file,
            output_file,
            duration
        )

        print()
        print(
            f"SHORT {index} COMPLETE"
        )

        print(
            f"Title: {title}"
        )

        print(
            f"Recitation: "
            f"{duration:.2f} seconds"
        )

        print(
            f"Nature clips: "
            f"{clip_count}"
        )

        print(
            f"File: {output_file.name}"
        )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("ALL 3 SHORTS CREATED SUCCESSFULLY")
    print("=" * 70)

    for file in sorted(
        OUTPUT_DIR.glob("*.mp4")
    ):

        size_mb = (
            file.stat().st_size /
            (1024 * 1024)
        )

        print(
            f"{file.name}: "
            f"{size_mb:.2f} MB"
        )


if __name__ == "__main__":
    main()
