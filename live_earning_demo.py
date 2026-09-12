import asyncio
import json
import math
import os
import random
import shutil
import subprocess
import wave
from pathlib import Path

import edge_tts
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parent

TOPICS_FILE = ROOT / "earning_topics.json"
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "work"

VIDEO_DIR = WORK_DIR / "browser_videos"
AUDIO_DIR = WORK_DIR / "audio"

WIDTH = 1080
HEIGHT = 1920

FPS = 30

VOICE = "en-US-GuyNeural"

VIDEO_COUNT = 3

random.seed()


# ============================================================
# DIRECTORIES
# ============================================================

def prepare_directories():

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)

    OUTPUT_DIR.mkdir(parents=True)
    VIDEO_DIR.mkdir(parents=True)
    AUDIO_DIR.mkdir(parents=True)


# ============================================================
# LOAD TOPICS
# ============================================================

def load_topics():

    with open(
        TOPICS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# FFPROBE
# ============================================================

def get_duration(file):

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file)
        ],
        capture_output=True,
        text=True
    )

    try:
        return float(
            result.stdout.strip()
        )
    except Exception:
        return 1.0


# ============================================================
# TEXT TO SPEECH
# ============================================================

async def make_voice(
    text,
    output_file
):

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate="+3%",
        pitch="+1Hz"
    )

    await communicate.save(
        str(output_file)
    )


# ============================================================
# CREATE AUDIO SEGMENTS
# ============================================================

async def create_audio_segments(
    topic,
    number
):

    segments = []

    intro = (
        topic["hook"]
    )

    segments.append(
        (
            "intro",
            intro
        )
    )

    segments.append(
        (
            "start",
            "First, open the website shown on screen."
        )
    )

    for index, step in enumerate(
        topic["earning_steps"],
        start=1
    ):

        segments.append(
            (
                f"earning_{index}",
                f"Step {index}. {step}"
            )
        )

    segments.append(
        (
            "verification",
            topic["verification_note"]
        )
    )

    segments.append(
        (
            "demo",
            "The information shown during this tutorial is demonstration information. "
            "For a real account, use your own details and the real verification code "
            "sent by the platform."
        )
    )

    segments.append(
        (
            "target",
            "Five hundred dollars a month is an example target, not a guaranteed income."
        )
    )

    segments.append(
        (
            "final",
            "Your results depend on eligibility, skills, demand, competition and platform rules. "
            "Follow for more practical online earning tutorials."
        )
    )

    generated = []

    for index, (name, text) in enumerate(
        segments
    ):

        audio_file = (
            AUDIO_DIR /
            f"{number}_{index}_{name}.mp3"
        )

        print(
            f"Creating voice: {text}"
        )

        await make_voice(
            text,
            audio_file
        )

        duration = get_duration(
            audio_file
        )

        generated.append(
            {
                "name": name,
                "text": text,
                "file": str(audio_file),
                "duration": duration
            }
        )

    return generated


# ============================================================
# CREATE AMBIENT MUSIC
# ============================================================

def create_music(
    duration,
    output_file
):

    sample_rate = 44100

    total_samples = int(
        duration *
        sample_rate
    )

    frequencies = [
        220.0,
        277.18,
        329.63
    ]

    with wave.open(
        str(output_file),
        "w"
    ) as wav:

        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(
            sample_rate
        )

        for i in range(
            total_samples
        ):

            t = (
                i /
                sample_rate
            )

            # Slow ambient movement
            modulation = (
                0.5 +
                0.5 *
                math.sin(
                    2 *
                    math.pi *
                    0.025 *
                    t
                )
            )

            sample = 0.0

            for frequency in frequencies:

                sample += math.sin(
                    2 *
                    math.pi *
                    frequency *
                    t
                )

            sample /= len(
                frequencies
            )

            sample *= (
                0.035 *
                modulation
            )

            value = int(
                max(
                    -1,
                    min(
                        1,
                        sample
                    )
                ) *
                32767
            )

            wav.writeframesraw(
                value.to_bytes(
                    2,
                    byteorder="little",
                    signed=True
                ) * 2
            )


# ============================================================
# PLAYWRIGHT OVERLAY
# ============================================================

OVERLAY_SCRIPT = r"""
(() => {

    if (window.__earning_overlay_installed)
        return;

    window.__earning_overlay_installed = true;

    const style = document.createElement("style");

    style.innerHTML = `

        #earning-top {

            position: fixed;

            top: 25px;
            left: 25px;
            right: 25px;

            z-index: 2147483647;

            background:
                rgba(0,0,0,0.82);

            color: white;

            border-radius: 25px;

            padding: 20px 25px;

            font-family:
                Arial,
                sans-serif;

            box-shadow:
                0 8px 30px
                rgba(0,0,0,0.35);

        }

        #earning-brand {

            font-size: 22px;

            font-weight: 800;

            letter-spacing: 1px;

            color: #8fe3ff;

            margin-bottom: 8px;

        }

        #earning-step {

            font-size: 30px;

            font-weight: 800;

            line-height: 1.15;

        }

        #earning-instruction {

            margin-top: 8px;

            font-size: 20px;

            line-height: 1.25;

            opacity: 0.95;

        }

        #earning-demo {

            position: fixed;

            bottom: 35px;
            left: 35px;

            z-index: 2147483647;

            background:
                rgba(170, 20, 20, 0.94);

            color: white;

            font-family:
                Arial,
                sans-serif;

            font-weight: 900;

            font-size: 18px;

            padding: 12px 18px;

            border-radius: 15px;

            letter-spacing: 1px;

            box-shadow:
                0 5px 20px
                rgba(0,0,0,0.35);

        }

        #earning-cursor {

            position: fixed;

            width: 34px;
            height: 34px;

            border-radius: 50%;

            background:
                rgba(255, 40, 40, 0.78);

            border:
                4px solid white;

            box-shadow:
                0 0 0 6px
                rgba(255,40,40,0.22);

            z-index: 2147483646;

            pointer-events: none;

            transform:
                translate(-50%, -50%);

            transition:
                left 0.35s ease,
                top 0.35s ease;

        }

        #earning-click {

            position: fixed;

            width: 70px;
            height: 70px;

            border-radius: 50%;

            border:
                5px solid white;

            z-index: 2147483645;

            pointer-events: none;

            transform:
                translate(-50%, -50%)
                scale(0.2);

            opacity: 0;

        }

    `;

    document.head.appendChild(style);

    const top = document.createElement("div");

    top.id = "earning-top";

    top.innerHTML = `

        <div id="earning-brand">
            ONLINE EARNING • LIVE DEMO
        </div>

        <div id="earning-step">
            GETTING STARTED
        </div>

        <div id="earning-instruction">
            Real website • demonstration data
        </div>

    `;

    document.body.appendChild(top);

    const demo = document.createElement("div");

    demo.id = "earning-demo";

    demo.innerText =
        "DEMO DATA — NOT A REAL ACCOUNT";

    document.body.appendChild(demo);

    const cursor = document.createElement("div");

    cursor.id = "earning-cursor";

    document.body.appendChild(cursor);

    const click = document.createElement("div");

    click.id = "earning-click";

    document.body.appendChild(click);

})();
"""


# ============================================================
# UPDATE OVERLAY
# ============================================================

async def update_overlay(
    page,
    step,
    instruction
):

    try:

        await page.evaluate(
            """
            ([step, instruction]) => {

                const s =
                    document.getElementById(
                        "earning-step"
                    );

                const i =
                    document.getElementById(
                        "earning-instruction"
                    );

                if (s)
                    s.innerText = step;

                if (i)
                    i.innerText = instruction;

            }
            """,
            [step, instruction]
        )

    except Exception:
        pass


# ============================================================
# MOVE DEMO CURSOR
# ============================================================

async def move_cursor(
    page,
    locator
):

    try:

        box = await locator.bounding_box()

        if not box:
            return False

        x = (
            box["x"] +
            box["width"] /
            2
        )

        y = (
            box["y"] +
            box["height"] /
            2
        )

        await page.evaluate(
            """
            ([x,y]) => {

                const cursor =
                    document.getElementById(
                        "earning-cursor"
                    );

                if (cursor) {

                    cursor.style.left =
                        x + "px";

                    cursor.style.top =
                        y + "px";
                }

            }
            """,
            [x, y]
        )

        await page.mouse.move(
            x,
            y,
            steps=12
        )

        await page.wait_for_timeout(
            600
        )

        return True

    except Exception:

        return False


# ============================================================
# CLICK ANIMATION
# ============================================================

async def click_demo(
    page,
    locator
):

    try:

        await move_cursor(
            page,
            locator
        )

        box = await locator.bounding_box()

        if box:

            x = (
                box["x"] +
                box["width"] /
                2
            )

            y = (
                box["y"] +
                box["height"] /
                2
            )

            await page.evaluate(
                """
                ([x,y]) => {

                    const c =
                        document.getElementById(
                            "earning-click"
                        );

                    if (!c)
                        return;

                    c.style.left =
                        x + "px";

                    c.style.top =
                        y + "px";

                    c.style.opacity =
                        "1";

                    c.style.transform =
                        "translate(-50%, -50%) scale(1)";

                    setTimeout(() => {

                        c.style.opacity =
                            "0";

                        c.style.transform =
                            "translate(-50%, -50%) scale(0.2)";

                    }, 350);

                }
                """,
                [x, y]
            )

        await locator.click(
            timeout=5000
        )

        await page.wait_for_timeout(
            1200
        )

        return True

    except Exception:

        return False


# ============================================================
# FIND FIRST WORKING SELECTOR
# ============================================================

async def find_locator(
    page,
    selectors
):

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            ).first

            if await locator.count() > 0:

                if await locator.is_visible(
                    timeout=1000
                ):

                    return locator

        except Exception:
            continue

    return None


# ============================================================
# SAFE FILL
# ============================================================

async def fill_demo(
    page,
    selectors,
    value
):

    locator = await find_locator(
        page,
        selectors
    )

    if not locator:
        return False

    try:

        await move_cursor(
            page,
            locator
        )

        await locator.click()

        await locator.fill(
            value
        )

        await page.wait_for_timeout(
            700
        )

        return True

    except Exception:

        return False


# ============================================================
# DEMO SIGNUP
# ============================================================

async def perform_signup_demo(
    page,
    topic,
    audio_segments
):

    selectors = topic.get(
        "selectors",
        {}
    )

    demo = topic.get(
        "demo",
        {}
    )

    # ----------------------------------------
    # Open signup website
    # ----------------------------------------

    await update_overlay(
        page,
        "STEP 1 • OPEN THE WEBSITE",
        "Real website • demonstration mode"
    )

    await page.wait_for_timeout(
        1500
    )

    # ----------------------------------------
    # Find signup/create button
    # ----------------------------------------

    create_selectors = (
        selectors.get(
            "create_account",
            []
        )
        +
        selectors.get(
            "signup",
            []
        )
        +
        selectors.get(
            "join",
            []
        )
        +
        selectors.get(
            "freelancer",
            []
        )
    )

    locator = await find_locator(
        page,
        create_selectors
    )

    if locator:

        await update_overlay(
            page,
            "STEP 2 • CREATE ACCOUNT",
            "Move to the signup button and open the form"
        )

        await click_demo(
            page,
            locator
        )

    else:

        await update_overlay(
            page,
            "STEP 2 • SIGNUP PAGE",
            "The website layout may have changed"
        )

        await page.wait_for_timeout(
            1800
        )

    # ----------------------------------------
    # Email
    # ----------------------------------------

    await update_overlay(
        page,
        "STEP 3 • EMAIL",
        "Put your email here — DEMO DATA ONLY"
    )

    await fill_demo(
        page,
        selectors.get(
            "email",
            []
        ),
        demo.get(
            "email",
            "demo.creator@example.com"
        )
    )

    # ----------------------------------------
    # Password
    # ----------------------------------------

    await update_overlay(
        page,
        "STEP 4 • PASSWORD",
        "Create your own strong password"
    )

    await fill_demo(
        page,
        selectors.get(
            "password",
            []
        ),
        demo.get(
            "password",
            "DemoOnly!7429"
        )
    )

    # ----------------------------------------
    # Name
    # ----------------------------------------

    if selectors.get(
        "first_name"
    ):

        await update_overlay(
            page,
            "STEP 5 • NAME",
            "Enter your real name for a real account"
        )

        await fill_demo(
            page,
            selectors.get(
                "first_name"
            ),
            demo.get(
                "first_name",
                "Alex"
            )
        )

        await fill_demo(
            page,
            selectors.get(
                "last_name"
            ),
            demo.get(
                "last_name",
                "Creator"
            )
        )

    # ----------------------------------------
    # Verification
    # ----------------------------------------

    await update_overlay(
        page,
        "STEP 6 • VERIFICATION",
        "The platform may send a code to your email or phone"
    )

    await page.wait_for_timeout(
        2500
    )

    await update_overlay(
        page,
        "DEMO VERIFICATION",
        "DEMO ONLY • never use a random OTP on a real account"
    )

    await page.wait_for_timeout(
        2200
    )

    # ----------------------------------------
    # Important transition
    # ----------------------------------------

    await update_overlay(
        page,
        "REAL ACCOUNT",
        "For your real account, complete the actual verification yourself"
    )

    await page.wait_for_timeout(
        2200
    )


# ============================================================
# EARNING WALKTHROUGH
# ============================================================

async def earning_walkthrough(
    page,
    topic
):

    for index, step in enumerate(
        topic["earning_steps"],
        start=1
    ):

        await update_overlay(
            page,
            f"STEP {index}",
            step
        )

        await page.wait_for_timeout(
            2200
        )

    await update_overlay(
        page,
        "EXAMPLE TARGET",
        "Example: build toward $500/month — NOT GUARANTEED"
    )

    await page.wait_for_timeout(
        2500
    )

    await update_overlay(
        page,
        "$500 TARGET",
        "5 × $100 = $500 • Example calculation only"
    )

    await page.wait_for_timeout(
        2500
    )

    await update_overlay(
        page,
        "IMPORTANT",
        "Income depends on eligibility, skills, demand and platform rules"
    )

    await page.wait_for_timeout(
        2500
    )


# ============================================================
# RECORD REAL WEBSITE
# ============================================================

async def record_topic(
    topic,
    number,
    audio_segments
):

    browser_video_dir = (
        VIDEO_DIR /
        f"video_{number}"
    )

    browser_video_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox"
            ]
        )

        context = await browser.new_context(

            viewport={
                "width": WIDTH,
                "height": HEIGHT
            },

            screen={
                "width": WIDTH,
                "height": HEIGHT
            },

            record_video_dir=
                str(browser_video_dir),

            record_video_size={
                "width": WIDTH,
                "height": HEIGHT
            },

            locale="en-US",

            timezone_id="Asia/Dubai"
        )

        page = await context.new_page()

        await page.add_init_script(
            OVERLAY_SCRIPT
        )

        print(
            f"Opening real website: "
            f"{topic['signup_url']}"
        )

        try:

            await page.goto(
                topic["signup_url"],
                wait_until="domcontentloaded",
                timeout=60000
            )

        except Exception as e:

            print(
                f"Website navigation warning: {e}"
            )

        await page.wait_for_timeout(
            2500
        )

        # Install overlay after navigation
        try:
            await page.evaluate(
                OVERLAY_SCRIPT
            )
        except Exception:
            pass

        # ------------------------------------
        # Start tutorial
        # ------------------------------------

        await perform_signup_demo(
            page,
            topic,
            audio_segments
        )

        await earning_walkthrough(
            page,
            topic
        )

        # ------------------------------------
        # Final screen
        # ------------------------------------

        await update_overlay(
            page,
            "FOLLOW FOR MORE",
            "Practical online earning tutorials every day"
        )

        await page.wait_for_timeout(
            2500
        )

        # ------------------------------------
        # Close context so video is saved
        # ------------------------------------

        await context.close()

        await browser.close()

    videos = list(
        browser_video_dir.glob(
            "*.webm"
        )
    )

    if not videos:

        raise RuntimeError(
            "Playwright did not create a browser recording."
        )

    return videos[0]


# ============================================================
# CONCAT AUDIO
# ============================================================

def concat_audio(
    segments,
    output_file
):

    concat_file = (
        AUDIO_DIR /
        "audio_concat.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for segment in segments:

            file.write(
                "file '"
                +
                str(
                    Path(
                        segment["file"]
                    ).resolve()
                )
                .replace(
                    "'",
                    "'\\''"
                )
                +
                "'\n"
            )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(output_file)
        ],
        check=True
    )


# ============================================================
# FINAL VIDEO
# ============================================================

def make_final_video(
    browser_video,
    narration,
    music,
    output
):

    filter_complex = (
        "[2:a]"
        "volume=0.08"
        "[music];"
        "[1:a]"
        "volume=1.0"
        "[voice];"
        "[voice][music]"
        "amix=inputs=2:"
        "duration=first:"
        "dropout_transition=2"
        "[audio]"
    )

    command = [
        "ffmpeg",
        "-y",

        "-i",
        str(browser_video),

        "-i",
        str(narration),

        "-i",
        str(music),

        "-filter_complex",
        filter_complex,

        "-map",
        "0:v:0",
        "-map",
        "[audio]",

        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:"
            "(ow-iw)/2:"
            "(oh-ih)/2:"
            "black"
        ),

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

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


# ============================================================
# METADATA
# ============================================================

def create_metadata(
    topic,
    number
):

    title_options = [

        f"How to Start {topic['name']} Step by Step",

        f"{topic['name']} Beginner Guide",

        f"How to Build Toward $500/Month with {topic['name']}",

        f"{topic['name']} Account to Earning Guide",

        f"Start {topic['name']} the Right Way"
    ]

    title = random.choice(
        title_options
    )

    description = f"""
{topic['name']} — complete beginner walkthrough.

This tutorial demonstrates the real website interface using demonstration information.

Website:
{topic['website']}

Official information:
{topic['official_source']}

IMPORTANT:
The $500/month figure is an example target and is NOT a guaranteed income.

Actual results depend on eligibility, skills, demand, competition, platform rules and other factors.

Verification:
Never use a random OTP on a real account. Use the actual verification code sent to your own email or phone.

#OnlineEarning
#MakeMoneyOnline
#SideHustle
#EarnOnline
#MoneyTips
#Shorts
""".strip()

    metadata_file = (
        OUTPUT_DIR /
        f"short_{number}_metadata.txt"
    )

    metadata_file.write_text(
        f"TITLE:\n{title}\n\n"
        f"DESCRIPTION:\n{description}\n\n"
        f"WEBSITE:\n{topic['website']}\n\n"
        f"SOURCE:\n{topic['official_source']}\n",
        encoding="utf-8"
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "=" * 70
    )

    print(
        "LIVE WEBSITE ONLINE EARNING SHORTS"
    )

    print(
        "=" * 70
    )

    prepare_directories()

    topics = load_topics()

    if len(topics) < VIDEO_COUNT:

        raise RuntimeError(
            "earning_topics.json must contain at least 3 topics."
        )

    selected = random.sample(
        topics,
        VIDEO_COUNT
    )

    for number, topic in enumerate(
        selected,
        start=1
    ):

        print()
        print(
            f"VIDEO {number}: "
            f"{topic['name']}"
        )

        # ------------------------------------
        # Voice
        # ------------------------------------

        audio_segments = (
            await create_audio_segments(
                topic,
                number
            )
        )

        narration = (
            AUDIO_DIR /
            f"narration_{number}.mp3"
        )

        concat_audio(
            audio_segments,
            narration
        )

        # ------------------------------------
        # Music
        # ------------------------------------

        narration_duration = (
            get_duration(
                narration
            )
        )

        music = (
            AUDIO_DIR /
            f"music_{number}.wav"
        )

        create_music(
            narration_duration + 3,
            music
        )

        # ------------------------------------
        # Browser
        # ------------------------------------

        browser_video = (
            await record_topic(
                topic,
                number,
                audio_segments
            )
        )

        # ------------------------------------
        # Final MP4
        # ------------------------------------

        final_video = (
            OUTPUT_DIR /
            f"online_earning_short_{number}.mp4"
        )

        print(
            "Creating final MP4..."
        )

        make_final_video(
            browser_video,
            narration,
            music,
            final_video
        )

        create_metadata(
            topic,
            number
        )

        print(
            f"COMPLETE: {final_video}"
        )

    print()
    print(
        "=" * 70
    )

    print(
        "3 LIVE WEBSITE SHORTS CREATED"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
