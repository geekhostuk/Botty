import os
import logging
from collections import defaultdict, deque
from typing import Dict, List, Any

import discord
from discord.ext import commands
import openai
import asyncio
from discord.ext import tasks
from dotenv import load_dotenv

# --- Configuration & Logging ---

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_HISTORY = 100

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("botty")

import json
from datetime import datetime

LOGS_DIR = "logs"
ACTIVITY_LOG = os.path.join(LOGS_DIR, "activity.log")
ERROR_LOG = os.path.join(LOGS_DIR, "errors.log")

def log_activity(data: dict):
    """Append a JSON line to the activity log."""
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"
CONFIG_FILE = os.path.join(LOGS_DIR, "bot_config.json")

def load_bot_config():
    if not os.path.exists(CONFIG_FILE):
        return {"model": "gpt-4o", "autoreply": True}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load bot config: {e}")
        return {"model": "gpt-4o", "autoreply": True}

def save_bot_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save bot config: {e}")

bot_config = load_bot_config()
DAILYJOKE_FILE = os.path.join(LOGS_DIR, "dailyjoke_channels.json")

def load_dailyjoke_channels():
    if not os.path.exists(DAILYJOKE_FILE):
        return {}
    try:
        with open(DAILYJOKE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load dailyjoke channels: {e}")
        return {}

def save_dailyjoke_channels(data):
    try:
        with open(DAILYJOKE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save dailyjoke channels: {e}")

dailyjoke_channels = load_dailyjoke_channels()
SCHEDULED_MESSAGES_FILE = os.path.join(LOGS_DIR, "scheduled_messages.json")

def load_scheduled_messages():
    if not os.path.exists(SCHEDULED_MESSAGES_FILE):
        return []
    try:
        with open(SCHEDULED_MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load scheduled messages: {e}")
        return []

def save_scheduled_messages(messages):
    try:
        with open(SCHEDULED_MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save scheduled messages: {e}")

scheduled_messages = load_scheduled_messages()

@tasks.loop(minutes=1)
async def scheduled_message_task():
    now = datetime.utcnow()
    to_send = []
    to_keep = []
    for msg in scheduled_messages:
        send_time = datetime.fromisoformat(msg["send_time"])
        if send_time <= now:
            to_send.append(msg)
            # If recurring, reschedule for next day
            if msg.get("recurring") == "daily":
                next_time = send_time + timedelta(days=1)
                msg["send_time"] = next_time.isoformat()
                to_keep.append(msg)
        else:
            to_keep.append(msg)
    # Save updated schedule
    if to_send or len(to_keep) != len(scheduled_messages):
        save_scheduled_messages(to_keep)
        scheduled_messages.clear()
        scheduled_messages.extend(to_keep)
# Handle dailyjoke
    import random
    from datetime import timedelta

    def random_joke_time(now_utc):
        # UK time: UTC+1 in summer, UTC in winter (simplified: always use UTC+1 for now)
        base_date = now_utc.date()
        hour = random.randint(9, 16)  # 9am to 4pm start
        minute = random.randint(0, 59)
        send_time = datetime(
            year=base_date.year, month=base_date.month, day=base_date.day,
            hour=hour-1, minute=minute  # UTC+1 for UK time
        )
        if send_time <= now_utc:
            send_time += timedelta(days=1)
        return send_time

    for channel_id, info in dailyjoke_channels.items():
        if not info.get("enabled"):
            continue
        next_time = info.get("next_time")
        if not next_time:
            # Schedule for today
            info["next_time"] = random_joke_time(now).isoformat()
            continue
        try:
            joke_time = datetime.fromisoformat(next_time)
        except Exception:
            joke_time = random_joke_time(now)
            info["next_time"] = joke_time.isoformat()
        if joke_time <= now:
            # Generate a random fact in a jokey way
            facts = [
                "Did you know honey never spoils? Unlike my patience for slow Wi-Fi.",
                "Bananas are berries, but strawberries aren't. The world is a lie.",
                "Octopuses have three hearts. That's two more than my ex gave me.",
                "A group of flamingos is called a 'flamboyance.' Just like my Saturday nights.",
                "Wombat poop is cube-shaped. Nature's way of keeping things... square.",
                "The unicorn is Scotland’s national animal. Because why not?",
                "Mosquitoes are attracted to people who just ate bananas. So, snack wisely.",
                "Cows have best friends and get stressed when separated. Moo-ving, isn’t it?",
                "A snail can sleep for three years. Same, after a big lunch.",
                "The inventor of the frisbee was turned into a frisbee after he died. Talk about flying off the handle."
            ]
            fact = random.choice(facts)
            channel = bot.get_channel(int(channel_id))
            if channel:
                try:
                    await channel.send(f"🤓 Daily Fact: {fact}")
                    log_activity({
                        "event": "dailyjoke_sent",
                        "channel_id": channel_id,
                        "content": fact
                    })
                except Exception as e:
                    logger.error(f"Failed to send dailyjoke: {e}")
                    log_error({
                        "event": "dailyjoke_error",
                        "error": str(e),
                        "channel_id": channel_id,
                        "content": fact
                    })
            # Schedule next joke
            next_joke = random_joke_time(now + timedelta(days=1))
            info["next_time"] = next_joke.isoformat()
    save_dailyjoke_channels(dailyjoke_channels)
from discord.ext.commands import has_permissions, CheckFailure

@bot.group(name="admin", invoke_without_command=True, help="Admin commands. Use !admin <subcommand>")
@has_permissions(administrator=True)
async def admin_group(ctx):
    await ctx.send("Available admin commands: clearhistory, setmodel, listmodels, autoreply")

@admin_group.command(name="clearhistory", help="Clear chat history for this channel")
async def clearhistory(ctx):
    channel_id = ctx.channel.id
    if hasattr(history_manager, "histories") and channel_id in history_manager.histories:
        history_manager.histories[channel_id].clear()
        await ctx.send("Chat history cleared for this channel.")
        log_activity({
            "event": "admin_clearhistory",
            "channel_id": str(channel_id),
            "user_id": str(ctx.author.id),
            "username": str(ctx.author)
        })
    else:
        await ctx.send("No history found for this channel.")

@admin_group.command(name="setmodel", help="Set the OpenAI model used for chat (e.g., gpt-4o, gpt-3.5-turbo)")
async def setmodel(ctx, model: str):
    bot_config["model"] = model
    save_bot_config(bot_config)
    await ctx.send(f"OpenAI model set to: {model}")
    log_activity({
        "event": "admin_setmodel",
        "model": model,
        "user_id": str(ctx.author.id),
        "username": str(ctx.author)
    })

@admin_group.command(name="listmodels", help="List available OpenAI models")
async def listmodels(ctx):
    try:
        models = openai.models.list()
        model_names = [m.id for m in models.data]
        await ctx.send("Available OpenAI models:\n" + "\n".join(model_names))
    except Exception as e:
        await ctx.send("Failed to fetch models from OpenAI.")
        log_error({
            "event": "admin_listmodels_error",
            "error": str(e),
            "user_id": str(ctx.author.id),
            "username": str(ctx.author)
        })

@admin_group.command(name="autoreply", help="Turn auto-reply to all messages on or off")
async def autoreply(ctx, mode: str):
    mode = mode.lower()
    if mode == "on":
        bot_config["autoreply"] = True
        save_bot_config(bot_config)
        await ctx.send("Auto-reply to all messages is now ON.")
    elif mode == "off":
        bot_config["autoreply"] = False
        save_bot_config(bot_config)
        await ctx.send("Auto-reply to all messages is now OFF.")
    else:
        await ctx.send("Usage: !admin autoreply on|off")
    log_activity({
        "event": "admin_autoreply",
        "mode": mode,
        "user_id": str(ctx.author.id),
        "username": str(ctx.author)
    })

@admin_group.error
async def admin_group_error(ctx, error):
    if isinstance(error, CheckFailure):
        await ctx.send("You must be an administrator to use admin commands.")
    # Send messages
    for msg in to_send:
        channel = bot.get_channel(int(msg["channel_id"]))
        if channel:
            try:
                await channel.send(msg["content"])
                log_activity({
                    "event": "scheduled_message_sent",
                    "channel_id": msg["channel_id"],
                    "content": msg["content"],
                    "recurring": msg.get("recurring", "none")
                })
            except Exception as e:
                logger.error(f"Failed to send scheduled message: {e}")
                log_error({
                    "event": "scheduled_message_error",
                    "error": str(e),
                    "channel_id": msg["channel_id"],
                    "content": msg["content"]
                })
    try:
        with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to activity log: {e}")

def log_error(data: dict):
    """Append a JSON line to the error log."""
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to error log: {e}")
if not DISCORD_TOKEN or not OPENAI_API_KEY:
    logger.error("Please set DISCORD_TOKEN and OPENAI_API_KEY in your .env file.")
    exit(1)

openai.api_key = OPENAI_API_KEY

# --- Discord Bot Setup ---

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- Message History Management ---

class ChannelHistory:
    """
    Maintains a fixed-length message history per channel.
    """
    def __init__(self, maxlen: int):
        self.histories: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=maxlen + 1)  # +1 for system prompt
        )
        self.system_prompt = {
            "role": "system",
            "content": (
                "Prompt for Botty (Discord Bot):\n\n"
                "You are Botty, a helpful and witty Discord bot. Your main role is to assist users with their questions and commands, "
                "but you never miss a chance to crack a joke or respond with dry, sarcastic humour. You're clever, quick-witted, and always "
                "stay just on the right side of cheeky. While you're always willing to help, your responses should carry a light, humorous tone — "
                "think helpful assistant meets stand-up comedian.\n\n"
                "Guidelines for your responses:\n"
                "- Always provide useful and accurate information.\n"
                "- Where appropriate, add a sarcastic remark, clever joke, or playful tease.\n"
                "- Never be offensive, rude, or insulting — keep it friendly and fun.\n"
                "- Tailor your humour to be suitable for a general audience (PG-rated).\n"
                "- If a user is upset or frustrated, dial down the sarcasm and be more supportive — but still with your signature personality.\n\n"
                "Example:\n"
                "User: \"Botty, how do I reset my password?\"\n"
                "Botty: \"Ah yes, the age-old struggle — forgetting your own password. Classic. No worries though, just head to your settings and click 'Reset Password'. Try not to forget it again this time.\""
            )
        }

    def get(self, channel_id: int) -> deque:
        history = self.histories[channel_id]
        if not history or history[0] != self.system_prompt:
            history.clear()
            history.append(self.system_prompt)
        return history

    def append(self, channel_id: int, message: dict) -> None:
        history = self.get(channel_id)
@bot.command(name="dailyjoke", help="Turn daily random fact joke on or off for this channel. Usage: !dailyjoke on|off")
async def dailyjoke_command(ctx, mode: str):
    """
    Enable or disable daily random fact jokes in this channel.
    When enabled, a random fact in a jokey way will be sent at a random time between 9am–5pm UK time each day.
    """
    import random
    from datetime import timedelta, time as dtime

    channel_id = str(ctx.channel.id)
    mode = mode.lower()
    now_utc = datetime.utcnow()

    def next_joke_time():
        # UK time: UTC+1 in summer, UTC in winter (simplified: always use UTC+1 for now)
        base_date = now_utc.date()
        hour = random.randint(9, 16)  # 9am to 4pm start
        minute = random.randint(0, 59)
        send_time = datetime(
            year=base_date.year, month=base_date.month, day=base_date.day,
            hour=hour-1, minute=minute  # UTC+1 for UK time
        )
        if send_time <= now_utc:
            send_time += timedelta(days=1)
        return send_time.isoformat()

    if mode == "on":
        dailyjoke_channels[channel_id] = {
            "enabled": True,
            "next_time": next_joke_time()
        }
        save_dailyjoke_channels(dailyjoke_channels)
        await ctx.send("Daily joke is now ON for this channel. You'll get a random fact in a jokey way each day between 9am–5pm UK time.")
        log_activity({
            "event": "dailyjoke_enabled",
            "channel_id": channel_id,
            "channel_name": str(ctx.channel),
            "user_id": str(ctx.author.id),
            "username": str(ctx.author),
            "next_time": dailyjoke_channels[channel_id]["next_time"]
        })
    elif mode == "off":
        if channel_id in dailyjoke_channels:
            dailyjoke_channels[channel_id]["enabled"] = False
            save_dailyjoke_channels(dailyjoke_channels)
        await ctx.send("Daily joke is now OFF for this channel.")
        log_activity({
            "event": "dailyjoke_disabled",
            "channel_id": channel_id,
            "channel_name": str(ctx.channel),
            "user_id": str(ctx.author.id),
            "username": str(ctx.author)
        })
    else:
        await ctx.send("Usage: !dailyjoke on|off")
        history.append(message)

    def as_list(self, channel_id: int) -> List[dict]:
        return list(self.get(channel_id))

history_manager = ChannelHistory(MAX_HISTORY)

# --- Bot Events ---

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
if not scheduled_message_task.is_running():
        scheduled_message_task.start()

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from bots (including itself)
    if message.author.bot:
        return
@bot.command(name="schedule", help="Schedule a message. Usage: !schedule 09:00 Hello world! [daily]")
async def schedule_command(ctx, time: str, *, message_and_recur: str):
    """
    Schedule a message to be sent at a specific time (UTC, 24h format).
    Optionally add 'daily' at the end for recurring messages.
    Example: !schedule 09:00 Hello everyone! daily
    """
    from datetime import timedelta

    user = ctx.author
    channel = ctx.channel

    # Parse recurrence
    parts = message_and_recur.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].lower() == "daily":
        message = parts[0]
        recurring = "daily"
    else:
        message = message_and_recur
        recurring = None

    # Parse time (UTC)
    try:
        hour, minute = map(int, time.split(":"))
        now = datetime.utcnow()
        send_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if send_time <= now:
            send_time += timedelta(days=1)
    except Exception:
        await ctx.send("Invalid time format. Use HH:MM in 24h UTC (e.g., 09:00).")
        return

    # Store scheduled message
    msg = {
        "channel_id": str(channel.id),
        "content": message,
        "send_time": send_time.isoformat(),
        "recurring": recurring
    }
    scheduled_messages.append(msg)
    save_scheduled_messages(scheduled_messages)
    log_activity({
        "event": "scheduled_message_created",
        "user_id": str(user.id),
        "username": str(user),
        "channel_id": str(channel.id),
        "channel_name": str(channel),
        "content": message,
        "send_time": send_time.isoformat(),
        "recurring": recurring or "none"
    })
    await ctx.send(f"Scheduled message for {send_time.strftime('%H:%M UTC')} ({'daily' if recurring else 'one-off'}): {message}")

    channel_id = message.channel.id
    user_message = message.content.strip()
    if not user_message:
        return

    # Only auto-reply if enabled in config
    if not bot_config.get("autoreply", True):
        return

    # Log user message activity
    log_activity({
        "event": "user_message",
        "user_id": str(message.author.id),
        "username": str(message.author),
        "channel_id": str(message.channel.id),
        "channel_name": str(message.channel),
        "content": user_message[:200]  # Truncate for log
    })

    # Add user message to history
    history_manager.append(channel_id, {"role": "user", "content": user_message})

    # Call OpenAI API
    try:
        response = openai.chat.completions.create(
            model=bot_config.get("model", "gpt-4o"),
            messages=history_manager.as_list(channel_id),
            max_tokens=150,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        if not reply:
            reply = "Hmm, I seem to have lost my train of thought. Try again?"
        # Add assistant reply to history
        history_manager.append(channel_id, {"role": "assistant", "content": reply})
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        log_error({
            "event": "openai_api_error",
            "error": str(e),
            "user_id": str(message.author.id),
            "username": str(message.author),
            "channel_id": str(message.channel.id),
            "channel_name": str(message.channel),
            "user_message": user_message[:200]
        })
        reply = "Sorry, I couldn't reach my brain (OpenAI API error). Try again later!"

    # Log bot response activity
    log_activity({
        "event": "bot_response",
        "channel_id": str(message.channel.id),
        "channel_name": str(message.channel),
        "reply": reply[:200]  # Truncate for log
    })

    # Send reply
    try:
        await message.channel.send(reply)
    except discord.DiscordException as e:
        logger.error(f"Failed to send message: {e}")
        log_error({
            "event": "discord_send_error",
            "error": str(e),
            "channel_id": str(message.channel.id),
            "channel_name": str(message.channel),
            "reply": reply[:200]
        })

@bot.command(name="image", help="Generate an image using OpenAI. Usage: !image <prompt>")
async def image_command(ctx, *, prompt: str):
    """Generate an image from a prompt using OpenAI's image API."""
    user = ctx.author
    channel = ctx.channel
    log_activity({
        "event": "image_request",
        "user_id": str(user.id),
        "username": str(user),
        "channel_id": str(channel.id),
        "channel_name": str(channel),
        "prompt": prompt[:200]
    })
    await ctx.trigger_typing()
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url
        await ctx.send(f"{user.mention} Here is your image for: \"{prompt}\"\n{image_url}")
        log_activity({
            "event": "image_generated",
            "user_id": str(user.id),
            "username": str(user),
            "channel_id": str(channel.id),
            "channel_name": str(channel),
            "prompt": prompt[:200],
            "image_url": image_url
        })
    except Exception as e:
        logger.error(f"OpenAI image generation error: {e}")
        log_error({
            "event": "openai_image_error",
            "error": str(e),
            "user_id": str(user.id),
            "username": str(user),
            "channel_id": str(channel.id),
            "channel_name": str(channel),
            "prompt": prompt[:200]
        })
        await ctx.send(f"Sorry, I couldn't generate an image for that prompt. (OpenAI error)")
# --- Main Entrypoint ---

if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}")