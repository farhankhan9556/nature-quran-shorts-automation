from datetime import date

TODAY = date.today()

topics = [
    {
        "nature": "mountain sunrise",
        "search": "mountain sunrise landscape",
        "theme": "The beauty of Allah's creation"
    },
    {
        "nature": "ocean waves",
        "search": "ocean waves beautiful nature",
        "theme": "The vastness of Allah's creation"
    },
    {
        "nature": "forest",
        "search": "beautiful green forest sunlight",
        "theme": "The signs of creation"
    },
    {
        "nature": "waterfall",
        "search": "beautiful waterfall nature",
        "theme": "The beauty of nature"
    },
    {
        "nature": "desert",
        "search": "beautiful desert landscape sunset",
        "theme": "Reflection and creation"
    },
    {
        "nature": "snow mountains",
        "search": "snow mountains cinematic landscape",
        "theme": "The majesty of creation"
    },
    {
        "nature": "lake",
        "search": "beautiful lake mountains nature",
        "theme": "Peace and reflection"
    },
    {
        "nature": "ocean sunset",
        "search": "ocean sunset cinematic",
        "theme": "Reflection on creation"
    },
    {
        "nature": "rain forest",
        "search": "rainforest beautiful nature",
        "theme": "Life and creation"
    },
    {
        "nature": "night sky",
        "search": "stars night sky mountains",
        "theme": "The vastness of creation"
    },
    {
        "nature": "river",
        "search": "beautiful river nature mountains",
        "theme": "The blessings of nature"
    },
    {
        "nature": "cliffs",
        "search": "dramatic cliffs ocean landscape",
        "theme": "The power of creation"
    }
]


# 3 different topics every day
start = TODAY.toordinal() % len(topics)

selected = [
    topics[start % len(topics)],
    topics[(start + 1) % len(topics)],
    topics[(start + 2) % len(topics)]
]


print("================================")
print("NATURE + QURAN DAILY CONTENT")
print("================================")

print(f"Date: {TODAY}")
print()

for number, topic in enumerate(selected, start=1):

    print(f"SHORT {number}")
    print(f"Nature: {topic['nature']}")
    print(f"Search: {topic['search']}")
    print(f"Theme: {topic['theme']}")
    print()
