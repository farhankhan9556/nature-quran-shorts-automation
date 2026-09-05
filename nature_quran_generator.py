import os
import random
import requests
from pathlib import Path
from datetime import date

API_KEY = os.environ.get("PEXELS_API_KEY")

if not API_KEY:
    raise RuntimeError("PEXELS_API_KEY is missing")

OUT = Path("assets")
OUT.mkdir(parents=True, exist_ok=True)

TODAY = date.today()

topics = [
    {
        "nature": "mountain sunrise",
        "search": "mountain sunrise landscape"
    },
    {
        "nature": "ocean waves",
        "search": "ocean waves beautiful nature"
    },
    {
        "nature": "forest",
        "search": "beautiful green forest sunlight"
    },
    {
        "nature": "waterfall",
        "search": "beautiful waterfall nature"
    },
    {
        "nature": "desert",
        "search": "beautiful desert landscape sunset"
    },
    {
        "nature": "snow mountains",
        "search": "snow mountains cinematic landscape"
    },
    {
        "nature": "lake",
        "search": "beautiful lake mountains nature"
    },
    {
        "nature": "ocean sunset",
        "search": "ocean sunset cinematic"
    },
    {
        "nature": "rain forest",
        "search": "rainforest beautiful nature"
    },
    {
        "nature": "night sky",
        "search": "stars night sky mountains"
    },
    {
        "nature": "river",
        "search": "beautiful river nature mountains"
    },
    {
        "nature": "cliffs",
        "search": "dramatic cliffs ocean landscape"
    }
]

# Select 3 different topics each day
start = TODAY.toordinal() % len(topics)

selected = [
    topics[start % len(topics)],
    topics[(start + 1) % len(topics)],
    topics[(start + 2) % len(topics)]
]

headers = {
    "Authorization": API_KEY
}


def download_video(topic, number):

    print()
    print("=" * 40)
    print(f"SHORT {number}")
    print(f"Topic: {topic['nature']}")
    print("=" * 40)

    response = requests.get(
        "https://api.pexels.com/v1/videos/search",
        headers=headers,
        params={
            "query": topic["search"],
            "orientation": "portrait",
            "size": "large",
            "per_page": 20
        },
        timeout=30
    )

    response.raise_for_status()

    videos = response.json().get("videos", [])

    if not videos:
        raise RuntimeError(
            f"No video found for {topic['search']}"
        )

    # Prefer portrait videos
    portrait_videos = []

    for video in videos:

        files = video.get("video_files", [])

        for file in files:

            width = file.get("width", 0)
            height = file.get("height", 0)

            if height >= width and width > 0:

                portrait_videos.append(
                    (video, file)
                )

    # If portrait videos exist, use them
    if portrait_videos:

        video, selected_file = random.choice(
            portrait_videos
        )

    else:

        # Otherwise use the best available video
        video = random.choice(videos)

        files = video.get("video_files", [])

        files = [
            f for f in files
            if f.get("width", 0) > 0
        ]

        files.sort(
            key=lambda f:
            f.get("width", 0) *
            f.get("height", 0),
            reverse=True
        )

        selected_file = files[0]

    video_url = selected_file["link"]

    output = OUT / f"nature_source_{number}.mp4"

    print("Downloading footage...")

    with requests.get(
        video_url,
        stream=True,
        timeout=120
    ) as r:

        r.raise_for_status()

        with open(output, "wb") as f:

            for chunk in r.iter_content(
                1024 * 1024
            ):

                if chunk:
                    f.write(chunk)

    print(
        f"Downloaded: {output}"
    )

    print(
        f"Resolution: "
        f"{selected_file.get('width')}x"
        f"{selected_file.get('height')}"
    )

    return video, selected_file


# Download 3 videos
downloaded = []

for number, topic in enumerate(
    selected,
    start=1
):

    video, video_file = download_video(
        topic,
        number
    )

    downloaded.append(
        (number, topic, video, video_file)
    )


print()
print("=" * 45)
print("3 NATURE VIDEOS DOWNLOADED SUCCESSFULLY")
print("=" * 45)

for number, topic, video, video_file in downloaded:

    print(
        f"Short {number}: "
        f"{topic['nature']}"
    )

    print(
        f"Resolution: "
        f"{video_file.get('width')}x"
        f"{video_file.get('height')}"
    )

print()
print("Ready for cinematic editing.")
