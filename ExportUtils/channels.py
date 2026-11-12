import discord

from ExportUtils.messages import export_messages


# -----------------------------------------
# FORUM POST COLLECTION
# -----------------------------------------

async def collect_forum_posts(channel):
    """Collect active and archived forum posts without duplicates."""

    threads = {}

    # Active forum posts.
    for thread in channel.threads:
        threads[thread.id] = thread

    # Archived forum posts.
    try:

        async for thread in channel.archived_threads(limit=None):
            threads[thread.id] = thread

    except discord.Forbidden:

        print(
            f"Cannot read archived posts in #{channel.name}"
        )

    except discord.HTTPException as error:

        print(
            f"Error retrieving archived posts in "
            f"#{channel.name}: {error}"
        )

    posts = []

    # Export each forum post.
    for thread in sorted(
        threads.values(),
        key=lambda thread: thread.id
    ):

        posts.append({
            "name": thread.name,
            "id": str(thread.id),
            "archived": thread.archived,
            "messages": await export_messages(thread),
        })

    return posts


# -----------------------------------------
# CHANNEL EXPORT
# -----------------------------------------

async def channel_entry(channel):
    """Represent a Discord channel and its messages."""

    entry = {
        "name": channel.name,
        "type": str(channel.type),
        "id": str(channel.id),
        "messages": [],
        "posts": [],
    }

    # Forum channels.
    if isinstance(channel, discord.ForumChannel):

        entry["posts"] = await collect_forum_posts(channel)

    # Regular text channels and threads.
    elif isinstance(
        channel,
        (discord.TextChannel, discord.Thread)
    ):

        entry["messages"] = await export_messages(channel)

    return entry
