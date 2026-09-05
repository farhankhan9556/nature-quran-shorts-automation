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
# QURAN AYAH NUMBERS
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
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "NatureQuranShorts/1.0",
    "Accept": "*/*"
})


# ============================================================
# DOWNLOAD FILE
# ============================================================

def download_file(url, destination):

    print(f"Downloading:")
    print(url)

    response = session.get(
        url,
        timeout=90,
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
# PEXELS NATURE VIDEO
# ============================================================

def get_pexels_video(
    topic,
    index,
    clip_number
):

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
            f"No Pexels videos found: {topic}"
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

            if height <= width:
                continue

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

                if link:

                    candidates.append({
                        "width":
                            file_info.get(
                                "width"
                            ) or 0,

                        "height":
                            file_info.get(
                                "height"
                            ) or 0,

                        "link": link
                    })

    if not candidates:
        raise RuntimeError(
            f"No downloadable Pexels video: {topic}"
        )

    candidates.sort(
        key=lambda x:
        x["width"] * x["height"],
        reverse=True
    )

    selected = random.choice(
        candidates[
            :min(8, len(candidates))
        ]
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
        f"Getting Quran Ayah: {global_ayah}"
    )

    response = session.get(
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
        "global_number":
            global_ayah,

        "arabic":
            ayah["text"],

        "surah_name":
            ayah["surah"]["englishName"],

        "surah_number":
            ayah["surah"]["number"],

        "ayah_number":
            ayah["numberInSurah"]
    }


# ============================================================
# GET COMPLETE ALAFASY RECITATION
#
# IMPORTANT:
# We now ask Al Quran Cloud API for the official
# audio URL instead of hard-coding the 192 kbps URL.
# ============================================================

def get_quran_audio(
    global_ayah,
    index
):

    print()
    print(
        f"Getting Alafasy audio URL "
        f"for Ayah {global_ayah}"
    )

    api_url = (
        f"https://api.alquran.cloud/v1/"
        f"ayah/{global_ayah}/ar.alafasy"
    )

    response = session.get(
        api_url,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "OK":
        raise RuntimeError(
            f"Audio API error for Ayah "
            f"{global_ayah}"
        )

    ayah_data = data.get("data", {})

    audio_url = ayah_data.get("audio")

    if not audio_url:

        # Some API responses may provide
        # multiple audio URLs.
        audio_urls = (
            ayah_data.get("audioSecondary")
            or []
        )

        if audio_urls:
            audio_url = audio_urls[0]

    if not audio_url:

        raise RuntimeError(
            f"No Alafasy audio URL returned "
            f"for Ayah {global_ayah}"
        )

    print()
    print("Official audio URL returned by API:")
    print(audio_url)

    destination = (
        ASSETS_DIR /
        f"quran_{index}.mp3"
    )

    # --------------------------------------------------------
    # Download API-provided URL
    # --------------------------------------------------------

    try:

        download_file(
            audio_url,
            destination
        )

        print(
            "Alafasy audio downloaded successfully."
        )

        return destination

    except requests.HTTPError as first_error:

        print()
        print(
            "API-provided audio URL failed:"
        )

        print(first_error)

        # ----------------------------------------------------
        # Fallback CDN URLs
        #
        # 128 is Alafasy's documented default bitrate.
        # ----------------------------------------------------

        fallback_bitrates = [
            128,
            64,
            192,
            48,
            40,
            32
        ]

        for bitrate in fallback_bitrates:

            fallback_url = (
                "https://cdn.islamic.network/"
                f"quran/audio/{bitrate}/"
                f"ar.alafasy/"
                f"{global_ayah}.mp3"
            )

            print()
            print(
                f"Trying fallback "
                f"{bitrate} kbps..."
            )

            try:

                download_file(
                    fallback_url,
                    destination
                )

                print(
                    f"Fallback {bitrate} kbps "
                    f"download successful."
                )

                return destination

            except requests.RequestException as error:

                print(
                    f"{bitrate} kbps failed: "
                    f"{error}"
                )

        raise RuntimeError(
            "Unable to download Alafasy "
            f"audio for Ayah {global_ayah}."
        ) from first_error


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

    print()
    print(
        f"COMPLETE RECITATION: "
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

        width = (
            bbox[2] -
            bbox[0]
        )

        if width <= max_width:

            current_line = test_line

        else:

            if current_line:
                lines.append(
                    current_line
                )

            current_line = word

    if current_line:
        lines.append(
            current_line
        )

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
            bbox[3] -
            bbox[1]
        )

    total_height = (
        sum(line_heights)
        +
        line_spacing *
        (len(lines) - 1)
    )

    center_y = 1070

    start_y = (
        center_y -
        total_height // 2
    )

    y = start_y

    # --------------------------------------------------------
    # Arabic Quran text
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
            bbox[2] -
            bbox[0]
        )

        x = (
            WIDTH -
            text_width
        ) // 2

        # Shadow
        draw.text(
            (
                x + 3,
                y + 5
            ),
            line,
            font=font,
            fill=(0, 0, 0, 190),
            direction="rtl",
            language="ar"
        )

        # Arabic
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
    # Surah / Verse reference
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
        bbox[2] -
        bbox[0]
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
# METADATA
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

    title = random.choice(titles)

    if len(title) > 95:

        title = (
            f"Quran Reminder | "
            f"{surah} {verse} #Shorts"
        )

    description = f"""Listen to a complete recitation from the Holy Quran — {surah}, Verse {verse}.

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
        f.write(
            ", ".join(tags)
        )
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
    print(
        f"CREATING {clip_count}-CLIP SHORT"
    )

    print(
        f"RECITATION: "
        f"{duration:.2f} seconds"
    )

    print("=" * 70)

    final_duration = (
        duration + 0.20
    )

    segment_duration = (
        duration /
        clip_count
    )

    filter_parts = []

    # --------------------------------------------------------
    # Prepare each nature clip
    # --------------------------------------------------------

    for i in range(
        clip_count
    ):

        current_duration = (
            segment_duration
        )

        if i == clip_count - 1:

            current_duration = (
                duration -
                segment_duration *
                (clip_count - 1)
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
    # Join all nature clips
    # --------------------------------------------------------

    concat_inputs = ""

    for i in range(
        clip_count
    ):

        concat_inputs += (
            f"[clip{i}]"
        )

    filter_parts.append(
        concat_inputs
        +
        f"concat=n={clip_count}:"
        f"v=1:a=0,"
        f"setpts=PTS-STARTPTS"
        f"[nature]"
    )

    # --------------------------------------------------------
    # Arabic overlay
    #
    # Nature inputs = 0,1,2
    # Audio = clip_count
    # Overlay = clip_count + 1
    # --------------------------------------------------------

    overlay_input = (
        clip_count + 1
    )

    filter_parts.append(
        f"[nature]"
        f"[{overlay_input}:v]"
        f"overlay=0:0:"
        f"format=auto,"
        f"format=yuv420p"
        f"[v]"
    )

    filter_complex = ";".join(
        filter_parts
    )

    # --------------------------------------------------------
    # FFmpeg command
    # --------------------------------------------------------

    command = [
        "ffmpeg",
        "-y"
    ]

    # Nature videos
    for clip in nature_clips:

        command += [
            "-stream_loop",
            "-1",
            "-i",
            str(clip)
        ]

    # Audio
    command += [
        "-i",
        str(audio_file)
    ]

    # Overlay
    command += [
        "-i",
        str(overlay_file)
    ]

    command += [
        "-filter_complex",
        filter_complex,

        "-map",
        "[v]",

        # Audio input index
        "-map",
        f"{clip_count}:a:0",

        # Complete recitation + tiny safety margin
        "-t",
        f"{final_duration:.3f}",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "19",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "48000",

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

    print()
    print(
        "Video created successfully."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("NATURE + QURAN SHORTS")
    print("3 VIDEOS / RUN")
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
    # Clean output
    # --------------------------------------------------------

    for file in OUTPUT_DIR.glob("*"):

        if file.is_file():
            file.unlink()

    # --------------------------------------------------------
    # Select 3 unique Ayahs
    # --------------------------------------------------------

    selected_ayahs = random.sample(
        QURAN_AYAHS,
        VIDEO_COUNT
    )

    # --------------------------------------------------------
    # Select 3 different main nature topics
    # --------------------------------------------------------

    selected_topics = random.sample(
        TOPICS,
        VIDEO_COUNT
    )

    print()
    print("TODAY'S VIDEOS")
    print("-" * 70)

    for i in range(
        VIDEO_COUNT
    ):

        print(
            f"{i + 1}. "
            f"{selected_topics[i]} | "
            f"Ayah {selected_ayahs[i]}"
        )

    # ========================================================
    # CREATE THREE SHORTS
    # ========================================================

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
        # COMPLETE AYAH
        # ----------------------------------------------------

        quran = get_quran_ayah(
            global_ayah
        )

        # ----------------------------------------------------
        # COMPLETE RECITATION
        # ----------------------------------------------------

        audio_file = get_quran_audio(
            global_ayah,
            index
        )

        # ----------------------------------------------------
        # ACTUAL AUDIO LENGTH
        # ----------------------------------------------------

        duration = get_audio_duration(
            audio_file
        )

        # ----------------------------------------------------
        # 2 OR 3 NATURE CLIPS
        # ----------------------------------------------------

        if duration <= 12:
            clip_count = 2
        else:
            clip_count = 3

        print()
        print(
            f"Using {clip_count} nature clips."
        )

        # ----------------------------------------------------
        # Unique nature topics
        # ----------------------------------------------------

        remaining_topics = [
            x
            for x in TOPICS
            if x != topic
        ]

        clip_topics = [
            topic
        ]

        clip_topics += random.sample(
            remaining_topics,
            clip_count - 1
        )

        # ----------------------------------------------------
        # Download nature clips
        # ----------------------------------------------------

        nature_clips = []

        for clip_number, clip_topic in enumerate(
            clip_topics,
            start=1
        ):

            print()
            print(
                f"Clip {clip_number}: "
                f"{clip_topic}"
            )

            clip = get_pexels_video(
                clip_topic,
                index,
                clip_number
            )

            nature_clips.append(
                clip
            )

        # ----------------------------------------------------
        # Arabic overlay
        # ----------------------------------------------------

        overlay_file = create_text_overlay(
            quran,
            index
        )

        # ----------------------------------------------------
        # Metadata
        # ----------------------------------------------------

        title = create_metadata(
            quran,
            topic,
            index
        )

        # ----------------------------------------------------
        # Final video
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
            f"Complete recitation: "
            f"{duration:.2f} seconds"
        )

        print(
            f"Nature clips: "
            f"{clip_count}"
        )

        print(
            f"Output: "
            f"{output_file.name}"
        )

    # ========================================================
    # FINAL CHECK
    # ========================================================

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
