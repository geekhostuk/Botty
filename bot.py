import os
import logging
from collections import defaultdict, deque
from typing import Dict, List, Any

import discord
from discord.ext import commands
import openai
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
        history.append(message)

    def as_list(self, channel_id: int) -> List[dict]:
        return list(self.get(channel_id))

history_manager = ChannelHistory(MAX_HISTORY)

# --- Bot Events ---

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from bots (including itself)
    if message.author.bot:
        return

    channel_id = message.channel.id
    user_message = message.content.strip()
    if not user_message:
        return

    # Add user message to history
    history_manager.append(channel_id, {"role": "user", "content": user_message})

    # Call OpenAI API
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
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
        reply = "Sorry, I couldn't reach my brain (OpenAI API error). Try again later!"

    # Send reply
    try:
        await message.channel.send(reply)
    except discord.DiscordException as e:
        logger.error(f"Failed to send message: {e}")

# --- Main Entrypoint ---

if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}")