import asyncio
import os
import random
import subprocess
from pathlib import Path

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# ONLINE EARNING SHORTS GENERATOR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
FONT_DIR = BASE_DIR / "fonts"

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")


# ============================================================
# VIDEO SETTINGS
# ============================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# EXACTLY 3 VIDEOS PER RUN
SHORT_COUNT = 3

# Target length
TARGET_SECONDS = 15

# AI voice
VOICE = "en-US-GuyNeural"

# Slightly faster voice for Shorts
VOICE_RATE = "+12%"

# Background music volume
MUSIC_VOLUME = 0.035


# ============================================================
# ONLINE EARNING TOPICS
# ============================================================

TOPICS = [

    {
        "topic": "TikTok earning",
        "query": "person using smartphone social media",

        "hook": "Want to earn from TikTok?",

        "body": (
            "Pick one niche, post useful short videos consistently, "
            "then explore eligible creator monetization, affiliate "
            "offers and sponsorships."
        ),

        "cta": "Follow for more daily earning tips!"
    },

    {
        "topic": "Affiliate marketing",
        "query": "laptop online shopping business",

        "hook": "Want to start affiliate marketing?",

        "body": (
            "Choose a useful product, create honest content around it, "
            "and send viewers through your approved affiliate link."
        ),

        "cta": "Follow for more online income ideas!"
    },

    {
        "topic": "AI freelancing",
        "query": "person working laptop artificial intelligence",

        "hook": "AI can help you freelance faster.",

        "body": (
            "Learn one useful AI workflow, turn it into a service, "
            "and sell the result instead of simply selling the tool."
        ),

        "cta": "Follow for practical AI income tips!"
    },

    {
        "topic": "YouTube Shorts",
        "query": "creator recording video smartphone",

        "hook": "Starting a YouTube Shorts channel?",

        "body": (
            "Choose one clear topic, make strong hooks, use readable "
            "captions, and improve each video from your audience retention."
        ),

        "cta": "Subscribe for more creator tips!"
    },

    {
        "topic": "Digital products",
        "query": "laptop digital product creator",

        "hook": "Want income from a digital product?",

        "body": (
            "Solve one specific problem with a simple template, guide "
            "or spreadsheet, then promote it with helpful free content."
        ),

        "cta": "Follow for more side hustle ideas!"
    },

    {
        "topic": "Freelancing",
        "query": "freelancer laptop home office",

        "hook": "No clients yet? Try this.",

        "body": (
            "Build three small samples for one service, show the results "
            "clearly, and contact potential clients with a short personalized pitch."
        ),

        "cta": "Follow for more freelancing tips!"
    },

    {
        "topic": "Online selling",
        "query": "small business online seller laptop",

        "hook": "Want to sell online with less risk?",

        "body": (
            "Test demand before buying large stock. Start with a small "
            "batch and track your real costs, fees and profit."
        ),

        "cta": "Follow for smarter online business tips!"
    },

    {
        "topic": "Remote work",
        "query": "remote worker laptop home office",

        "hook": "Looking for remote income?",

        "body": (
            "Focus on a skill employers already pay for, build proof "
            "of your work, and apply consistently instead of chasing "
            "quick-money promises."
        ),

        "cta": "Follow for realistic earning ideas!"
    },

    {
        "topic": "Print on demand",
        "query": "designer laptop graphic design",

        "hook": "Want to try print on demand?",

        "body": (
            "Create original designs for a specific audience, test "
            "different ideas, and track which products actually sell."
        ),

        "cta": "Follow for more online business tips!"
    },

    {
        "topic": "Online courses",
        "query": "online teacher laptop course",

        "hook": "Know something people want to learn?",

        "body": (
            "Turn your knowledge into a focused mini course, "
            "template or guide that solves one clear problem."
        ),

        "cta": "Follow for more digital income ideas!"
    },

    {
        "topic": "AI tools",
        "query": "AI technology laptop workspace",

        "hook": "Don't just use AI. Learn a workflow.",

        "body": (
            "Find repetitive work businesses already pay for, "
            "use AI to speed it up, and offer the finished service."
        ),

        "cta": "Follow for practical AI business tips!"
    },

    {
        "topic": "Side hustle",
        "query": "young entrepreneur laptop home office",

        "hook": "Want to start a side hustle?",

        "body": (
            "Start with one skill you can improve quickly, "
            "solve a real problem, and reinvest your first earnings "
            "into improving the service."
        ),

        "cta": "Follow for realistic side hustle ideas!"
    }

]


# ============================================================
# COMMAND RUNNER
# ============================================================

def run_cmd(command):

    print(
        "RUN:",
        " ".join(str(x) for x in command)
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        print(result.stdout)
        print(result.stderr)

        raise RuntimeError(
            f"Command failed with exit code "
            f"{result.returncode}"
        )

    return result.stdout.strip()


# ============================================================
# GET MEDIA DURATION
# ============================================================

def get_duration(file_path):

    output = run_cmd([

        "ffprobe",
        "-v",
        "error",

        "-show_entries",
        "format=duration",

        "-of",
        "default=noprint_wrappers=1:nokey=1",

        str(file_path)

    ])

    return float(output)


# ============================================================
# DOWNLOAD FILE
# ============================================================

def download_file(
    url,
    destination,
    headers=None
):

    print(
        f"Downloading: {url}"
    )

    response = requests.get(

        url,

        headers=headers or {},

        timeout=180,

        allow_redirects=True

    )

    response.raise_for_status()

    destination.write_bytes(
        response.content
    )

    if destination.stat().st_size < 1000:

        raise RuntimeError(
            f"Downloaded file is unexpectedly small: "
            f"{destination}"
        )

    return destination


# ============================================================
# PEXELS VIDEO SEARCH
# ============================================================

def search_pexels_video(query):

    if not PEXELS_API_KEY:

        raise RuntimeError(
            "PEXELS_API_KEY GitHub Secret is missing."
        )

    response = requests.get(

        "https://api.pexels.com/v1/videos/search",

        headers={
            "Authorization": PEXELS_API_KEY
        },

        params={

            "query": query,

            "orientation": "portrait",

            "size": "medium",

            "per_page": 20

        },

        timeout=60

    )

    response.raise_for_status()

    videos = response.json().get(
        "videos",
        []
    )

    if not videos:

        raise RuntimeError(
            f"No Pexels video found for: {query}"
        )


    usable = []


    for video in videos:

        for video_file in video.get(
            "video_files",
            []
        ):

            link = video_file.get(
                "link"
            )

            width = (
                video_file.get("width")
                or 0
            )

            height = (
                video_file.get("height")
                or 0
            )


            if (

                link

                and height >= width

                and height >= 720

            ):

                usable.append({

                    "url": link,

                    "width": width,

                    "height": height

                })


    # --------------------------------------------------------
    # Fallback if portrait footage isn't available
    # --------------------------------------------------------

    if not usable:

        for video in videos:

            for video_file in video.get(
                "video_files",
                []
            ):

                link = video_file.get(
                    "link"
                )

                if link:

                    usable.append({

                        "url": link,

                        "width": (
                            video_file.get(
                                "width"
                            )
                            or 1080
                        ),

                        "height": (
                            video_file.get(
                                "height"
                            )
                            or 1920
                        )

                    })


    if not usable:

        raise RuntimeError(
            f"No usable Pexels video found for: {query}"
        )


    return random.choice(
        usable
    )


# ============================================================
# DOWNLOAD PEXELS CLIP
# ============================================================

def download_pexels_clip(
    query,
    destination
):

    selected = search_pexels_video(
        query
    )

    download_file(
        selected["url"],
        destination
    )


# ============================================================
# AI VOICE
# ============================================================

async def generate_voice_async(
    text,
    output_file
):

    communicate = edge_tts.Communicate(

        text,

        VOICE,

        rate=VOICE_RATE

    )

    await communicate.save(
        str(output_file)
    )


def generate_voice(
    text,
    output_file
):

    asyncio.run(

        generate_voice_async(
            text,
            output_file
        )

    )


# ============================================================
# FONT
# ============================================================

def get_font(size):

    candidates = [

        FONT_DIR / "NotoSans-Regular.ttf",

        FONT_DIR / "NotoSans-Bold.ttf",

        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        )

    ]


    for font_path in candidates:

        if font_path.exists():

            return ImageFont.truetype(

                str(font_path),

                size

            )


    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(
    text,
    font,
    max_width
):

    dummy = Image.new(
        "RGB",
        (10, 10)
    )

    draw = ImageDraw.Draw(
        dummy
    )

    words = text.split()

    lines = []

    current = ""


    for word in words:

        test = (

            word

            if not current

            else current + " " + word

        )


        box = draw.textbbox(

            (0, 0),

            test,

            font=font

        )


        width = (
            box[2] - box[0]
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
# CREATE TEXT OVERLAY
# ============================================================

def create_overlay(

    title,

    body,

    badge,

    output_file

):

    image = Image.new(

        "RGBA",

        (
            VIDEO_WIDTH,
            VIDEO_HEIGHT
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


    title_font = get_font(
        72
    )

    body_font = get_font(
        42
    )

    badge_font = get_font(
        28
    )


    # --------------------------------------------------------
    # Main glass-style panel
    # --------------------------------------------------------

    draw.rounded_rectangle(

        (
            55,
            520,
            1025,
            1435
        ),

        radius=55,

        fill=(
            0,
            0,
            0,
            165
        )

    )


    # --------------------------------------------------------
    # Top badge
    # --------------------------------------------------------

    draw.rounded_rectangle(

        (
            95,
            575,
            455,
            655
        ),

        radius=30,

        fill=(
            255,
            255,
            255,
            235
        )

    )


    draw.text(

        (
            275,
            615
        ),

        badge.upper(),

        font=badge_font,

        fill=(
            20,
            20,
            20
        ),

        anchor="mm"

    )


    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title_lines = wrap_text(

        title,

        title_font,

        820

    )


    y = 745


    for line in title_lines[:3]:

        draw.text(

            (
                540,
                y
            ),

            line,

            font=title_font,

            fill="white",

            anchor="mm",

            stroke_width=3,

            stroke_fill=(
                0,
                0,
                0,
                190
            )

        )

        y += 95


    # --------------------------------------------------------
    # Body
    # --------------------------------------------------------

    body_lines = wrap_text(

        body,

        body_font,

        800

    )


    y += 45


    for line in body_lines[:7]:

        draw.text(

            (
                540,
                y
            ),

            line,

            font=body_font,

            fill=(
                240,
                240,
                240
            ),

            anchor="mm"

        )

        y += 58


    # --------------------------------------------------------
    # Bottom progress bar
    # --------------------------------------------------------

    draw.rounded_rectangle(

        (
            100,
            1540,
            980,
            1556
        ),

        radius=8,

        fill=(
            255,
            255,
            255,
            100
        )

    )


    image.save(
        output_file
    )


# ============================================================
# BACKGROUND VIDEO
# ============================================================

def create_background_video(

    clips,

    duration,

    output_file

):

    segment_duration = (

        duration / len(clips)

    )


    inputs = []

    filters = []


    for i, clip in enumerate(
        clips
    ):

        inputs.extend([

            "-stream_loop",
            "-1",

            "-i",
            str(clip)

        ])


        filters.append(

            f"[{i}:v]"

            f"scale="
            f"{VIDEO_WIDTH}:"
            f"{VIDEO_HEIGHT}:"
            f"force_original_aspect_ratio=increase,"

            f"crop="
            f"{VIDEO_WIDTH}:"
            f"{VIDEO_HEIGHT},"

            f"fps={VIDEO_FPS},"

            f"trim="
            f"duration={segment_duration:.3f},"

            f"setpts=PTS-STARTPTS"

            f"[v{i}]"

        )


    joined = "".join(

        f"[v{i}]"

        for i in range(
            len(clips)
        )

    )


    filters.append(

        f"{joined}"

        f"concat="
        f"n={len(clips)}:"
        f"v=1:"
        f"a=0,"

        f"trim="
        f"duration={duration:.3f},"

        f"setpts=PTS-STARTPTS,"

        f"eq="
        f"brightness=-0.08:"
        f"saturation=1.05,"

        f"vignette"

        f"[v]"

    )


    filter_complex = ";".join(
        filters
    )


    run_cmd([

        "ffmpeg",

        "-y",

        *inputs,

        "-filter_complex",
        filter_complex,

        "-map",
        "[v]",

        "-an",

        "-t",
        str(duration),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        str(output_file)

    ])


# ============================================================
# LIGHT BACKGROUND MUSIC
# ============================================================

def create_music(

    output_file,

    duration

):

    fade_start = max(

        0,

        duration - 1

    )


    # Very light original synthetic background
    audio_filter = (

        "sine="
        "frequency=196:"
        f"duration={duration}"
        "[a];"

        "sine="
        "frequency=246.94:"
        f"duration={duration}"
        "[b];"

        "[a][b]"

        "amix="
        "inputs=2,"

        "volume=0.22,"

        "afade="
        "t=in:"
        "st=0:"
        "d=1,"

        "afade="
        "t=out:"
        f"st={fade_start}:"
        "d=1"

    )


    run_cmd([

        "ffmpeg",

        "-y",

        "-f",
        "lavfi",

        "-i",
        audio_filter,

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        str(output_file)

    ])


# ============================================================
# FINAL VIDEO
# ============================================================

def create_final_video(

    background,

    voice,

    music,

    overlays,

    duration,

    output_file

):

    inputs = [

        "-i",
        str(background),

        "-i",
        str(voice),

        "-i",
        str(music)

    ]


    filters = []

    current_video = "[0:v]"


    for i, overlay in enumerate(
        overlays
    ):

        input_index = i + 3


        inputs.extend([

            "-loop",
            "1",

            "-i",
            str(
                overlay["file"]
            )

        ])


        next_video = (
            f"[v{i}]"
        )


        filters.append(

            f"{current_video}"

            f"[{input_index}:v]"

            f"overlay=0:0:"

            f"enable='between("
            f"t,"
            f"{overlay['start']:.3f},"
            f"{overlay['end']:.3f}"
            f")'"

            f"{next_video}"

        )


        current_video = next_video


    # Voice
    filters.append(

        "[1:a]"

        "volume=1.0"

        "[voice]"

    )


    # Music
    filters.append(

        "[2:a]"

        f"volume={MUSIC_VOLUME}"

        "[music]"

    )


    # Mix
    filters.append(

        "[voice][music]"

        "amix="
        "inputs=2:"
        "duration=first:"
        "dropout_transition=0"

        "[audio]"

    )


    filter_complex = ";".join(
        filters
    )


    run_cmd([

        "ffmpeg",

        "-y",

        *inputs,

        "-filter_complex",
        filter_complex,

        "-map",
        current_video,

        "-map",
        "[audio]",

        "-t",
        str(duration),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-movflags",
        "+faststart",

        str(output_file)

    ])


# ============================================================
# YOUTUBE METADATA
# ============================================================

def create_metadata(

    index,

    item,

    duration

):

    title = (

        f"{item['topic']} | "
        f"Practical Online Earning Tip #Shorts"

    )


    description = (

        f"{item['hook']}\n\n"

        f"{item['body']}\n\n"

        f"{item['cta']}\n\n"

        "This video provides general educational "
        "information about online earning. Results "
        "vary depending on skills, effort, market "
        "demand, platform rules and eligibility. "
        "No income is guaranteed.\n\n"

        "Visuals: Pexels.\n"

        "Background audio: original generated audio.\n\n"

        "#OnlineEarning "
        "#MakeMoneyOnline "
        "#SideHustle "
        "#AffiliateMarketing "
        "#Freelancing "
        "#AITools "
        "#YouTubeShorts "
        "#Shorts"

    )


    metadata_file = (

        OUTPUT_DIR
        / f"metadata_{index}.txt"

    )


    metadata_file.write_text(

        f"TITLE:\n"
        f"{title}\n\n"

        f"DESCRIPTION:\n"
        f"{description}\n",

        encoding="utf-8"

    )


# ============================================================
# CREATE ONE SHORT
# ============================================================

def create_short(

    index,

    item

):

    print()
    print("=" * 70)

    print(

        f"CREATING ONLINE EARNING SHORT {index}"

    )

    print("=" * 70)


    # --------------------------------------------------------
    # Complete voice script
    # --------------------------------------------------------

    voice_text = (

        f"{item['hook']} "

        f"{item['body']} "

        f"{item['cta']}"

    )


    voice_file = (

        TEMP_DIR
        / f"voice_{index}.mp3"

    )


    generate_voice(

        voice_text,

        voice_file

    )


    voice_duration = get_duration(
        voice_file
    )


    # --------------------------------------------------------
    # Keep video around 15 seconds.
    #
    # If voice is slightly longer than 15 seconds,
    # use the actual voice duration so speech isn't cut.
    # --------------------------------------------------------

    duration = min(

        16.0,

        max(

            12.0,

            voice_duration + 0.25

        )

    )


    print(

        f"Voice duration: "
        f"{voice_duration:.2f}s"

    )

    print(

        f"Video duration: "
        f"{duration:.2f}s"

    )


    # --------------------------------------------------------
    # Download two different background clips
    # --------------------------------------------------------

    clip1 = (

        TEMP_DIR
        / f"clip_{index}_1.mp4"

    )

    clip2 = (

        TEMP_DIR
        / f"clip_{index}_2.mp4"

    )


    download_pexels_clip(

        item["query"],

        clip1

    )


    download_pexels_clip(

        item["query"],

        clip2

    )


    # --------------------------------------------------------
    # Create background
    # --------------------------------------------------------

    background = (

        TEMP_DIR
        / f"background_{index}.mp4"

    )


    create_background_video(

        [
            clip1,
            clip2
        ],

        duration,

        background

    )


    # --------------------------------------------------------
    # Create light music
    # --------------------------------------------------------

    music = (

        TEMP_DIR
        / f"music_{index}.m4a"

    )


    create_music(

        music,

        duration

    )


    # --------------------------------------------------------
    # Create text overlays
    # --------------------------------------------------------

    hook_image = (

        TEMP_DIR
        / f"hook_{index}.png"

    )

    body_image = (

        TEMP_DIR
        / f"body_{index}.png"

    )

    cta_image = (

        TEMP_DIR
        / f"cta_{index}.png"

    )


    # Hook
    create_overlay(

        item["hook"],

        "Watch for one practical step.",

        "ONLINE EARNING",

        hook_image

    )


    # Main tip
    create_overlay(

        "The practical step",

        item["body"],

        "TIP",

        body_image

    )


    # CTA
    create_overlay(

        "Build skills. Stay consistent.",

        item["cta"],

        "FOLLOW",

        cta_image

    )


    # --------------------------------------------------------
    # Overlay timing
    # --------------------------------------------------------

    hook_end = min(

        2.5,

        duration * 0.22

    )


    body_end = min(

        10.8,

        duration * 0.78

    )


    overlays = [

        {

            "file": hook_image,

            "start": 0.0,

            "end": hook_end

        },

        {

            "file": body_image,

            "start": hook_end,

            "end": body_end

        },

        {

            "file": cta_image,

            "start": body_end,

            "end": duration

        }

    ]


    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    output_file = (

        OUTPUT_DIR
        / f"online_earning_short_{index}.mp4"

    )


    create_final_video(

        background,

        voice_file,

        music,

        overlays,

        duration,

        output_file

    )


    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    create_metadata(

        index,

        item,

        duration

    )


    print()
    print(

        f"SUCCESS: {output_file}"

    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)

    print(
        "ONLINE EARNING SHORTS GENERATOR"
    )

    print(
        "3 VIDEOS PER RUN"
    )

    print(
        "FACELESS YOUTUBE SHORTS"
    )

    print("=" * 70)


    # --------------------------------------------------------
    # Check Pexels
    # --------------------------------------------------------

    if not PEXELS_API_KEY:

        raise RuntimeError(

            "PEXELS_API_KEY GitHub Secret "
            "is missing."

        )


    # --------------------------------------------------------
    # Select exactly 3 DIFFERENT topics
    # --------------------------------------------------------

    selected_topics = random.sample(

        TOPICS,

        SHORT_COUNT

    )


    print()
    print(
        "Selected topics:"
    )


    for index, item in enumerate(

        selected_topics,

        start=1

    ):

        print(

            f"{index}. "
            f"{item['topic']}"

        )


    print()


    # --------------------------------------------------------
    # Generate exactly 3 videos
    # --------------------------------------------------------

    for index, item in enumerate(

        selected_topics,

        start=1

    ):

        create_short(

            index,

            item

        )


    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    print()
    print("=" * 70)

    print(
        "ALL 3 ONLINE EARNING SHORTS "
        "CREATED SUCCESSFULLY"
    )

    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
