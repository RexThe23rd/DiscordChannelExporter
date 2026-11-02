import os
import json
import asyncio
from pathlib import Path

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OUTPUT_FILE = Path("world_export.json")


def channel_entry(channel):
    """Represent a channel and its metadata."""
    entry = {
        "name": channel.name,
        "type": str(channel.type),
        "id": channel.id,
        "locations": [],
    }

    if isinstance(channel, discord.ForumChannel):
        # Forum posts are threads; collect active ones here.
        for thread in channel.threads:
            entry["locations"].append({
                "name": thread.name,
                "id": thread.id,
                "archived": thread.archived,
            })

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

            # Include normal channels and forum channels.
            for category in guild.categories:
                category_data = {
                    "name": category.name,
                    "channels": [],
                }

                for channel in category.channels:
                    data = channel_entry(channel)

                    if isinstance(channel, discord.ForumChannel):
                        try:
                            async for thread in channel.archived_threads(limit=None):
                                if not any(
                                    item["id"] == thread.id
                                    for item in data["locations"]
                                ):
                                    data["locations"].append({
                                        "name": thread.name,
                                        "id": thread.id,
                                        "archived": True,
                                    })
                        except discord.Forbidden:
                            print(
                                f"Cannot read archived posts in "
                                f"#{channel.name}"
                            )

                    category_data["channels"].append(data)

                result["categories"].append(category_data)

            # Also retain channels that don't belong to a category.
            for channel in guild.channels:
                if channel.category is None:
                    result["uncategorized_channels"].append(
                        channel_entry(channel)
                    )

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
