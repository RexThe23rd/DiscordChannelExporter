from collections import Counter, defaultdict

PROBOT_NAME = "probot"

MOVEMENT_COMMANDS = {
    "!caminar": "walking",
    "!correr": "running",
    "!caballo": "horseback",
}


# -----------------------------------------
# MOVEMENT DETECTION
# -----------------------------------------

def extract_movement_type(message):
    """Identify a movement command, ignoring capitalization."""

    content = message.get("content", "").strip().lower()

    if not content:
        return None

    command = content.split(maxsplit=1)[0]

    return MOVEMENT_COMMANDS.get(command)


def is_movement_command(message):
    """Check whether a message contains a recognized movement command."""

    return (
        message.get("author_type") in ("user", "tupper")
        and extract_movement_type(message) is not None
    )


# -----------------------------------------
# MESSAGE CLASSIFICATION
# -----------------------------------------

def classify_message(message):
    author_type = message.get("author_type")

    if author_type == "tupper":
        return "rp"

    if author_type == "user":
        return "ooc"

    if author_type == "bot":
        return "bot"

    if author_type == "system":
        return "system"

    return "unknown"


def filter_messages(messages, classification):
    """Filter messages using their previously assigned classification."""

    return [
        message
        for message in messages
        if message.get("classification") == classification
    ]


# -----------------------------------------
# TIMESTAMP UTILITIES
# -----------------------------------------

def timestamp_sort_key(message):
    """Sort messages chronologically, placing missing timestamps last."""

    timestamp = message.get("timestamp")

    return (
        timestamp is None or timestamp == "",
        str(timestamp) if timestamp is not None else "",
    )


# -----------------------------------------
# MOVEMENT RESPONSE ASSOCIATION
# -----------------------------------------

def associate_movement_responses(messages):
    """Associate ProBot responses with immediately preceding commands.

    Messages are matched within their own channel or forum post.
    """

    conversations = defaultdict(list)

    # Separate messages into independent conversations.
    for message in messages:

        conversation_key = (
            message.get("channel_id"),
            message.get("post_id"),
        )

        conversations[conversation_key].append(message)

    # Check consecutive messages in each conversation.
    for conversation in conversations.values():

        for index in range(1, len(conversation)):

            previous = conversation[index - 1]
            current = conversation[index]

            # The current message must be from ProBot.
            if current.get("author_type") != "bot":
                continue

            author = current.get("discord_author", "").lower()

            if PROBOT_NAME not in author:
                continue

            # The previous message must contain a movement command.
            movement_type = extract_movement_type(previous)

            if not is_movement_command(previous):
                continue

            # Mark ProBot's response as a movement event.
            current["classification"] = "movement"
            current["movement_type"] = movement_type
            current["command_message_id"] = previous.get("id")

    return messages


# -----------------------------------------
# MESSAGE COLLECTION
# -----------------------------------------

def collect_messages(export_data):
    """Collect messages from categories and uncategorized channels.

    Reference categories are intentionally excluded because they contain
    world lore, systems, rules, and other reference information.
    """

    collected = []

    def add_channel(channel, category_name=None, category_id=None):

        metadata = {
            "category": category_name,
            "category_id": (
                str(category_id) if category_id is not None else None
            ),
            "channel": channel.get("name"),
            "channel_id": channel.get("id"),
            "channel_type": channel.get("type"),
        }

        # Regular text-channel messages.
        for message in channel.get("messages", []):

            entry = message.copy()
            entry.update(metadata)

            entry["classification"] = classify_message(entry)

            collected.append(entry)

        # Messages inside forum posts.
        for post in channel.get("posts", []):

            for message in post.get("messages", []):

                entry = message.copy()
                entry.update(metadata)

                entry["post"] = post.get("name")
                entry["post_id"] = post.get("id")
                entry["post_archived"] = post.get("archived")

                entry["classification"] = classify_message(entry)

                collected.append(entry)

    # Categorized channels.
    for category in export_data.get("categories", []):

        for channel in category.get("channels", []):

            add_channel(
                channel,
                category.get("name"),
                category.get("id"),
            )

    # Uncategorized channels.
    for channel in export_data.get("uncategorized_channels", []):

        add_channel(channel)

    # Associate movement commands with ProBot responses.
    associate_movement_responses(collected)
    
    debug_movement_messages(collected)

    return collected


# -----------------------------------------
# CHARACTER GROUPING
# -----------------------------------------

def group_character_messages(rp_messages, all_messages):
    """Group RP messages by character and connect their replies."""

    characters = {}
    interactions = []
    unassigned = []

    # Create a lookup of every exported message by its ID.
    message_lookup = {
        str(message["id"]): message
        for message in all_messages
        if message.get("id") is not None
    }

    for message in rp_messages:

        character_name = message.get("character_name")

        # Keep messages without a character name separately.
        if not character_name:
            unassigned.append(message.copy())
            continue

        entry = message.copy()

        if character_name not in characters:
            characters[character_name] = []

        # Find the message this character is replying to.
        quoted_reply = message.get("quoted_reply") or {}

        target_id = (
            quoted_reply.get("message_id")
            or message.get("reply_to")
        )

        if target_id:

            target = message_lookup.get(str(target_id))

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
                "message_id": message.get("id"),
                "target_message_id": target_id,
                "target_found": target is not None,
            })

        else:
            entry["reply"] = None

        characters[character_name].append(entry)

    # Keep each character's messages chronological.
    for messages in characters.values():
        messages.sort(key=timestamp_sort_key)

    return {
        "characters": characters,
        "interactions": interactions,
        "unassigned_character_messages": unassigned,
    }

def debug_movement_messages(messages):
    print("\n--- MOVEMENT DEBUG ---")

    for index, message in enumerate(messages):

        content = message.get("content", "").strip()
        author = message.get("discord_author")
        author_type = message.get("author_type")

        if content.lower().startswith(tuple(MOVEMENT_COMMANDS)):

            print("\nCOMMAND FOUND:")
            print("Author:", author)
            print("Type:", author_type)
            print("Content:", repr(content))
            print("Channel:", message.get("channel_id"))

            if index + 1 < len(messages):
                following = messages[index + 1]

                print("NEXT MESSAGE:")
                print("Author:", following.get("discord_author"))
                print("Type:", following.get("author_type"))
                print("Content:", repr(following.get("content", "")[:100]))
                print("Channel:", following.get("channel_id"))

# -----------------------------------------
# VALIDATION
# -----------------------------------------

def validate_processed_data(
    all_messages,
    rp_messages,
    movement_messages,
    timeline,
    character_data,
):
    """Check the consistency of processed RP data."""

    # Normalize message IDs before checking duplicates.
    message_ids = [
        str(message["id"])
        for message in all_messages
        if message.get("id") is not None
    ]

    id_counts = Counter(message_ids)

    duplicates = [
        message_id
        for message_id, count in id_counts.items()
        if count > 1
    ]

    # Create a lookup of all exported messages.
    message_lookup = {
        str(message["id"]): message
        for message in all_messages
        if message.get("id") is not None
    }

    # Check timestamps.
    missing_timestamps = sum(
        message.get("timestamp") is None
        or message.get("timestamp") == ""
        for message in all_messages
    )

    timeline_sorted = (
        timeline == sorted(timeline, key=timestamp_sort_key)
    )

    # Check character grouping.
    expected_ids = [
        str(message["id"])
        for message in rp_messages
        if message.get("character_name")
        and message.get("id") is not None
    ]

    grouped_ids = [
        str(message["id"])
        for messages in character_data["characters"].values()
        for message in messages
        if message.get("id") is not None
    ]

    grouping_matches = (
        Counter(expected_ids) == Counter(grouped_ids)
    )

    # Check unassigned messages.
    expected_unassigned = [
        str(message["id"])
        for message in rp_messages
        if not message.get("character_name")
        and message.get("id") is not None
    ]

    actual_unassigned = [
        str(message["id"])
        for message in character_data["unassigned_character_messages"]
        if message.get("id") is not None
    ]

    unassigned_matches = (
        Counter(expected_unassigned) == Counter(actual_unassigned)
    )

    # Check reply references.
    reply_count = 0
    resolved_character_replies = 0
    unresolved_reply_targets = 0
    non_character_reply_targets = 0

    for message in rp_messages:

        quoted_reply = message.get("quoted_reply") or {}

        target_id = (
            quoted_reply.get("message_id")
            or message.get("reply_to")
        )

        if not target_id:
            continue

        reply_count += 1

        target = message_lookup.get(str(target_id))

        if target is None:
            unresolved_reply_targets += 1

        elif target.get("author_type") == "tupper":
            resolved_character_replies += 1

        else:
            non_character_reply_targets += 1

    # Determine overall validation status.
    passed = (
        not duplicates
        and missing_timestamps == 0
        and timeline_sorted
        and grouping_matches
        and unassigned_matches
    )

    return {
        "passed": passed,

        "message_count": len(all_messages),
        "rp_message_count": len(rp_messages),
        "movement_message_count": len(movement_messages),

        "character_count": len(character_data["characters"]),

        "duplicate_message_id_count": len(duplicates),
        "duplicate_message_id_examples": duplicates[:10],

        "missing_timestamp_count": missing_timestamps,
        "timeline_sorted": timeline_sorted,

        "character_grouping_matches": grouping_matches,
        "unassigned_grouping_matches": unassigned_matches,

        "reply_count": reply_count,
        "resolved_character_replies": resolved_character_replies,
        "unresolved_reply_targets": unresolved_reply_targets,
        "non_character_reply_targets": non_character_reply_targets,
    }