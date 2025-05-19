# Discord OpenAI Chat Bot

A simple Discord bot that responds to all messages using OpenAI's GPT model.

---

## Features

- Listens to all messages in channels it has access to
- Sends each message to OpenAI and replies with the generated response

---

## Getting Started

### 1. Clone the Repository

```sh
git clone https://github.com/geekhostuk/Botty.git
cd Botty
```

### 2. Install Dependencies

```sh
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

- Copy `.env.example` to `.env`:
  ```sh
  cp .env.example .env
  ```
- Fill in your Discord bot token and OpenAI API key in `.env`:
  ```
  DISCORD_TOKEN=your-discord-bot-token-here
  OPENAI_API_KEY=your-openai-api-key-here
  ```

### 4. Enable "MESSAGE CONTENT INTENT" in Discord Developer Portal

- Go to your application in the [Discord Developer Portal](https://discord.com/developers/applications).
- Navigate to the **Bot** tab.
- Under **Privileged Gateway Intents**, enable **MESSAGE CONTENT INTENT**.

### 5. Invite the Bot to Your Server

1. **Get your Bot's Client ID:**
   - In the Developer Portal, select your application.
   - Go to the "General Information" tab and copy the "Application ID" (Client ID).

2. **Generate an Invite Link:**
   - Replace `YOUR_CLIENT_ID` in the URL below with your actual Client ID:
     ```
     https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot&permissions=274877990912
     ```
   - The permission integer grants:
     - Read Messages/View Channels
     - Send Messages
     - Read Message History

3. **Open the link in your browser and select your server to invite the bot.**
   - You must have "Manage Server" permissions.

---

## Running the Bot

### Locally

```sh
python bot.py
```

### With Docker

1. **Build the Docker image:**
   ```sh
   docker build -t discord-botty .
   ```

2. **Run the container with your `.env` file:**
   ```sh
   docker run --env-file .env discord-botty
   ```
   - Ensure your `.env` file is in the same directory as your Dockerfile, or provide the full path.

3. **Run the container by specifying environment variables directly:**
   ```sh
   docker run -e DISCORD_TOKEN=your-discord-bot-token-here -e OPENAI_API_KEY=your-openai-api-key-here discord-botty
   ```
   - This method does not require a `.env` file. Replace the values with your actual tokens.

4. **Stopping the bot:**
   - Use `docker ps` to find the container ID, then:
     ```sh
     docker stop <container_id>
     ```

---

## Troubleshooting & Error Handling

- **Bot not appearing in server:**  
  - Ensure you completed the invite process and have the correct permissions.
  - Double-check your `DISCORD_TOKEN` in `.env` or your Docker command.
  - Make sure the bot is running without errors.

- **Bot not responding to messages:**  
  - Confirm "MESSAGE CONTENT INTENT" is enabled in the Developer Portal.
  - Check for errors in the terminal where the bot is running.
  - Ensure the bot has permission to read/send messages in the channel.

- **OpenAI errors:**  
  - Verify your `OPENAI_API_KEY` is correct and has sufficient quota.
  - Check for API rate limits or invalid key errors in the logs.

- **General tips:**  
  - Restart the bot after making changes to `.env` or code.
  - Review logs for stack traces or error messages.

---

## Configuration

- The bot uses the `gpt-4o` model by default. You can change this in [`bot.py`](bot.py:1) if you have access to other models.
- The bot will reply to every message it can see, except its own.

---

## Repository

This project is hosted at [https://github.com/geekhostuk/Botty](https://github.com/geekhostuk/Botty)

## License

MIT