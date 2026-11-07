
import discord


async def channel_entry(channel):
    """Represent a Discord channel and its metadata."""

    entry = {
        "name": channel.name,
        "type": str(channel.type),
        "id": channel.id,
        "posts": [],
    }

    if isinstance(channel, discord.ForumChannel):

        # Active forum posts.
        for thread in channel.threads:

            entry["posts"].append({
                "name": thread.name,
                "id": thread.id,
                "archived": thread.archived,
            })

        # Archived forum posts.
        try:
            async for thread in channel.archived_threads(
                limit=None
            ):

                if not any(
                    item["id"] == thread.id
                    for item in entry["posts"]
                ):

                    entry["posts"].append({
                        "name": thread.name,
                        "id": thread.id,
                        "archived": True,
                    })

        except discord.Forbidden:
            print(
                f"Cannot read archived posts in #{channel.name}"
            )

    return entry