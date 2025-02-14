import discord
import youtube_dl
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client

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
        data, count = supabase.table('server_configs').select("*").eq("guild_id", guild_id).execute()
        if data:
            return data[0]
        return None
    except Exception as e:
        print(f"Error getting config from Supabase: {e}")
        return None


def set_server_config(guild_id, youtube_channel_id, discord_channel_id):
    try:
        data, count = supabase.table('server_configs').upsert({"guild_id": guild_id, "youtube_channel_id": youtube_channel_id, "discord_channel_id": discord_channel_id}).execute()
        return data
    except Exception as e:
        print(f"Error setting config in Supabase: {e}")
        return None


def update_last_video_id(guild_id, last_video_id):
    try:
        data, count = supabase.table('server_configs').update({"last_video_id": last_video_id}).eq("guild_id", guild_id).execute()
        return data
    except Exception as e:
        print(f"Error updating last_video_id in Supabase: {e}")
        return None

def remove_server_config(guild_id):
    try:
        data, count = supabase.table('server_configs').delete().eq("guild_id", guild_id).execute()
        return data
    except Exception as e:
        print(f"Error removing config from Supabase: {e}")
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
            channel_url = f"https://www.youtube.com/channel/{youtube_channel_id}" # or user/{username}
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


async def check_periodically():
    while True:
        for guild in client.guilds:
            await check_for_new_videos(guild.id)
        await asyncio.sleep(60 * 5)  # Check every 5 minutes (adjust as needed)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    client.loop.create_task(check_periodically())


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!tb"):
        command = message.content.split()[0]

        if command == "!tb help":
            await message.channel.send("Available commands: !tb help, !tb setchannel <id>, !tb setdiscordchannel <id>, !tb test, !tb info, !tb remove, !tb about")

        elif command == "!tb setchannel":
            try:
                channel_id = message.content.split()[1]
                server_id = message.guild.id
                set_server_config(server_id, channel_id, None)  # Set channel, other values None
                await message.channel.send("YouTube channel set!")
            except IndexError:
                await message.channel.send("Usage: !tb setchannel <youtube_channel_id>")
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")

        elif command == "!tb setdiscordchannel":
            try:
                discord_channel_id = message.content.split()[1]
                server_id = message.guild.id
                set_server_config(server_id, None, discord_channel_id) # Set channel, other values None
                await message.channel.send("Discord channel set!")
            except IndexError:
                await message.channel.send("Usage: !tb setdiscordchannel <discord_channel_id>")
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")

        elif command == "!tb test":
            config = get_server_config(message.guild.id)
            if config and config.get("youtube_channel_id") and config.get("discord_channel_id"):
                await message.channel.send("Testing connection... (This may take a moment)")
                await check_for_new_videos(message.guild.id)
            else:
                await message.channel.send("Please set both YouTube and Discord channels first.")

        elif command == "!tb info":
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

        elif command == "!tb remove":
            server_id = message.guild.id
            if server_id in server_configs:
                del server_configs[server_id]
                await message.channel.send("YouTube channel and Discord channel removed for this server.")
            else:
                await message.channel.send("No configuration found for this server.")

        elif command == "!tb about":
            await message.channel.send("BotTuber - A YouTube video posting bot for Discord. Created by SigmaSauer07.")

client.run(DISCORD_TOKEN)