import os
import json
import asyncio
import argparse

from pathlib import Path

import discord
from dotenv import load_dotenv

from ExportUtils.channels import channel_entry

from ExportUtils.filters import (
    collect_messages,
    filter_messages,
    group_character_messages,
    validate_processed_data,
    timestamp_sort_key,
)


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

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

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
                # These contain world lore, systems, rules, etc.
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
            # SAVE RAW EXPORT
            # ---------------------------------

            output_path = (
                OUTPUT_DIR / f"{guild.id}_world_export.json"
            )

            output_path.write_text(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8",
            )

            print(f"Saved raw export: {output_path.resolve()}")

            # ---------------------------------
            # COLLECT MESSAGES
            # ---------------------------------

            all_messages = collect_messages(result)

            print(f"Collected messages: {len(all_messages)}")

            # ---------------------------------
            # CLASSIFY MESSAGES
            # ---------------------------------

            rp_messages = filter_messages(
                all_messages,
                "rp"
            )

            movement_messages = filter_messages(
                all_messages,
                "movement"
            )

            # ---------------------------------
            # CHARACTER GROUPING
            # ---------------------------------

            character_data = group_character_messages(
                rp_messages,
                all_messages
            )

            # ---------------------------------
            # TIMELINE
            # ---------------------------------

            timeline = sorted(
                rp_messages + movement_messages,
                key=timestamp_sort_key
            )

            # ---------------------------------
            # VALIDATION
            # ---------------------------------

            validation = validate_processed_data(
                all_messages,
                rp_messages,
                movement_messages,
                timeline,
                character_data,
            )

            # ---------------------------------
            # PROCESSED EXPORT
            # ---------------------------------

            processed = {
                "server": guild.name,
                "server_id": guild.id,

                "rp_messages": rp_messages,
                "movement_messages": movement_messages,
                "timeline": timeline,

                "validation": validation,

                "characters": character_data["characters"],
                "interactions": character_data["interactions"],

                "unassigned_character_messages": (
                    character_data["unassigned_character_messages"]
                ),
            }

            processed_path = (
                PROCESSED_DIR / f"{guild.id}_processed.json"
            )

            processed_path.write_text(
                json.dumps(
                    processed,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8",
            )

            print(f"Saved processed export: {processed_path.resolve()}")

            # ---------------------------------
            # EXPORT SUMMARY
            # ---------------------------------

            print(
                f"Validation: "
                f"{'PASSED' if validation['passed'] else 'CHECK REQUIRED'}"
            )

            print(
                f"Messages: {validation['message_count']} | "
                f"RP: {validation['rp_message_count']} | "
                f"Movement: {validation['movement_message_count']}"
            )

            print(
                f"Characters: {validation['character_count']} | "
                f"Replies: {validation['reply_count']} | "
                f"Resolved character replies: "
                f"{validation['resolved_character_replies']}"
            )

            print(
                f"Unresolved replies: "
                f"{validation['unresolved_reply_targets']} | "
                f"Non-character replies: "
                f"{validation['non_character_reply_targets']}"
            )

            if not validation["passed"]:

                print("Validation details:")

                print(
                    json.dumps(
                        validation,
                        indent=2
                    )
                )

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