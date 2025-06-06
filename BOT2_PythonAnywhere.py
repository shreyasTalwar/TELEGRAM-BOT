# BOT2_PythonAnywhere.py - Refactored Version

import os
import sys
import asyncio
import datetime # Keep as datetime to avoid conflict with datetime class

# --- Early Global Constants & Setup -----------------------------------------
# Determine BASE_DIR early for consistent pathing across the script.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_FLOW_FILE = os.path.join(BASE_DIR, "debug_script_flow.txt")

# --- Load .env file VERY EARLY ----------------------------------------------
# This MUST happen before any os.getenv() calls that depend on .env variables.
from dotenv import load_dotenv
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

# --- Initial Debug Breadcrumbs ----------------------------------------------
def write_breadcrumb(message, mode="a"):
    """Helper function to write breadcrumbs to the debug file."""
    try:
        with open(DEBUG_FLOW_FILE, mode, encoding='utf-8') as f_flow:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            f_flow.write(f"[{timestamp}] SCRIPT_FLOW: {message}\\n")
    except Exception as e_flow:
        # Fallback to print if file writing fails
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CRITICAL_BREADCRUMB_ERROR] {message}: {e_flow}", flush=True)

write_breadcrumb(f"BASE_DIR defined: {BASE_DIR}", mode="w") # Start with "w" to overwrite
write_breadcrumb(f"Attempting to load .env from: {ENV_PATH}")
write_breadcrumb(f"load_dotenv called for {ENV_PATH}")

# --- Environment Variable Loading & Validation ------------------------------
# These os.getenv calls now happen AFTER load_dotenv() has been called.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RENDER_APP_BASE_URL = os.getenv('RENDER_APP_BASE_URL', '')  # Default to empty string for optional webhook
PORT_FROM_ENV = os.getenv('PORT', '8443') # Port for webhook, defaults to 8443

write_breadcrumb(f"After os.getenv calls. TOKEN_LOADED: {'Yes' if TELEGRAM_TOKEN else 'NO!!'}, RENDER_APP_BASE_URL: '{RENDER_APP_BASE_URL}', PORT_FROM_ENV: {PORT_FROM_ENV}")

if not TELEGRAM_TOKEN:
    error_message = "CRITICAL ERROR: TELEGRAM_TOKEN not found. Ensure it is set in your .env file and that load_dotenv() is called correctly before this check."
    write_breadcrumb(error_message)
    print(error_message, file=sys.stderr, flush=True)
    raise RuntimeError(error_message)

# --- Import Third-Party & Local Modules -------------------------------------
# These imports happen after .env loading and initial variable checks.
write_breadcrumb("Before main module imports (telegram, instance_lock, etc.)")
try:
    import telegram
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ChatAction
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
        # TypeHandler, # Removed as it was unused
    )
    import telegram.error
    from instance_lock import InstanceLock
    write_breadcrumb("Successfully imported main modules.")
except ImportError as e_import:
    critical_import_error = f"CRITICAL IMPORT ERROR: Failed to import a required module: {e_import}"
    write_breadcrumb(critical_import_error)
    print(critical_import_error, file=sys.stderr, flush=True)
    raise  # Re-raise the import error to halt execution

# --- Global Variables & Constants (Bot Specific) ----------------------------
NOTES_DATA_PATH = os.path.join(BASE_DIR, "data", "notes")
PAPERS_DATA_PATH = os.path.join(BASE_DIR, "data", "papers")

SUBJECTS = {
    "ACS": "Advanced Communication Systems",
    "ARM": "ARM Based System Design",
    "AIML": "AI and Machine Learning",
    "PYTHON": "Python and Its Applications",
    "JAVA": "Java Programming"
}

# --- Helper Functions -------------------------------------------------------
def build_subject_keyboard(action_prefix: str) -> InlineKeyboardMarkup:
    """Builds an inline keyboard with subjects for notes or papers."""
    write_breadcrumb(f"Building subject keyboard for action_prefix: {action_prefix}")
    keyboard = [
        # Callback changes to e.g. "notes_showmodules_ACS"
        [InlineKeyboardButton(name, callback_data=f"{action_prefix}_showmodules_{code}")]
        for code, name in SUBJECTS.items()
    ]
    # Assuming 'start_menu' callback is handled by start_command to show main options
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_menu")])
    return InlineKeyboardMarkup(keyboard)

def build_module_keyboard(action_prefix: str, subject_code: str) -> InlineKeyboardMarkup:
    """Builds an inline keyboard with modules (1-5) for a selected subject."""
    write_breadcrumb(f"Building module keyboard for action: {action_prefix}, subject: {subject_code}")
    keyboard = []
    row = []
    for i in range(1, 6):  # Modules 1 to 5
        button_text = f"Module {i}"
        # Callback e.g. "notes_getfiles_ACS_1" or "papers_getfiles_AIML_3"
        callback_data = f"{action_prefix}_getfiles_{subject_code}_{i}"
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        if len(row) == 2 or i == 5: # Max 2 buttons per row, or if it's the last module
            keyboard.append(row)
            row = []
    
    # Callback e.g. "notes_showsubjects" (action_prefix determines if it's notes or papers)
    keyboard.append([InlineKeyboardButton("🔙 Back to Subjects", callback_data=f"{action_prefix}_showsubjects")])
    keyboard.append([InlineKeyboardButton("🏠 Back to Main Menu", callback_data="start_menu")]) # Add main menu button
    return InlineKeyboardMarkup(keyboard)


async def send_module_files(chat_id: int, base_data_path: str, subject_code: str, module_number: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends all files from a specific subject and module folder to the user."""
    operation_start_time = datetime.datetime.now()
    module_folder_name = f"Module{module_number}" # Assuming module folders are named Module1, Module2, etc.
    specific_module_path = os.path.join(base_data_path, subject_code, module_folder_name)
    subject_name = SUBJECTS.get(subject_code, subject_code)

    write_breadcrumb(f"send_module_files: Initiated for chat_id {chat_id}, subject: {subject_code}, module: {module_number}. Path: {specific_module_path}")

    if not os.path.isdir(specific_module_path):
        write_breadcrumb(f"send_module_files: Module folder not found: {specific_module_path}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: Content folder not found for {subject_name} - {module_folder_name}.\nExpected path: {specific_module_path}")
        return

    all_files = []
    for filename in sorted(os.listdir(specific_module_path)):
        if filename.lower().endswith(('.pdf', '.doc', '.docx', '.txt', '.zip', '.rar', '.jpg', '.png')):
            all_files.append(os.path.join(specific_module_path, filename))

    if not all_files:
        write_breadcrumb(f"send_module_files: No suitable files found in {specific_module_path}")
        await context.bot.send_message(chat_id=chat_id, text=f"📭 No suitable files found for {subject_name} - {module_folder_name}.")
        return

    await context.bot.send_message(chat_id=chat_id, text=f"Found {len(all_files)} file(s) for {subject_name} - {module_folder_name}. Starting upload...")
    write_breadcrumb(f"send_module_files: Found {len(all_files)} files for {subject_name} - {module_folder_name}. User notified.")

    for file_path in all_files:
        file_name = os.path.basename(file_path)
        file_send_start_time = datetime.datetime.now()
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
            with open(file_path, "rb") as f_doc:
                await context.bot.send_document(chat_id=chat_id, document=f_doc, filename=file_name)
            file_send_duration = (datetime.datetime.now() - file_send_start_time).total_seconds()
            write_breadcrumb(f"send_module_files: Sent {file_name} to chat_id {chat_id} in {file_send_duration:.2f}s")
        except telegram.error.NetworkError as e_net:
            write_breadcrumb(f"send_module_files: NetworkError sending {file_name}: {e_net}. Retrying once...")
            await asyncio.sleep(1) # Brief pause before retry
            try:
                with open(file_path, 'rb') as f_doc_retry:
                    await context.bot.send_document(chat_id=chat_id, document=f_doc_retry, filename=file_name)
                write_breadcrumb(f"send_module_files: Successfully sent {file_name} on retry.")
            except Exception as e_retry:
                write_breadcrumb(f"send_module_files: Failed to send {file_name} on retry: {e_retry}")
                await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Failed to send {file_name} after a retry.")
        except Exception as e_gen:
            write_breadcrumb(f"send_module_files: Generic error sending {file_name}: {e_gen}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ An error occurred while sending {file_name}.")

    await context.bot.send_message(chat_id=chat_id, text=f"✅ All files sent for {subject_name} - {module_folder_name}!")
    operation_duration = (datetime.datetime.now() - operation_start_time).total_seconds()
    write_breadcrumb(f"send_module_files: Completed for chat_id {chat_id} for {subject_name} - {module_folder_name}. Duration: {operation_duration:.2f}s")

# --- Command Handlers -------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message_text = (
        f"Hi {user.mention_html()}! Welcome to the ECE Resource Bot.\n\n"
        "You can use me to get Notes or Previous Year Papers.\n\n"
        "Available commands:\n"
        "/notes - Get lecture notes\n"
        "/papers - Get previous year question papers\n"
        "/help - Show this help message"
    )
    if update.callback_query: # Called from a button like 'Back to Main Menu'
        query = update.callback_query # Define query from update
        await query.answer() # Acknowledge callback first
        await query.edit_message_text(text=message_text, reply_markup=None, parse_mode='HTML')
        write_breadcrumb(f"Callback 'start_menu': User {user.id} ({user.first_name})")
    else: # Called directly via /start command
        await update.message.reply_html(message_text)
        write_breadcrumb(f"Command /start: User {user.id} ({user.first_name})")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    write_breadcrumb(f"Command /help: User {update.effective_user.id}")
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Welcome message\n"
        "/help - This help message\n"
        "/notes - Browse lecture notes\n"
        "/papers - Browse previous year papers"
    )

async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    write_breadcrumb(f"Command /notes: User {update.effective_user.id}")
    # build_subject_keyboard now generates 'notes_showmodules_CODE' callbacks
    keyboard = build_subject_keyboard("notes") 
    await update.message.reply_text("📚 Please select a subject for notes:", reply_markup=keyboard)

async def papers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    write_breadcrumb(f"Command /papers: User {update.effective_user.id}")
    # build_subject_keyboard now generates 'papers_showmodules_CODE' callbacks
    keyboard = build_subject_keyboard("papers") 
    await update.message.reply_text("📝 Please select a subject for papers:", reply_markup=keyboard)

# --- Callback Query Handler -------------------------------------------------
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer() # Acknowledge callback
    data = query.data
    chat_id = query.effective_chat.id
    user_id = query.effective_user.id

    write_breadcrumb(f"CallbackQuery: User {user_id}, Data: {data}")

    parts = data.split('_')
    action_prefix = parts[0] # 'notes', 'papers', or 'start'
    command = parts[1] if len(parts) > 1 else None
    subject_code = parts[2] if len(parts) > 2 else None
    module_number = parts[3] if len(parts) > 3 else None

    if action_prefix == "start" and command == "menu":
        # This is triggered by 'Back to Main Menu' buttons
        # Re-use start_command logic, but ensure it edits the message
        # For simplicity, directly call the text/reply_markup part here or refactor start_command
        message_text = (
            f"Hi {query.effective_user.mention_html()}! Welcome to the ECE Resource Bot.\n\n"
            "You can use me to get Notes or Previous Year Papers.\n\n"
            "Available commands:\n"
            "/notes - Get lecture notes\n"
            "/papers - Get previous year question papers\n"
            "/help - Show this help message"
        )
        await query.edit_message_text(text=message_text, reply_markup=None, parse_mode='HTML')
        write_breadcrumb(f"Callback 'start_menu': Displayed main menu for User {user_id}")
        return

    if action_prefix in ["notes", "papers"]:
        current_data_path_root = NOTES_DATA_PATH if action_prefix == "notes" else PAPERS_DATA_PATH
        text_prompt_subject = "📚 Please select a subject for notes:" if action_prefix == "notes" else "📝 Please select a subject for papers:"
        
        if command == "showsubjects": # e.g. notes_showsubjects (from 'Back to Subjects')
            keyboard = build_subject_keyboard(action_prefix)
            await query.edit_message_text(text=text_prompt_subject, reply_markup=keyboard)
            write_breadcrumb(f"Callback '{data}': Displayed subject keyboard for {action_prefix}")
        
        elif command == "showmodules" and subject_code in SUBJECTS:
            # e.g. notes_showmodules_ACS (from subject button or /notes -> subject)
            keyboard = build_module_keyboard(action_prefix, subject_code)
            subject_name = SUBJECTS[subject_code]
            await query.edit_message_text(text=f"Selected: {subject_name}\n🔢 Please select a module for {action_prefix}:", reply_markup=keyboard)
            write_breadcrumb(f"Callback '{data}': Displayed module keyboard for {action_prefix}, {subject_code}")

        elif command == "getfiles" and subject_code in SUBJECTS and module_number:
            # e.g. notes_getfiles_ACS_1 (from module button)
            subject_name = SUBJECTS[subject_code]
            await query.edit_message_text(text=f"Fetching {action_prefix} for {subject_name} - Module {module_number}...")
            await send_module_files(chat_id, current_data_path_root, subject_code, module_number, context)
            # After sending files, perhaps offer to go back to modules or subjects?
            # For now, send_module_files sends a completion message.
            write_breadcrumb(f"Callback '{data}': Triggered file sending for {action_prefix}, {subject_code}, Module {module_number}")
        
        else:
            await query.edit_message_text(text="Sorry, I didn't understand that selection or it's invalid. Please try again.")
            write_breadcrumb(f"CallbackQuery: Unhandled or invalid data structure for {action_prefix}: {data}")
    else:
        await query.edit_message_text(text="Sorry, an unexpected error occurred with your selection.")
        write_breadcrumb(f"CallbackQuery: Unhandled action_prefix: {data}")


# --- Error Handler ----------------------------------------------------------
async def error_handler_telegram(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs errors caused by Updates."""
    error_message = f"Telegram Update {update} caused error: {context.error}"
    write_breadcrumb(f"ERROR_HANDLER: {error_message}")
    print(error_message, file=sys.stderr, flush=True) # Also print to console for visibility

    if isinstance(context.error, telegram.error.NetworkError):
        # Potentially notify user if it's a user-facing command
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            try:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="A network error occurred. Please try again later.")
            except Exception as e_send:
                write_breadcrumb(f"ERROR_HANDLER: Failed to send network error notification: {e_send}")
    # Add more specific error handling as needed

# --- Main Application Logic -------------------------------------------------
def run_bot() -> None:
    """Sets up and runs the Telegram bot."""
    write_breadcrumb("run_bot: Initializing bot application...")
    
    try:
        port_to_use = int(PORT_FROM_ENV)
    except ValueError:
        write_breadcrumb(f"run_bot: Invalid PORT_FROM_ENV value '{PORT_FROM_ENV}'. Defaulting to 8443.")
        port_to_use = 8443

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("notes", notes_command))
    application.add_handler(CommandHandler("papers", papers_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern=r"^(notes|papers|start)_"))

    application.add_error_handler(error_handler_telegram)

    write_breadcrumb("run_bot: Bot application handlers configured.")

    if RENDER_APP_BASE_URL:
        # Using Webhook
        full_webhook_url = f"{RENDER_APP_BASE_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
        write_breadcrumb(f"run_bot: Starting in WEBHOOK mode. URL: {full_webhook_url}, Port: {port_to_use}, Path: /<TOKEN>")
        application.run_webhook(
            listen="0.0.0.0",
            port=port_to_use,
            url_path=TELEGRAM_TOKEN, # The path part of the webhook URL
            webhook_url=full_webhook_url # The full URL Telegram will call
        )
        write_breadcrumb("run_bot: Webhook is running.")
    else:
        # Using Polling
        write_breadcrumb("run_bot: RENDER_APP_BASE_URL not set. Starting in POLLING mode.")
        application.run_polling()
        write_breadcrumb("run_bot: Polling is running.")

# --- Script Entry Point -----------------------------------------------------
if __name__ == "__main__":
    write_breadcrumb("__main__: Script execution started.")
    
    # --- Instance Locking ---
    # Check if instance lock is explicitly disabled via a marker in this script file.
    # This is a simple way to allow disabling the lock for debugging without editing instance_lock.py
    instance_lock_disabled_marker = "# INSTANCE_LOCK_DISABLE_MARKER" 
    lock_is_disabled_by_marker = False
    try:
        with open(__file__, 'r', encoding='utf-8') as f_script_check:
            if instance_lock_disabled_marker in f_script_check.read():
                lock_is_disabled_by_marker = True
                write_breadcrumb("__main__: Instance lock is DISABLED by marker in script file.")
    except Exception as e_script_check:
        write_breadcrumb(f"__main__: Error checking for instance_lock_disabled_marker: {e_script_check}")

    if lock_is_disabled_by_marker:
        # If disabled by marker, try to clean up any existing lock file as a precaution
        lock_file_path_for_cleanup = os.path.join(BASE_DIR, "bot.lock") # Default lock file name
        if os.path.exists(lock_file_path_for_cleanup):
            write_breadcrumb(f"__main__: Instance lock disabled by marker, but lock file '{lock_file_path_for_cleanup}' exists. Attempting removal.")
            try:
                os.remove(lock_file_path_for_cleanup)
                write_breadcrumb(f"__main__: Successfully removed stale lock file: {lock_file_path_for_cleanup}")
            except OSError as e_remove_stale:
                write_breadcrumb(f"__main__: Failed to remove stale lock file '{lock_file_path_for_cleanup}' (lock disabled by marker): {e_remove_stale}")
        
        write_breadcrumb("__main__: Proceeding without instance lock due to disable marker.")
        run_bot() # Run the bot directly
    else:
        # Proceed with instance lock enabled
        write_breadcrumb("__main__: Instance lock is ENABLED (no disable marker found).")
        lock = InstanceLock() # Uses default lock file name "bot.lock" in BASE_DIR
        if lock.acquire():
            write_breadcrumb("__main__: Instance lock acquired successfully.")
            try:
                run_bot()
            finally:
                # Ensure lock is released if acquired
                lock.release()
                write_breadcrumb("__main__: Instance lock released (in finally block).")
        else:
            # This 'else' corresponds to 'if lock.acquire():'
            # lock.acquire() itself prints messages on failure, so we just add a breadcrumb and exit.
            write_breadcrumb("__main__: CRITICAL - Failed to acquire instance lock. Bot cannot start. Check previous breadcrumbs/console for details from InstanceLock.")
            # Print a consolidated error message to stderr for user visibility if they are not checking breadcrumbs.
            print("CRITICAL: Bot startup failed - Could not acquire instance lock.", file=sys.stderr, flush=True)
            print("This may be due to another instance running or a stale 'bot.lock' file.", file=sys.stderr, flush=True)
            print("Check 'debug_script_flow.txt' and console output for detailed messages from the locking mechanism.", file=sys.stderr, flush=True)
            print("If safe, manually delete 'bot.lock' or use debug options (DISABLE_LOCK_FILE_FOR_DEBUG in .env / # INSTANCE_LOCK_DISABLE_MARKER in script).", file=sys.stderr, flush=True)
            sys.exit(1) # Exit with error code

    write_breadcrumb("__main__: Script execution finished or bot stopped.")
