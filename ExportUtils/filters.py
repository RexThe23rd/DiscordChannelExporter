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