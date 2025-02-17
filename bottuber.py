import discord
import asyncio
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging
import pytz
from decimal import Decimal
from googleapiclient.discovery import build

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

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
if YOUTUBE_API_KEY is None:
    print("Error: YOUTUBE_API_KEY environment variable not set.")
    exit(1)


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def get_server_config(guild_id):
    try:
        guild_id_int = int(guild_id)
        response = supabase.table('server_configs').select("*").eq("guild_id", guild_id_int).execute()
        data = response.data if hasattr(response, "data") else response
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting config from Supabase: {e}")
        return None

def set_server_config(guild_id, youtube_channel_id, discord_channel_id):
    try:
        guild_id_int = int(guild_id)
        existing = get_server_config(guild_id_int)
        if existing:
            if youtube_channel_id is None:
                youtube_channel_id = existing.get('youtube_channel_id')
            if discord_channel_id is None:
                discord_channel_id = existing.get('discord_channel_id')
        else:
            if youtube_channel_id is None:
                raise ValueError("You must set a YouTube channel first before setting the Discord channel.")
        data, count = supabase.table('server_configs').upsert({
            "id": guild_id_int,
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
    except Exception as e:
        logger.error(f"Error setting schedule in Supabase: {e}")
        return None

def remove_server_schedule(guild_id):
    try:
        guild_id_int = int(guild_id)
        data, count = supabase.table('server_schedules').delete().eq("guild_id", guild_id_int).execute()
        return data
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
            # Return a very old time so that the first check is always due.
            return datetime.fromtimestamp(0, tz=pytz.utc)
    except Exception as e:
        logger.error(f"Error getting last check time from Supabase: {e}")
        return datetime.fromtimestamp(0, tz=pytz.utc)

async def set_last_check_time(guild_id, last_check_time):
    try:
        guild_id_int = int(guild_id)
        data, count = supabase.table('server_schedules').update({"last_check": last_check_time.isoformat()}).eq("guild_id", guild_id_int).execute()
        return data
    except Exception as e:
        logger.error(f"Error setting last check time in Supabase: {e}")
        return None

def get_channel_info(youtube_channel_id):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.channels().list(
            part='snippet,statistics',
            id=youtube_channel_id
        )
        response = request.execute()
        if response['items']:
            channel = response['items'][0]
            title = channel['snippet']['title']
            description = channel['snippet']['description']
            subscriber_count = channel['statistics']['subscriberCount']
            thumbnail = channel['snippet']['thumbnails']['high']['url'] if 'high' in channel['snippet']['thumbnails'] else None
            return {
                'title': title,
                'description': description,
                'subscriber_count': subscriber_count,
                'thumbnail': thumbnail
            }
        else:
            logger.error(f"Channel with ID {youtube_channel_id} not found.")
            return None
    except Exception as e:
        logger.error(f"An error occurred while fetching channel info: {e}")
        return None

def get_latest_videos(youtube_channel_id, max_results=5):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            part='snippet',
            channelId=youtube_channel_id,
            order='date',
            type='video',
            maxResults=max_results
        )
        response = request.execute()
        videos = []
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            url = f"http://www.youtube.com/watch?v={video_id}"
            published_at = item['snippet']['publishedAt']
            videos.append({'video_id': video_id, 'title': title, 'url': url, 'published_at': published_at})
        return videos
    except Exception as e:
        logger.error(f"An error occurred while fetching latest videos: {e}")
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
        latest_videos = get_latest_videos(youtube_channel_id)
        if latest_videos:
            new_video = latest_videos[0]
            video_id = new_video.get('video_id')
            if video_id != last_video_id:
                update_last_video_id(guild_id, video_id)
                title = new_video.get('title')
                url = new_video.get('url')
                published_at = new_video.get('published_at')
                channel = client.get_channel(int(discord_channel_id))
                if channel:
                    embed = discord.Embed(title=title, url=url)
                    embed.add_field(name="Published", value=published_at, inline=True)
                    try:
                        await channel.send(embed=embed)
                        logger.info(f"New video posted: {title} in server {guild_id}")
                    except discord.errors.HTTPException as e:
                        logger.error(f"Error sending embed to Discord: {e}")
                else:
                    logger.error(f"Could not find Discord channel with ID: {discord_channel_id} for server {guild_id}")
        else:
            logger.error(f"Could not retrieve videos for YouTube channel ID: {youtube_channel_id}")
    except Exception as e:
        logger.error(f"Error checking for videos in server {guild_id}: {e}")


def is_check_due(schedule, last_check_time):
    """
    Determines whether the scheduled check for the day is due.
    If the scheduled time for today has passed and no check has been recorded for today, return True.
    """
    try:
        now = datetime.now(timezone.utc)
        check_time_str = schedule.get("check_time")  # e.g., "09:00"
        timezone_str = schedule.get("timezone")      # e.g., "US/Central"
        guild_timezone = pytz.timezone(timezone_str)
        # Convert current UTC time to the guild's local date
        now_local = now.astimezone(guild_timezone)
        today_local_date = now_local.date()
        # Build today's scheduled datetime in the guild's local time
        scheduled_local = datetime.combine(today_local_date, datetime.strptime(check_time_str, "%H:%M").time(), tzinfo=guild_timezone)
        # Convert scheduled time to UTC for comparison
        scheduled_utc = scheduled_local.astimezone(pytz.utc)
        
        # If current time is past the scheduled time and last_check_time is before today's scheduled time, it's due.
        if now >= scheduled_utc:
            if last_check_time < scheduled_utc:
                return True
    except Exception as e:
        logger.error(f"Error in is_check_due: {e}")
    return False

async def scheduled_check():
    CHECK_INTERVAL = 60  # seconds
    while True:
        now = datetime.now(timezone.utc)
        for guild in client.guilds:
            schedule = get_server_schedule(guild.id)
            if not schedule:
                continue  # Skip guilds without a schedule
            
            try:
                last_check_time = await get_last_check_time(guild.id)
                if is_check_due(schedule, last_check_time):
                    # Update last_check_time to now before running the check
                    await set_last_check_time(guild.id, now)
                    await check_for_new_videos(guild.id)
            except Exception as e:
                logger.error(f"Error during scheduled check for guild {guild.id}: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


@client.event
async def on_ready():
    logger.info(f'{client.user} has connected to Discord!')
    # On startup, check if any scheduled checks were missed (for instance, while the bot was offline)
    for guild in client.guilds:
        schedule = get_server_schedule(guild.id)
        if schedule:
            last_check_time = await get_last_check_time(guild.id)
            if is_check_due(schedule, last_check_time):
                logger.info(f"Missed scheduled check for guild {guild.id}; checking now.")
                await set_last_check_time(guild.id, datetime.now(timezone.utc))
                await check_for_new_videos(guild.id)
    # Start the scheduled check loop
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
    logger.info(f"Received command: {subcommand}")

    admin_commands = {"setchannel", "setdiscordchannel", "setschedule", "removeschedule", "remove"}
    if subcommand in admin_commands and not message.author.guild_permissions.administrator:
        await message.channel.send("You must be an administrator to use this command.")
        return

    if subcommand == "help":
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
                # Try 12-hour format first
                check_time = datetime.strptime(time_str, "%I:%M%p").time()
            except ValueError:
                # Fallback to 24-hour format
                check_time = datetime.strptime(time_str, "%H:%M").time()
            pytz.timezone(timezone_str)  # Validate timezone
            server_id = message.guild.id
            result = set_server_schedule(server_id, check_time.strftime("%H:%M"), timezone_str)
            if result:
                await message.channel.send(f"Schedule set to {time_str} in {timezone_str}!")
            else:
                await message.channel.send("Failed to set schedule. Please check the logs for errors.")
        except ValueError as e:
            await message.channel.send(f"Usage: !tb setschedule <HH:MMam/pm or HH:MM> <Timezone>\nError: {e}")
        except pytz.exceptions.UnknownTimeZoneError:
            await message.channel.send("Invalid Timezone. Please check the IANA timezone database (https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)")
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
            channel_info = get_channel_info(config['youtube_channel_id'])
            if channel_info:
                embed = discord.Embed(title=channel_info['title'], description=channel_info['description'])
                embed.add_field(name="Subscribers", value=channel_info['subscriber_count'], inline=True)
                if channel_info['thumbnail']:
                    embed.set_thumbnail(url=channel_info['thumbnail'])
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("Error fetching channel info.")
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