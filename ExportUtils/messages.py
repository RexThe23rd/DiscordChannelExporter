
import re
import discord


# -----------------------------------------
# MESSAGE SUMMARY
# -----------------------------------------

def message_summary(message):
    """Create a compact representation of a message's author and content."""

    if message.webhook_id is not None:

        author_type = "tupper"
        character_name = message.author.display_name
        discord_author = None

    elif message.is_system():

        author_type = "system"
        character_name = None
        discord_author = None

    elif message.author.bot:

        author_type = "bot"
        character_name = None
        discord_author = str(message.author)

    else:

        author_type = "user"
        character_name = None
        discord_author = str(message.author)

    return {
        "id": str(message.id),
        "character_name": character_name,
        "discord_author": discord_author,
        "author_type": author_type,
        "content": message.content,
        "timestamp": message.created_at.isoformat(),
    }


# -----------------------------------------
# TUPPERBOX REPLY PARSING
# -----------------------------------------

DISCORD_REPLY_PATTERN = re.compile(
    r"https?://"
    r"(?:(?:canary|ptb)\.)?"
    r"discord(?:app)?\.com/"
    r"channels/(\d+)/(\d+)"
)

MENTION_PATTERN = re.compile(
    r"@(.+?)\s*\(<@!?(\d+)>\)"
)


def parse_quoted_reply(content):
    """Extract reply information embedded in Tupperbox messages."""

    # Find the Discord message URL.
    url_match = DISCORD_REPLY_PATTERN.search(content)

    if not url_match:
        return None

    channel_id = url_match.group(1)
    message_id = url_match.group(2)

    # Extract the character name and Discord user ID.
    mention_match = MENTION_PATTERN.search(
        content[url_match.end():]
    )

    character_name = None
    discord_user_id = None

    if mention_match:

        character_name = mention_match.group(1).strip()
        discord_user_id = mention_match.group(2)

    # Extract the quoted message preview.
    lines = content.splitlines()

    preview_lines = []
    header_found = False

    for line in lines:

        if not header_found:

            if "[Reply to]" in line:
                header_found = True

            continue

        stripped = line.lstrip()

        if not stripped.startswith(">"):
            break

        # Remove Discord quote markers.
        quoted_line = re.sub(
            r"^\s*>+\s?",
            "",
            line
        )

        preview_lines.append(quoted_line)

    preview = "\n".join(preview_lines).strip()

    return {
        "message_id": message_id,
        "channel_id": channel_id,
        "character_name": character_name,
        "discord_user_id": discord_user_id,
        "preview": preview,
    }


# -----------------------------------------
# ATTACHMENT EXPORT
# -----------------------------------------

def export_attachments(message):
    """Extract attachment metadata from a Discord message."""

    return [
        {
            "filename": attachment.filename,
            "url": attachment.url,
        }
        for attachment in message.attachments
    ]


# -----------------------------------------
# MESSAGE EXPORT
# -----------------------------------------

async def export_messages(channel):
    """Export messages and resolve their Discord reply references."""

    messages = []
    message_lookup = {}

    try:

        async for message in channel.history(
            limit=None,
            oldest_first=True
        ):

            # Ignore bots except ProBot.
            # Webhook messages are preserved.
            if (
                message.author.bot
                and message.webhook_id is None
                and message.author.name.lower() != "probot"
            ):
                continue

            entry = message_summary(message)

            entry.update({
                "webhook_id": (
                    str(message.webhook_id)
                    if message.webhook_id else None
                ),

                "reply_to": None,
                "reply_channel_id": None,
                "reply_context": None,

                "quoted_reply": parse_quoted_reply(
                    message.content
                ),

                "attachments": export_attachments(message),
            })

            # Native Discord reply references.
            if message.reference:

                if message.reference.message_id:

                    entry["reply_to"] = str(
                        message.reference.message_id
                    )

                if message.reference.channel_id:

                    entry["reply_channel_id"] = str(
                        message.reference.channel_id
                    )

            messages.append(entry)

            message_lookup[str(message.id)] = entry

        # ---------------------------------
        # RESOLVE NATIVE REPLIES
        # ---------------------------------

        for message in messages:

            reply_id = message["reply_to"]

            if not reply_id:
                continue

            # Only resolve replies belonging to this channel.
            reply_channel_id = message["reply_channel_id"]

            if (
                reply_channel_id is not None
                and reply_channel_id != str(channel.id)
            ):
                continue

            referenced = message_lookup.get(reply_id)

            if referenced:

                message["reply_context"] = {
                    key: referenced[key]
                    for key in (
                        "id",
                        "character_name",
                        "discord_author",
                        "author_type",
                        "content",
                        "timestamp",
                    )
                }

    except discord.Forbidden:

        print(
            f"Cannot read messages in #{channel.name}"
        )

    except discord.HTTPException as error:

        print(
            f"Error retrieving messages in "
            f"#{channel.name}: {error}"
        )

    return messages