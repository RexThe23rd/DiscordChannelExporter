import os
import json
import asyncio
from pathlib import Path

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OUTPUT_FILE = Path("world_export.json")


async def channel_entry(channel):
    """Represent a channel and its metadata."""
    entry = {
        "name": channel.name,
        "type": str(channel.type),
        "id": channel.id,
        "posts": [],
    }

    if isinstance(channel, discord.ForumChannel):
        # Collect active forum posts.
        for thread in channel.threads:
            entry["posts"].append({
                "name": thread.name,
                "id": thread.id,
                "archived": thread.archived,
            })

        # Collect archived forum posts.
        try:
            async for thread in channel.archived_threads(limit=None):
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
            print(f"Cannot read archived posts in #{channel.name}")

    return entry


class WorldExporter(discord.Client):
    async def on_ready(self):
        print(f"Connected as {self.user}")

        guilds = list(self.guilds)

        if not guilds:
            print("No servers are visible to the bot.")
            await self.close()
            return

        for guild in guilds:
            print(f"Exporting server: {guild.name}")

            result = {
                "server": guild.name,
                "server_id": guild.id,
                "categories": [],
                "uncategorized_channels": [],
            }

            # Export categorized channels.
            for category in guild.categories:
                category_data = {
                    "name": category.name,
                    "channels": [],
                }

                for channel in category.channels:
                    data = await channel_entry(channel)
                    category_data["channels"].append(data)

                result["categories"].append(category_data)

            # Export channels without a category.
            for channel in guild.channels:
                if (
                    channel.category is None
                    and not isinstance(channel, discord.CategoryChannel)
                ):
                    data = await channel_entry(channel)
                    result["uncategorized_channels"].append(data)

            # Save the server export.
            output_path = OUTPUT_FILE.with_name(
                f"{guild.id}_{OUTPUT_FILE.name}"
            )

            output_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            print(f"Saved: {output_path.resolve()}")

        await self.close()


intents = discord.Intents.default()
client = WorldExporter(intents=intents)

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. Check your .env file."
    )

asyncio.run(client.start(TOKEN))
