import discord

from ExportUtils.messages import export_messages


async def channel_entry(channel):
    """Represent a Discord channel and its messages."""

    entry = {
        "name": channel.name,
        "type": str(channel.type),
        "id": str(channel.id),
        "messages": [],
        "posts": [],
    }

    if isinstance(channel, discord.ForumChannel):

        threads = {}

        # Active forum posts.
        for thread in channel.threads:
            threads[thread.id] = thread

        # Archived forum posts.
        try:
            async for thread in channel.archived_threads(
                limit=None
            ):
                threads[thread.id] = thread

        except discord.Forbidden:
            print(
                f"Cannot read archived posts in #{channel.name}"
            )

        # Export each forum post and its messages.
        for thread in threads.values():

            entry["posts"].append({
                "name": thread.name,
                "id": str(thread.id),
                "archived": thread.archived,
                "messages": await export_messages(thread),
            })

    elif isinstance(
        channel,
        (discord.TextChannel, discord.Thread)
    ):
        entry["messages"] = await export_messages(channel)

    return entry
