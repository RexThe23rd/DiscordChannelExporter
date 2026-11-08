import os
import json
import asyncio
import argparse

from pathlib import Path

import discord
from dotenv import load_dotenv

from ExportUtils.channels import channel_entry
from ExportUtils.filters import collect_messages, filter_messages

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OUTPUT_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


# -----------------------------------------
# ARGUMENTS
# -----------------------------------------

def parse_arguments():

    parser = argparse.ArgumentParser(
        description="Discord server exporter."
    )

    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        help="Categories to exclude from export."
    )

    parser.add_argument(
        "--separate",
        nargs="+",
        default=[],
        help="Categories to export as references."
    )

    return parser.parse_args()


# -----------------------------------------
# DISCORD CLIENT
# -----------------------------------------

class WorldExporter(discord.Client):

    def __init__(self, *args, options, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = options

    async def on_ready(self):

        print(f"Connected as {self.user}")

        if not self.guilds:
            print("No servers are visible to the bot.")
            await self.close()
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        for guild in self.guilds:

            print(f"\nExporting server: {guild.name}")

            result = {
                "server": guild.name,
                "server_id": guild.id,
                "categories": [],
                "references": {},
                "uncategorized_channels": [],
            }

            # ---------------------------------
            # CATEGORIZED CHANNELS
            # ---------------------------------

            for category in guild.categories:

                name = category.name

                # Exclusion takes priority.
                if name in self.options.exclude:
                    print(f"Excluded category: {name}")
                    continue

                category_data = {
                    "name": name,
                    "id": category.id,
                    "channels": [],
                }

                for channel in category.channels:

                    data = await channel_entry(channel)
                    category_data["channels"].append(data)

                # Separate reference categories.
                if name in self.options.separate:

                    result["references"][name] = category_data

                else:
                    result["categories"].append(category_data)

            # ---------------------------------
            # UNCATEGORIZED CHANNELS
            # ---------------------------------

            for channel in guild.channels:

                if (
                    channel.category is None
                    and not isinstance(
                        channel,
                        discord.CategoryChannel
                    )
                ):

                    data = await channel_entry(channel)

                    result["uncategorized_channels"].append(data)

            # ---------------------------------
            # SAVE EXPORT
            # ---------------------------------            
            # Save the complete raw export.
            
            output_path = OUTPUT_DIR / f"{guild.id}_world_export.json"

            output_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            print(f"Saved raw export: {output_path.resolve()}")

            # Collect and classify messages.
            all_messages = collect_messages(result)

            processed = {
                "server": guild.name,
                "server_id": guild.id,
                "rp_messages": filter_messages(all_messages, "rp"),
                "movement_messages": filter_messages(all_messages, "movement"),
            }

            # Save the processed export.
            PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

            processed_path = PROCESSED_DIR / f"{guild.id}_processed.json"

            processed_path.write_text(
                json.dumps(processed, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            print(f"Saved processed export: {processed_path.resolve()}")


        await self.close()


# -----------------------------------------
# MAIN
# -----------------------------------------

async def main():

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing. Check your .env file."
        )

    options = parse_arguments()

    intents = discord.Intents.default()
    intents.message_content = True

    client = WorldExporter(
        intents=intents,
        options=options
    )

    await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())