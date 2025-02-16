import discord
import yt_dlp as youtube_dl
import asyncio
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
if DISCORD_TOKEN is None:
    print("Error: DISCORD_TOKEN environment variable not set.")
    exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY environment variables not set.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

ydl_opts = {
    'format': 'bestaudio/bestvideo',
    'noplaylist': True,
}


def get_server_config(guild_id):
    try:
        guild_id_int = int(guild_id)
        response = supabase.table('server_configs').select("*").eq("guild_id", guild_id_int).execute()
        # Use response.data if available
        data = response.data if hasattr(response, "data") else response
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting config from Supabase: {e}")
        return None


def set_server_config(guild_id, youtube_channel_id, discord_channel_id):
    """
    Merge new values with any existing record.
    If no record exists and youtube_channel_id is not provided,
    raise an error (since youtube_channel_id is required).
    """
    try:
        guild_id_int = int(guild_id)
        existing = get_server_config(guild_id_int)
        if existing:
            # Preserve existing values if not provided now.
            if youtube_channel_id is None:
                youtube_channel_id = existing.get('youtube_channel_id')
            if discord_channel_id is None:
                discord_channel_id = existing.get('discord_channel_id')
        else:
            # No existing record – require a YouTube channel
            if youtube_channel_id is None:
                raise ValueError("You must set a YouTube channel first before setting the Discord channel.")
        data, count = supabase.table('server_configs').upsert({
            "id": guild_id_int,  # Satisfy the NOT NULL constraint on 'id'
            "guild_id": guild_id_int,
            "youtube_channel_id": youtube_channel_id,
            "discord_channel_id": discord_channel_id
        }).execute()
        return data
    except Exception as e:
        logger.error(f"Error setting config in Supabase: {e}")
        return None


def update_last_video_id(guild_id, last_video_id):
    try:
        guild_id_int = int(guild_id)
        data, count = supabase.table('server_configs').update({"last_video_id": last_video_id}).eq("guild_id", guild_id_int).execute()
        return data
    except Exception as e:
        logger.error(f"Error updating last_video_id in Supabase: {e}")
        return None


def remove_server_config(guild_id):
    try:
        guild_id_int = int(guild_id)
        data, count = supabase.table('server_configs').delete().eq("guild_id", guild_id_int).execute()
        return data
    except Exception as e:
        logger.error(f"Error removing config from Supabase: {e}")
        return None


def get_server_schedule(guild_id):
    try:
        guild_id_int = int(guild_id)
        response = supabase.table('server_schedules').select("*").eq("guild_id", guild_id_int).execute()
        data = response.data if hasattr(response, "data") else response
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting schedule from Supabase: {e}")
        return None


def set_server_schedule(guild_id, check_time_str, timezone_str):
    try:
        guild_id_int = int(guild_id)
        data, count = supabase.table('server_schedules').upsert({
            "guild_id": guild_id_int,
            "check_time": check_time_str,
            "timezone": timezone_str
        }).execute()
        return data
    except (ValueError, TypeError):
        logger.error("Invalid guild_id: Must be an integer.")
        return None
    except Exception as e:
        logger.error(f"Error setting schedule in Supabase: {e}")
        return None


def remove_server_schedule(guild_id):
    try:
        guild_id_int = int(guild_id)
        data, count = supabase.table('server_schedules').delete().eq("guild_id", guild_id_int).execute()
        return data
    except (ValueError, TypeError):
        logger.error("Invalid guild_id: Must be an integer.")
        return None
    except Exception as e:
        logger.error(f"Error removing schedule from Supabase: {e}")
        return None


async def get_last_check_time(guild_id):
    try:
        guild_id_int = int(guild_id)
        response = supabase.table('server_schedules').select("last_check").eq("guild_id", guild_id_int).execute()
        data = response.data if hasattr(response, "data") else response
        if data and isinstance(data, list) and len(data) > 0 and data[0].get('last_check'):
            return datetime.fromisoformat(data[0]['last_check'])
        else:
            return datetime.fromtimestamp(0, tz=pytz.utc)
    except Exception as e:
        logger.error(f"Error getting last check time from Supabase: {e}")
        return datetime.fromtimestamp(0, tz=pytz.utc)


async def set_last_check_time(guild_id, last_check_time):
    try:
        guild_id_int = int(guild_id)
        data, count = supabase.table('server_schedules').update({"last_check": last_check_time.isoformat()}).eq("guild_id", guild_id_int).execute()
        return data
    except (ValueError, TypeError):
        logger.error("Invalid guild_id: Must be an integer.")
        return None
    except Exception as e:
        logger.error(f"Error setting last check time in Supabase: {e}")
        return None


async def check_for_new_videos(guild_id):
    config = get_server_config(guild_id)
    if not config:
        return

    youtube_channel_id = config.get("youtube_channel_id")
    discord_channel_id = config.get("discord_channel_id")
    last_video_id = config.get("last_video_id")

    if not youtube_channel_id or not discord_channel_id:
        return

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            channel_url = f"https://www.youtube.com/channel/{youtube_channel_id}"
            info = ydl.extract_info(channel_url, download=False)

            if 'entries' not in info or not info['entries']:
                print(f"No videos found for channel ID: {youtube_channel_id}")
                return

            video = info['entries'][0]
            video_id = video['id']

            if video_id != last_video_id:
                update_last_video_id(guild_id, video_id)
                title = video.get('title')
                url = video.get('webpage_url')
                description = video.get('description')
                published_at = datetime.fromisoformat(video.get('upload_date')[0:10]).strftime("%Y-%m-%d")

                channel = client.get_channel(int(discord_channel_id))
                if channel:
                    embed = discord.Embed(title=title, description=description, url=url)
                    embed.add_field(name="Published", value=published_at, inline=True)
                    await channel.send(embed=embed)
                    print(f"New video posted: {title} in server {guild_id}")
                else:
                    print(f"Could not find channel with ID: {discord_channel_id} in server {guild_id}")

    except Exception as e:
        print(f"Error checking for videos in server {guild_id}: {e}")


async def scheduled_check():
    while True:
        now = datetime.now(timezone.utc)  # Ensure now is timezone-aware

        for guild in client.guilds:
            schedule = get_server_schedule(guild.id)
            if not schedule:
                continue  # Skip if no schedule exists
            
            try:
                check_time_str = schedule.get("check_time")  # e.g., "09:00"
                timezone_str = schedule.get("timezone")  # e.g., "US/Central"
                
                guild_timezone = pytz.timezone(timezone_str)  # Avoid overwriting 'timezone'
                check_time = datetime.strptime(check_time_str, "%H:%M").time()
                
                # Convert target time to UTC
                target_time_local = datetime.combine(now.date(), check_time, tzinfo=guild_timezone)
                target_time_utc = target_time_local.astimezone(pytz.utc)

                # Get last check time
                last_check_time = await get_last_check_time(guild.id)
                if last_check_time and last_check_time.tzinfo is None:
                    last_check_time = last_check_time.replace(tzinfo=timezone.utc)

                # Check if it's time to run
                if now >= target_time_utc and (now - last_check_time).total_seconds() >= 86400:
                    await set_last_check_time(guild.id, now)
                    await check_for_new_videos(guild.id)

            except ValueError:
                logger.error(f"Invalid time format for guild {guild.id}")
                remove_server_schedule(guild.id)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.error(f"Invalid timezone for guild {guild.id}")
                remove_server_schedule(guild.id)

        await asyncio.sleep(60)  # Check every minute


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    client.loop.create_task(scheduled_check())


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not message.content.startswith("!tb"):
        return

    parts = message.content.split()
    if len(parts) < 2:
        await message.channel.send("Please provide a command after !tb")
        return

    subcommand = parts[1].lower()
    print(f"Received command: {subcommand}")

    # Commands requiring administrator privileges
    admin_commands = {"setchannel", "setdiscordchannel", "setschedule", "removeschedule", "remove"}
    if subcommand in admin_commands:
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You must be an administrator to use this command.")
            return

    if subcommand == "ping":
        await message.channel.send("Pong!")

    elif subcommand == "help":
        await message.channel.send(
            "Available commands:\n"
            "!tb help\n"
            "!tb setchannel <youtube_channel_id>\n"
            "!tb setdiscordchannel <discord_channel_id>\n"
            "!tb setschedule <HH:MMam/pm or HH:MM> <Timezone>\n"
            "!tb removeschedule\n"
            "!tb listschedule\n"
            "!tb test\n"
            "!tb info\n"
            "!tb remove\n"
            "!tb about"
        )

    elif subcommand == "setchannel":
        if len(parts) < 3:
            await message.channel.send("Usage: !tb setchannel <youtube_channel_id>")
            return
        channel_id = parts[2]
        server_id = message.guild.id
        result = set_server_config(server_id, channel_id, None)
        if result:
            await message.channel.send("YouTube channel set!")
        else:
            await message.channel.send("Failed to set YouTube channel. Check logs for errors.")

    elif subcommand == "setdiscordchannel":
        if len(parts) < 3:
            await message.channel.send("Usage: !tb setdiscordchannel <discord_channel_id>")
            return
        discord_channel_id = parts[2]
        server_id = message.guild.id
        result = set_server_config(server_id, None, discord_channel_id)
        if result:
            await message.channel.send("Discord channel set!")
        else:
            await message.channel.send("Failed to set Discord channel. Make sure you have already set a YouTube channel.")

    elif subcommand == "setschedule":
        try:
            if len(parts) != 4:
                raise ValueError("Incorrect number of arguments")
            time_str = parts[2].lower()
            timezone_str = parts[3]

            try:
                check_time = datetime.strptime(time_str, "%I:%M%p").time()
            except ValueError:
                try:
                    check_time = datetime.strptime(time_str, "%H:%M").time()
                except ValueError:
                    raise ValueError("Invalid time format. Use HH:MMam/pm or HH:MM (24-hour format)")

            # Validate the timezone
            pytz.timezone(timezone_str)
            server_id = message.guild.id
            result = set_server_schedule(server_id, check_time.strftime("%H:%M"), timezone_str)
            if result:
                await message.channel.send(f"Schedule set to {time_str} in {timezone_str}!")
            else:
                await message.channel.send("Failed to set schedule. Please check the logs for errors.")

        except ValueError as e:
            await message.channel.send(f"Usage: !tb setschedule <HH:MMam/pm or HH:MM> <Timezone (e.g., US/Central)>\nError: {e}")
        except pytz.exceptions.UnknownTimeZoneError:
            await message.channel.send("Invalid Timezone, please check the IANA timezone database (https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)")
        except Exception as e:
            logger.exception("Error setting schedule")
            await message.channel.send(f"An unexpected error occurred: {e}")

    elif subcommand == "removeschedule":
        server_id = message.guild.id
        removed = remove_server_schedule(server_id)
        if removed:
            await message.channel.send("Schedule removed for this server.")
        else:
            await message.channel.send("No schedule found for this server.")

    elif subcommand == "listschedule":
        schedule = get_server_schedule(message.guild.id)
        if schedule:
            check_time = schedule.get("check_time")
            timezone = schedule.get("timezone")
            await message.channel.send(f"Current schedule: {check_time} in {timezone}")
        else:
            await message.channel.send("No schedule set for this server.")

    elif subcommand == "test":
        config = get_server_config(message.guild.id)
        if config and config.get("youtube_channel_id") and config.get("discord_channel_id"):
            await message.channel.send("Testing connection... (This may take a moment)")
            await check_for_new_videos(message.guild.id)
        else:
            await message.channel.send("Please set both YouTube and Discord channels first.")

    elif subcommand == "info":
        config = get_server_config(message.guild.id)
        if config and config.get("youtube_channel_id"):
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    channel_url = f"https://www.youtube.com/channel/{config['youtube_channel_id']}"
                    info = ydl.extract_info(channel_url, download=False)
                    channel_name = info.get('title') or info.get('channel_name')
                    subscriber_count = info.get('subscriber_count')
                    description = info.get('description')
                    thumbnail = info.get('thumbnail')

                    embed = discord.Embed(title=channel_name, description=description)
                    embed.add_field(name="Subscribers", value=subscriber_count, inline=True)
                    if thumbnail:
                        embed.set_thumbnail(url=thumbnail)
                    await message.channel.send(embed=embed)
            except Exception as e:
                await message.channel.send(f"Error fetching channel info: {e}")
        else:
            await message.channel.send("Please set the YouTube channel first.")

    elif subcommand == "remove":
        server_id = message.guild.id
        try:
            removed_config = remove_server_config(server_id)
            removed_schedule = remove_server_schedule(server_id)
            if removed_config or removed_schedule:
                await message.channel.send("Configuration and schedule removed for this server.")
            else:
                await message.channel.send("No configuration or schedule found for this server.")
        except Exception as e:
            logger.exception("Error removing configuration or schedule")
            await message.channel.send("An error occurred while removing the configuration or schedule.")

    elif subcommand == "about":
        await message.channel.send("BotTuber - A YouTube video posting bot for Discord. Created by SigmaSauer07.")

    else:
        await message.channel.send("Unknown command. Use !tb help for a list of commands.")


client.run(DISCORD_TOKEN)
