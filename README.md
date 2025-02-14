# BotTuber - YouTube to Discord Bot

BotTuber is a Discord bot that automatically posts new videos from a specified YouTube channel to a designated Discord channel.  It keeps your community engaged and informed about the latest content releases.

## Features

* **Automatic Video Posting:** Automatically detects new uploads on the configured YouTube channel and posts them to your Discord server.
* **Embeds:** Uses Discord embeds to display video information (title, description, thumbnail, publish date) in a visually appealing way.
* **Easy Setup:** Simple commands to configure the YouTube channel and Discord channel.
* **Informative Commands:** Provides commands to view channel information, remove configurations, and learn about the bot.

## Commands

* `!tb help`: Displays this help message.
* `!tb setchannel <youtube_channel_id>`: Sets the YouTube channel to monitor. Replace `<youtube_channel_id>` with the actual channel ID.
* `!tb setdiscordchannel <discord_channel_id>`: Sets the Discord channel where new videos will be posted. Replace `<discord_channel_id>` with the channel ID.
* `!tb test`: Tests the connection to the specified YouTube channel and Discord channel. Posts a test message.
* `!tb info`: Displays information about the currently configured YouTube channel.
* `!tb remove`: Removes the configured YouTube channel and stops automatic posting.
* `!tb about`: Displays information about BotTuber.

## Setup

1. **Invite the Bot:** Invite BotTuber to your Discord server using the invite link: [Insert your bot's invite link here].
2. **Set the YouTube Channel:** Use the `!tb setchannel <youtube_channel_id>` command.
3. **Set the Discord Channel:** Use the `!tb setdiscordchannel <discord_channel_id>` command.
4. **Test the Connection:** Use the `!tb test` command to verify that the bot is working.

## Finding the Channel ID

The easiest way to find a YouTube channel ID is to go to the channel's page, view the page source (right-click, "View Page Source"), and search for `"channel_id": "UCxxxxxxxxxxxxx"`.

## Running the Bot (For Developers)

1. **Clone the Repository:**
   ```bash
   git clone [Your Repository URL]
Install Dependencies:

Bash

pip install -r requirements.txt  # Create a requirements.txt file with the necessary libraries
Set Environment Variables: Create a .env file in the same directory as your bot's script and add your Discord bot token:

DISCORD_TOKEN="YOUR_ACTUAL_TOKEN"
Run the Bot:

Bash

python your_bot_script_name.py  # Replace with your script's name
Contributing
Contributions are welcome!  Please open an issue or submit a pull request.

Support
Join our support server for help, bug reports, and suggestions: [Link to your support server]

License
[Choose a license - e.g., MIT License]

Acknowledgements
Thanks to the developers of the discord.py and youtube-dl libraries.
TODO
Implement database integration for persistent server configurations.
Add more robust error handling and logging.
Implement rate limiting strategies.
... other improvements

**Key Improvements and Explanations:**

* **Clear Structure:**  The README is organized with clear headings, making it easy to navigate.
* **Comprehensive Information:**  It includes sections for features, commands, setup instructions, finding the channel ID, running the bot (for developers), contributing, support, license, and acknowledgments.
* **Placeholders:**  I've included placeholders for important information like the invite link, repository URL, support server link, license, and TODOs.  Make sure to replace these with your actual information.
* **Requirements File:**  Added a note about creating a `requirements.txt` file.  This file should list all the Python libraries your bot depends on (e.g., `discord.py`, `youtube-dl`, `python-dotenv`).  This makes it easy for others to install the necessary dependencies.
* **TODO Section:**  The TODO section reminds you of the important next steps, like database integration, error handling, and rate limiting.
* **Standard Practices:**  The README follows common conventions and best practices for open-source projects.

**Next Steps:**

1. **Replace Placeholders:**  Fill in all the placeholder information.
2. **Create `requirements.txt`:** Create this file in the same directory as your bot's script.  List all the libraries your bot uses, one per line (e.g., `discord.py`, `youtube-dl`, `python-dotenv`).  You can generate this file automatically using `pip freeze > requirements.txt`.
3. **Choose a License:**  Decide on a license for your bot (e.g., MIT, GPL, Apache) and add the appropriate license text to your README.
4. **Consider Adding Screenshots/GIFs:**  Visuals can make your README more engaging.  Consider adding screenshots or GIFs of your bot in action.
