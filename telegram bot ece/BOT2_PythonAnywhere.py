#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import atexit
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import telegram.error
from dotenv import load_dotenv

print(f"BOT2_PythonAnywhere.py script started execution at {datetime.now()}.") # DEBUG PRINT

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── Path Setup ─────────────────────────────────────────────────────────────
# Get the absolute path to the directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Load Bot Token ──────────────────────────────────────────────────────────
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("⚠️ TELEGRAM_TOKEN not found in .env file")
    raise RuntimeError("⚠️ Please set TELEGRAM_TOKEN in your .env file.")

# ─── File Locking Mechanism ───────────────────────────────────────────────────
# Global variable to store the lock file handle
lock_file = None
lock_filename = None

def acquire_lock():
    """
    Try to acquire a lock to ensure only one instance of the bot is running.
    Returns True if lock was acquired, False otherwise.
    Uses file-based locking compatible with PythonAnywhere.
    """
    global lock_file, lock_filename
    
    # Create a lock file in the same directory as the script
    lock_filename = os.path.join(BASE_DIR, "bot.lock")
    
    try:
        # Try to open the file in exclusive creation mode
        # This will fail if the file already exists
        lock_file = open(lock_filename, "x")
        
        # Write the process ID to the file
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        
        # Register cleanup function
        atexit.register(release_lock)
        
        logger.info("Lock acquired successfully. This is the only running instance.")
        return True
        
    except FileExistsError:
        # Lock file exists, check if it's stale
        try:
            with open(lock_filename, "r") as f:
                pid = int(f.read().strip())
            
            # PythonAnywhere uses Linux, so we can use os.kill to check process
            try:
                # Send signal 0 to check if process exists
                os.kill(pid, 0)
                logger.warning(f"ERROR: Another instance (PID {pid}) is already running.")
                return False
            except OSError:
                # Process doesn't exist, the lock is stale
                os.remove(lock_filename)
                # Try again
                return acquire_lock()
                
        except (ValueError, IOError):
            # Couldn't read PID or file is corrupted
            os.remove(lock_filename)
            # Try again
            return acquire_lock()
            
        except Exception as e:
            logger.error(f"ERROR: Failed to check lock: {e}")
            return False

def release_lock():
    """
    Release the lock file.
    """
    global lock_file, lock_filename
    
    if lock_file:
        lock_file.close()
        
    if lock_filename and os.path.exists(lock_filename):
        try:
            os.remove(lock_filename)
            logger.info("Lock released.")
        except Exception as e:
            logger.warning(f"Warning: Failed to remove lock file: {e}")

# ─── Command Handlers ───────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send greeting message when /start command is issued.
    """
    user = update.effective_user
    await update.message.reply_text(
        f"Hello, {user.first_name}! 👋\n\n"
        f"Welcome to the ECE 6th Semester Bot!\n\n"
        f"Use /notes to browse lecture notes\n"
        f"Use /papers to browse previous year papers\n\n"
        f"Use /help to see all available commands."
    )
    logger.info(f"User {user.id} ({user.first_name}) started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send help message when /help command is issued.
    """
    await update.message.reply_text(
        "ECE 6th Semester Bot Help:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/notes - Browse lecture notes\n"
        "/papers - Browse previous year papers"
    )
    logger.info(f"User {update.effective_user.id} requested help")

async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show available subjects for notes when /notes command is issued.
    """
    keyboard = build_subject_keyboard("notes")
    await update.message.reply_text(
        "📚 Please select a subject to view notes:",
        reply_markup=keyboard
    )
    logger.info(f"User {update.effective_user.id} requested notes menu")

async def papers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show available subjects for papers when /papers command is issued.
    """
    keyboard = build_subject_keyboard("papers")
    await update.message.reply_text(
        "📝 Please select a subject to view previous year papers:",
        reply_markup=keyboard
    )
    logger.info(f"User {update.effective_user.id} requested papers menu")

# ─── Helper Functions ───────────────────────────────────────────────────────
async def send_files(chat_id: int, folder_path: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Send all files from a directory to the user recursively.
    """
    logger.info(f"Searching for files in: {folder_path}")
    all_files = []
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            all_files.append(os.path.join(root, file))
    
    # If no files found
    if not all_files:
        await context.bot.send_message(chat_id=chat_id, text="📭 No files found.")
        logger.warning(f"No files found in {folder_path}")
        return
    
    # Send a message with the number of files found
    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"Found {len(all_files)} file(s). Starting upload..."
    )
    logger.info(f"Found {len(all_files)} files in {folder_path}")
    
    # Send each file
    for file_path in all_files:
        try:
            file_name = os.path.basename(file_path)
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
            with open(file_path, "rb") as f:
                await context.bot.send_document(chat_id=chat_id, document=f, filename=file_name)
            logger.info(f"Sent file: {file_name}")
        except Exception as e:
            logger.error(f"Error sending file {file_path}: {e}")
            await context.bot.send_message(
                chat_id=chat_id, 
                text=f"❌ Error sending file: {file_path}\nError: {str(e)}"
            )
    
    # Send completion message
    await context.bot.send_message(chat_id=chat_id, text="✅ All files sent!")

def build_subject_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Build an InlineKeyboardMarkup where each subject is its own row (full-width).
    `action` should be either "notes" or "papers".
    """
    # Each inner list creates one button per row:
    buttons = [
        [InlineKeyboardButton("ARM and Embedded Systems", callback_data=f"{action}_arm")],
        [InlineKeyboardButton("Advanced Communication System", callback_data=f"{action}_acs")],
        [InlineKeyboardButton("Artificial Intelligence and Machine Learning", callback_data=f"{action}_aiml")],
        [InlineKeyboardButton("Python and Application", callback_data=f"{action}_python")],
        [InlineKeyboardButton("Java Programming", callback_data=f"{action}_java")],
    ]
    
    return InlineKeyboardMarkup(buttons)

def build_module_keyboard(action: str, subject: str) -> InlineKeyboardMarkup:
    """
    Build an InlineKeyboardMarkup for module selection.
    First row has modules 1-3, second row has modules 4-5.
    """
    keyboard = [
        # First row: Modules 1-3
        [
            InlineKeyboardButton("Module 1", callback_data=f"{action}_{subject}_module1"),
            InlineKeyboardButton("Module 2", callback_data=f"{action}_{subject}_module2"),
            InlineKeyboardButton("Module 3", callback_data=f"{action}_{subject}_module3"),
        ],
        # Second row: Modules 4-5
        [
            InlineKeyboardButton("Module 4", callback_data=f"{action}_{subject}_module4"),
            InlineKeyboardButton("Module 5", callback_data=f"{action}_{subject}_module5"),
        ],
        # Back button
        [InlineKeyboardButton("« Back to Subjects", callback_data=f"{action}_back")],
    ]
    
    return InlineKeyboardMarkup(keyboard)

# ─── Callback Handler ───────────────────────────────────────────────────────
async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle button selection from inline keyboards.
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    logger.info(f"User {user_id} selected: {data}")
    
    # Handle back button
    if data.endswith("_back"):
        parts = data.split("_")
        action = parts[0]  # "notes" or "papers"
        
        if action == "notes":
            keyboard = build_subject_keyboard("notes")
            await query.edit_message_text(
                text="📚 Please select a subject to view notes:",
                reply_markup=keyboard
            )
        else:  # action == "papers"
            keyboard = build_subject_keyboard("papers")
            await query.edit_message_text(
                text="📝 Please select a subject to view previous year papers:",
                reply_markup=keyboard
            )
        return
    
    # Parse the callback data
    parts = data.split("_")
    
    # Check if this is a module selection
    if len(parts) == 3 and parts[2].startswith("module"):
        action = parts[0]  # "notes" or "papers"
        subject = parts[1]  # subject code
        module = parts[2]   # "module1", "module2", etc.
        
        # Get appropriate folder based on action, subject, and module
        folder_name = "notes" if action == "notes" else "papers"
        folder_path = os.path.join(BASE_DIR, "data", folder_name, subject, module)
        
        # Log the folder path for debugging
        logger.info(f"Accessing folder: {folder_path}")
        
        # Check if directory exists
        if not os.path.isdir(folder_path):
            await query.edit_message_text(
                text=f"❌ Error: Folder not found for {subject} {module}.\n"
                f"Path being checked: {folder_path}"
            )
            logger.error(f"Directory not found: {folder_path}")
            return
        
        # Send all files from this folder
        await query.edit_message_text(text=f"🔍 Searching for files in {subject} {module}...")
        await send_files(chat_id, folder_path, context)
        
        # After sending files, show the module selection again
        keyboard = build_module_keyboard(action, subject)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Select another module for {subject} or go back to subjects:",
            reply_markup=keyboard
        )
        
    else:  # This is a subject selection
        action = parts[0]  # "notes" or "papers"
        subject = parts[1]  # subject code
        
        # Show module selection keyboard
        keyboard = build_module_keyboard(action, subject)
        
        await query.edit_message_text(
            text=f"Please select a module for {subject}:",
            reply_markup=keyboard
        )

# ─── Error Handler ────────────────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Log errors caused by updates.
    """
    error = context.error
    
    # Log the error
    logger.error(f"Error occurred: {error}")
    
    # Handle different types of errors
    if isinstance(error, telegram.error.NetworkError):
        logger.error("Network error occurred. Please check your internet connection.")
    elif isinstance(error, telegram.error.TimedOut):
        logger.error("Connection timed out. The server might be busy or the files might be too large.")
    elif isinstance(error, telegram.error.Conflict):
        logger.error("Update conflict occurred. Make sure only one instance of the bot is running.")
    
    # Try to notify the user about the error if possible
    try:
        if update and isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="An error occurred while processing your request. Please try again later."
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")

# ─── Main Entrypoint ─────────────────────────────────────────────────────────
def main() -> None:
    # Check if another instance is already running
    if not acquire_lock():
        logger.error("Exiting: Another instance of the bot is already running.")
        return
        
    logger.info("Starting bot with instance locking on PythonAnywhere...")
    
    # Configure the application with proper timeout and connection pool settings
    app = (ApplicationBuilder()
          .token(TOKEN)
          # Increase connection pool size for better handling of multiple requests
          .connection_pool_size(8)
          # Increase the read timeout to prevent timeouts during larger file transfers
          .read_timeout(30)
          # Increase the write timeout for sending larger files
          .write_timeout(30)
          # Increase connection timeout
          .connect_timeout(15)
          # Add request retries for network issues
          .get_updates_connect_timeout(15)
          # Enable automatic reconnection on network errors
          .get_updates_connection_pool_size(16)
          .pool_timeout(10.0)
          .build())

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("notes", notes))
    app.add_handler(CommandHandler("papers", papers))

    # Register callback handler for all button presses
    app.add_handler(CallbackQueryHandler(handle_selection))

    # Register error handler
    app.add_error_handler(error_handler)
    
    logger.info(f"Bot started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Use drop_pending_updates to avoid processing old updates when restarting the bot
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
