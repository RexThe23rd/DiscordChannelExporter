PROBOT_NAME = "probot"

MOVEMENT_COMMANDS = (
    "!caminar",
    "!caballo",
)


def classify_message(message):
    author_type = message.get("author_type")

    if author_type == "tupper":
        return "rp"

    if author_type == "user":
        return "ooc"

    if author_type == "bot":
        author = message.get("discord_author", "").lower()

        if PROBOT_NAME in author:
            content = message.get("content", "").lower()

            if content.startswith(MOVEMENT_COMMANDS):
                return "movement"

        return "bot"

    if author_type == "system":
        return "system"

    return "unknown"


def filter_messages(messages, classification):
    return [
        message
        for message in messages
        if classify_message(message) == classification
    ]


def collect_messages(export_data):
    """Collect messages from categories, references, and forum posts."""

    collected = []

    def add_channel(channel, category_name=None):
        # Regular text-channel messages.
        for message in channel.get("messages", []):
            entry = message.copy()
            entry["category"] = category_name
            entry["channel"] = channel.get("name")
            entry["classification"] = classify_message(entry)
            collected.append(entry)

        # Messages inside forum posts.
        for post in channel.get("posts", []):
            for message in post.get("messages", []):
                entry = message.copy()
                entry["category"] = category_name
                entry["channel"] = channel.get("name")
                entry["post"] = post.get("name")
                entry["classification"] = classify_message(entry)
                collected.append(entry)

    for category in export_data.get("categories", []):
        for channel in category.get("channels", []):
            add_channel(channel, category.get("name"))

    for channel in export_data.get("uncategorized_channels", []):
        add_channel(channel)

    return collected
