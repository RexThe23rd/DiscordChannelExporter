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

def group_character_messages(rp_messages, all_messages):
    """Group RP messages by character and connect their replies."""

    characters = {}
    interactions = []
    unassigned = []

    # Create a lookup of every exported message by its ID.
    message_lookup = {
        message["id"]: message
        for message in all_messages
    }

    for message in rp_messages:

        character_name = message.get("character_name")

        # Keep messages without a character name separately.
        if not character_name:
            unassigned.append(message.copy())
            continue

        entry = message.copy()

        # Create the character group if it doesn't exist.
        if character_name not in characters:
            characters[character_name] = []

        # Find the message this character is replying to.
        quoted_reply = message.get("quoted_reply") or {}

        target_id = (
            quoted_reply.get("message_id")
            or message.get("reply_to")
        )

        if target_id:

            target = message_lookup.get(target_id)

            target_character = (
                target.get("character_name")
                if target and target.get("author_type") == "tupper"
                else None
            )

            entry["reply"] = {
                "message_id": target_id,
                "character_name": target_character,
                "found": target is not None,
            }

            interactions.append({
                "from": character_name,
                "to": target_character,
                "message_id": message["id"],
                "target_message_id": target_id,
                "target_found": target is not None,
            })

        else:
            entry["reply"] = None

        characters[character_name].append(entry)

    # Keep each character's messages chronological.
    for messages in characters.values():
        messages.sort(
            key=lambda message: message["timestamp"]
        )

    return {
        "characters": characters,
        "interactions": interactions,
        "unassigned_character_messages": unassigned,
    }
