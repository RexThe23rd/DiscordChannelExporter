import discord


async def export_messages(channel):
    """Export messages from a Discord text channel or forum thread."""

    messages = []

    try:
        async for message in channel.history(
            limit=None,
            oldest_first=True
        ):

            # Identify webhook messages (Tupperbox, NPCs, etc.).
            if message.webhook_id is not None:
                author_type = "tupper"
                character_name = message.author.display_name
                discord_author = None

            # Ignore messages from other bots for now.
            elif message.author.bot:
                continue

            else:
                author_type = "user"
                character_name = None
                discord_author = str(message.author)

            messages.append({
                "id": str(message.id),
                "character_name": character_name,
                "discord_author": discord_author,
                "author_type": author_type,
                "webhook_id": (
                    str(message.webhook_id)
                    if message.webhook_id else None
                ),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "reply_to": (
                    str(message.reference.message_id)
                    if message.reference
                    and message.reference.message_id
                    else None
                ),
                "attachments": [
                    {
                        "filename": attachment.filename,
                        "url": attachment.url,
                    }
                    for attachment in message.attachments
                ],
            })

    except discord.Forbidden:
        print(f"Cannot read messages in #{channel.name}")

    return messages