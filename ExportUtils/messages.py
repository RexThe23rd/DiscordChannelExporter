
import re
import discord


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


def parse_quoted_reply(content):
    """Extract reply information embedded in Tupperbox messages."""

    url_match = re.search(
        r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/"
        r"channels/[^/\s>]+/(\d+)/(\d+)",
        content
    )

    if not url_match:
        return None

    channel_id = url_match.group(1)
    message_id = url_match.group(2)

    mention_match = re.search(
        r"@(.+?)\s*\(<@!?(\d+)>\)",
        content[url_match.end():]
    )

    character_name = None
    discord_user_id = None

    if mention_match:
        character_name = mention_match.group(1).strip()
        discord_user_id = mention_match.group(2)

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

        quoted_line = re.sub(
            r"^\s*(?:>\s*)+",
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
                "quoted_reply": parse_quoted_reply(message.content),
                "attachments": [
                    {
                        "filename": attachment.filename,
                        "url": attachment.url,
                    }
                    for attachment in message.attachments
                ],
            })

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

        # Resolve native Discord replies.
        for message in messages:

            reply_id = message["reply_to"]

            if not reply_id:
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
        print(f"Cannot read messages in #{channel.name}")

    return messages