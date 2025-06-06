import os
import ffmpeg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import time
import urllib.request
import traceback
import re
from aiohttp import web
import asyncio

# Bot token and owner ID from environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))

# Telegram message character limit
TELEGRAM_MESSAGE_LIMIT = 4096

# Car image URL
CAR_IMAGE_URL = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c"

# List to store channel names (in-memory, will reset on bot restart)
channel_list = []

# Function to truncate a message to fit within Telegram's limit
def truncate_message(message, max_length=TELEGRAM_MESSAGE_LIMIT - 100):
    if len(message) <= max_length:
        return message
    return message[:max_length] + "... (message truncated)"

# Function to validate URL accessibility
def check_url_accessibility(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://livegeoroueu.akamaized.net',
            }
        )
        with urllib.request.urlopen(req) as response:
            return response.getcode() == 200, None
    except Exception as e:
        return False, str(e)

# Function to restrict commands to the owner
def restrict_to_owner(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            await update.message.reply_text("🚫 Access denied! This command is only for the bot owner.")
            print(f"Unauthorized access attempt by user ID {user_id} for command: {update.message.text}")
            return
        return await handler(update, context)
    return wrapper

# Function to handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        welcome_text = (
            "🎉 *Welcome to the Stream Recorder Bot!* 🎉\n\n"
            "🚗 Ready to capture your favorite streams with ease? Here's how to get started:\n"
            "1️⃣ Use `/record` followed by your M3U8 URL (Owner only)\n"
            "2️⃣ Choose your recording duration from the options\n"
            "3️⃣ Select your preferred quality (Original only)\n"
            "4️⃣ Wait for the magic to happen ✨\n"
            "5️⃣ Download your recorded video! 📹\n\n"
            "🔒 Owner-only feature: Add a channel with `/addchannel <channel_link>`\n\n"
            "*Let’s roll! 🚀*"
        )
        await update.message.reply_text(truncate_message(welcome_text), parse_mode='Markdown')
        try:
            await update.message.reply_photo(photo=CAR_IMAGE_URL, caption="Here’s a beautiful car to get you in the mood! 🏎️")
        except Exception as e:
            error_msg = f"Error sending car image: {str(e)}. Enjoy the bot anyway! 😊"
            await update.message.reply_text(truncate_message(error_msg))
            print(f"Error sending car image: {error_msg}")
            print(traceback.format_exc())
    except Exception as e:
        error_msg = f"Error in /start command: {str(e)}"
        await update.message.reply_text(truncate_message(error_msg))
        print(f"Error in /start: {error_msg}")
        print(traceback.format_exc())

# Function to handle the /addchannel command
@restrict_to_owner
async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Please provide a Telegram channel link after /addchannel. Example: /addchannel https://t.me/channelname")
            return
        channel_link = context.args[0]
        match = re.search(r't\.me/([a-zA-Z0-9_]+)', channel_link)
        if not match:
            await update.message.reply_text("Invalid channel link format. Please use a link like https://t.me/channelname")
            return
        channel_name = match.group(1)
        if channel_name in channel_list:
            await update.message.reply_text(f"Channel @{channel_name} is already added!")
            return
        channel_list.append(channel_name)
        await update.message.reply_text(f"✅ Channel @{channel_name} added successfully!\nCurrent channels: {', '.join(['@' + ch for ch in channel_list])}")
        print(f"Channel added: @{channel_name}, Current channels: {channel_list}")
    except Exception as e:
        error_msg = f"Error in /addchannel command: {str(e)}"
        await update.message.reply_text(truncate_message(error_msg))
        print(f"Error in /addchannel: {error_msg}")
        print(traceback.format_exc())

# Function to handle the /record command
@restrict_to_owner
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Please provide an M3U8 URL after /record. Example: /record <M3U8_URL>")
            return
        m3u8_url = context.args[0]
        context.user_data['m3u8_url'] = m3u8_url
        is_valid, error = check_url_accessibility(m3u8_url)
        if not is_valid:
            error_msg = f"Cannot access the URL: {error}. Please check the URL and try again."
            await update.message.reply_text(truncate_message(error_msg))
            return
        keyboard = [
            [
                InlineKeyboardButton("10 sec", callback_data="duration_10"),
                InlineKeyboardButton("30 sec", callback_data="duration_30"),
                InlineKeyboardButton("1 min", callback_data="duration_60"),
            ],
            [
                InlineKeyboardButton("5 min", callback_data="duration_300"),
                InlineKeyboardButton("10 min", callback_data="duration_600"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please select the recording duration (max 10 min):", reply_markup=reply_markup)
    except Exception as e:
        error_msg = f"Error in /record command: {str(e)}"
        await update.message.reply_text(truncate_message(error_msg))
        print(f"Error in /record: {error_msg}")
        print(traceback.format_exc())

# Function to handle button clicks for duration
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        print(f"Error answering callback query: {str(e)}")
        print(traceback.format_exc())
        return
    callback_data = query.data
    try:
        user_id = query.from_user.id
        if user_id != OWNER_ID:
            await query.message.reply_text("🚫 Access denied! This bot is for the owner only.")
            print(f"Unauthorized button interaction by user ID {user_id}")
            return
        if callback_data.startswith("duration_"):
            duration = int(callback_data.split("_")[1])
            m3u8_url = context.user_data.get('m3u8_url')
            if not m3u8_url:
                await query.message.reply_text("Session expired. Please start again with /record <M3U8_URL>")
                return
            timestamp = int(time.time())
            output_file = f"/tmp/recording_{timestamp}.mp4"
            await query.message.reply_text("Recording started... Please wait.")
            headers = "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\r\nReferer: https://livegeoroueu.akamaized.net"
            try:
                input_stream = ffmpeg.input(m3u8_url, t=duration, headers=headers)
                output_stream = ffmpeg.output(
                    input_stream,
                    output_file,
                    **{'c:v': 'copy'},
                    **{'c:a': 'copy'},
                    f='mp4'
                )
                print(f"Running FFmpeg command for URL: {m3u8_url}, Duration: {duration}s")
                ffmpeg.run(output_stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            except ffmpeg.Error as e:
                stdout = e.stdout.decode('utf-8', errors='replace') if e.stdout else "No stdout captured."
                stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else "No stderr captured."
                error_message = f"FFmpeg stdout: {stdout}\nFFmpeg stderr: {stderr}"
                truncated_message = truncate_message(error_message)
                await query.message.reply_text(f"Error recording the stream: {truncated_message}. Please check the M3U8 URL and try again.")
                print(f"FFmpeg Error: {error_message}")
                print(traceback.format_exc())
                return
            except Exception as e:
                error_message = str(e)
                truncated_message = truncate_message(error_message)
                await query.message.reply_text(f"Unexpected error during recording: {truncated_message}. Please try again.")
                print(f"Unexpected Recording Error: {error_message}")
                print(traceback.format_exc())
                return
            try:
                file_size = os.path.getsize(output_file) / (1024 * 1024)
            except Exception as e:
                error_msg = f"Error accessing recorded file: {str(e)}"
                await query.message.reply_text(truncate_message(error_msg))
                print(f"File Access Error: {error_msg}")
                print(traceback.format_exc())
                return
            if file_size > 2000:
                await query.message.reply_text("Recording completed, but the file is too large to upload (>2GB). Please try a shorter duration.")
                try:
                    os.remove(output_file)
                except Exception as e:
                    print(f"Error deleting oversized file {output_file}: {str(e)}")
                context.user_data.clear()
                return
            success_msg = f"✅ Recording completed and uploaded...\n\nFile: {output_file}\nSize: {file_size:.1f} MB\nDuration: {duration} seconds\nQuality: Original"
            await query.message.reply_text(truncate_message(success_msg))
            try:
                await query.message.reply_text("Uploading the recorded video...")
                with open(output_file, 'rb') as video:
                    await query.message.reply_document(document=video, filename=output_file)
            except Exception as e:
                error_msg = f"Error uploading the video: {str(e)}"
                await query.message.reply_text(truncate_message(error_msg))
                print(f"Upload Error: {error_msg}")
                print(traceback.format_exc())
                return
            try:
                os.remove(output_file)
            except Exception as e:
                print(f"Error deleting file {output_file}: {str(e)}")
            context.user_data.clear()
    except Exception as e:
        error_msg = f"Error in button callback: {str(e)}"
        await query.message.reply_text(truncate_message(error_msg))
        print(f"Button Callback Error: {error_msg}")
        print(traceback.format_exc())

# Dummy HTTP server to satisfy Render's port requirement
async def handle_root(request):
    return web.Response(text="Stream Recorder Bot is running!")

async def run_http_server():
    app = web.Application()
    app.add_routes([web.get('/', handle_root)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"HTTP server running on port {port}")

# Main function to run both the bot and HTTP server
async def main():
    try:
        # Start the Telegram bot
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("addchannel", add_channel))
        application.add_handler(CommandHandler("record", record))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Start both the HTTP server and bot polling concurrently
        print("Starting bot and HTTP server...")
        await asyncio.gather(
            run_http_server(),
            application.run_polling()
        )
    except Exception as e:
        print(f"Error starting bot or HTTP server: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
