import os
import json
import asyncio
import logging
import base64
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from functools import lru_cache, wraps
from collections import defaultdict
import aiofiles

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# For Vercel deployment - webhook mode
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager

# ─── Config & Constants ──────────────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("Please set TELEGRAM_TOKEN in your .env file.")

# Root content layout: data/{notes|papers}/{subject_key}/<files>
_current_dir = Path(__file__).parent
DATA_ROOT = _current_dir / "telegram bot ece" / "data"

# Check if data folder exists (deployment vs local development)
DATA_FOLDER_EXISTS = DATA_ROOT.exists()

ITEMS_PER_PAGE = 10
RATE_SLEEP_PER_MSG = 1.1
MAX_FILE_SIZE = 20 * 1024 * 1024

# Emojis for polish
SUBJECTS = {
    "arm": "🔧 ARM & Embedded",
    "acs": "📡 Advanced Comm",
    "aiml": "🤖 AI & ML",
    "python": "🐍 Python Application",
    "java": "☕ Java Programming",
}

# Simple in-memory + file-backed cache for file_ids
CACHE_FILE = DATA_ROOT / "cache" / "file_ids.json" if DATA_FOLDER_EXISTS else None
FILE_ID_CACHE: Dict[str, str] = {}
CACHE_LOCK = asyncio.Lock()  # Global cache lock for async operations

# Track bulk sends
SENDING_LOCKS: Dict[int, asyncio.Lock] = {}

# Rate limiting per user
USER_RATE_LIMITS = defaultdict(list)  # {user_id: [timestamps]}
MAX_REQUESTS_PER_MINUTE = 30

# Global application instance for webhook mode
application: Optional[Application] = None

# Performance optimizations
FILE_METADATA_CACHE: Dict[str, Dict] = {}  # Cache file sizes, modification times
FOLDER_CACHE: Dict[str, List[Path]] = {}   # Cache folder listings
CACHE_TTL = 300  # 5 minutes cache TTL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("ece-bot")


# ─── Utility: Cache Persistence ──────────────────────────────────────────────
def load_cache() -> None:
    """Load file_id cache from disk."""
    global FILE_ID_CACHE
    if not DATA_FOLDER_EXISTS or not CACHE_FILE or not CACHE_FILE.exists():
        logger.info("Cache file not available (deployment mode)")
        FILE_ID_CACHE = {}
        return

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            FILE_ID_CACHE = data
        else:
            logger.warning("Cache file has invalid format, resetting")
            FILE_ID_CACHE = {}
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        FILE_ID_CACHE = {}


async def save_cache_async() -> None:
    """Save file_id cache to disk asynchronously."""
    if not DATA_FOLDER_EXISTS or not CACHE_FILE:
        return

    async with CACHE_LOCK:
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            cache_data = json.dumps(FILE_ID_CACHE, ensure_ascii=False, indent=2)
            async with aiofiles.open(CACHE_FILE, 'w', encoding='utf-8') as f:
                await f.write(cache_data)
        except Exception as e:
            logger.error(f"Failed to persist file_id cache: {e}")


def save_cache() -> None:
    """Synchronous wrapper for cache saving (for shutdown handlers)."""
    if not DATA_FOLDER_EXISTS or not CACHE_FILE:
        return

    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(FILE_ID_CACHE, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to persist file_id cache: {e}")


def cache_key(path: Path) -> str:
    return str(path.resolve())


def validate_file_path(file_path: Path, base_folder: Path) -> bool:
    """Validate file path to prevent directory traversal attacks."""
    try:
        resolved_path = file_path.resolve()
        resolved_base = base_folder.resolve()
        return resolved_path.is_relative_to(resolved_base) and resolved_path.exists()
    except (ValueError, OSError):
        return False


def generate_file_id(file_path: Path, base_folder: Path) -> str:
    """Generate a stable, unique file identifier using base64 encoding of relative path."""
    try:
        relative_path = file_path.relative_to(base_folder)
        path_str = str(relative_path).replace("\\", "/")
        encoded = base64.b64encode(path_str.encode('utf-8')).decode('ascii')
        return encoded[:50]
    except (ValueError, OSError) as e:
        logger.error(f"Failed to generate file_id for {file_path}: {e}")
        return base64.b64encode(file_path.name.encode('utf-8')).decode('ascii')[:50]


def decode_file_id(file_id: str, base_folder: Path) -> Optional[Path]:
    """Decode a file_id back to its Path object."""
    try:
        path_str = base64.b64decode(file_id.encode('ascii')).decode('utf-8')
        file_path = base_folder / path_str
        return file_path if file_path.exists() else None
    except Exception as e:
        logger.error(f"Failed to decode file_id {file_id}: {e}")
        return None


# ─── UI Builders ────────────────────────────────────────────────────────────
def subject_keyboard(action: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(name, callback_data=f"sub|{action}|{key}")]
        for key, name in SUBJECTS.items()
    ]
    return InlineKeyboardMarkup(buttons)


def files_keyboard(action: str, subject_key: str, files: List[Path], page: int) -> InlineKeyboardMarkup:
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = files[start:end]
    base_folder = folder_for(action, subject_key)

    rows: List[List[InlineKeyboardButton]] = []
    for i, f in enumerate(page_items):
        if f.parent.name != subject_key:
            module_name = f.parent.name
            file_name = f.name
            if len(f"{module_name}/{file_name}") > 48:
                label = f"{module_name}/{file_name[:40]}…"
            else:
                label = f"{module_name}/{file_name}"
        else:
            label = f.name[:48] + ("…" if len(f.name) > 48 else "")

        file_id = generate_file_id(f, base_folder)
        rows.append([InlineKeyboardButton(f"📄 {label}", callback_data=f"fil|{action}|{subject_key}|{file_id}")])

    controls: List[InlineKeyboardButton] = []
    if page > 1:
        controls.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"pg|{action}|{subject_key}|{page-1}"))
    
    if len(files) <= ITEMS_PER_PAGE:
        controls.append(InlineKeyboardButton(f"📦 Send all ({len(files)})", callback_data=f"all|{action}|{subject_key}|{page}|full"))
    else:
        controls.append(InlineKeyboardButton(f"📦 Page ({len(page_items)})", callback_data=f"all|{action}|{subject_key}|{page}|page"))
        if len(files) <= 30:
            controls.append(InlineKeyboardButton(f"📦📦 All ({len(files)})", callback_data=f"all|{action}|{subject_key}|{page}|full"))
    
    if end < len(files):
        controls.append(InlineKeyboardButton("Next ➡️", callback_data=f"pg|{action}|{subject_key}|{page+1}"))
    if controls:
        rows.append(controls)

    rows.append([
        InlineKeyboardButton("🔙 Back", callback_data=f"back|{action}"),
        InlineKeyboardButton("🏠 Home", callback_data="home|")
    ])
    return InlineKeyboardMarkup(rows)


# ─── Data Scanning ──────────────────────────────────────────────────────────
def folder_for(action: str, subject_key: str) -> Path:
    return DATA_ROOT / action / subject_key


# Cache with TTL for folder listings
FOLDER_CACHE_DATA: Dict[str, Tuple[float, List[Path]]] = {}

def get_cached_folder_files(folder_path: str) -> List[Path]:
    """Get cached list of files in folder with TTL-based cache."""
    folder = Path(folder_path)
    if not folder.exists():
        return []

    now = time.time()
    
    # Check if cache is still valid
    if folder_path in FOLDER_CACHE_DATA:
        timestamp, cached_files = FOLDER_CACHE_DATA[folder_path]
        if now - timestamp < CACHE_TTL:
            return cached_files

    # Refresh cache
    files = []
    try:
        for p in folder.rglob("*"):
            if p.is_file() and not p.name.startswith('.'):
                files.append(p)
    except (PermissionError, OSError) as e:
        logger.warning(f"Error accessing {folder}: {e}")
        return []

    files.sort(key=lambda p: p.name.lower())
    FOLDER_CACHE_DATA[folder_path] = (now, files)
    return files


def list_files(folder: Path) -> List[Path]:
    """List all files in folder recursively with caching."""
    if not DATA_FOLDER_EXISTS:
        logger.info(f"Data folder not available: {folder}")
        return []

    folder_str = str(folder.resolve())
    return get_cached_folder_files(folder_str)


# ─── Rate Limiting ─────────────────────────────────────────────────────────
async def check_rate_limit(user_id: int) -> bool:
    """Check if user is within rate limits."""
    now = time.time()
    minute_ago = now - 60
    
    # Clean old timestamps
    USER_RATE_LIMITS[user_id] = [
        ts for ts in USER_RATE_LIMITS[user_id] 
        if ts > minute_ago
    ]
    
    if len(USER_RATE_LIMITS[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    USER_RATE_LIMITS[user_id].append(now)
    return True


# ─── Sending Helpers ────────────────────────────────────────────────────────
async def send_document_with_cache(chat_id: int, path: Path, context: ContextTypes.DEFAULT_TYPE, save_cache_now: bool = True) -> bool:
    """Send a document with caching. Returns True if successful, False otherwise."""
    try:
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ File too large: {path.name} ({size_mb:.1f}MB > 20MB limit)"
            )
            return False
    except OSError as e:
        logger.error(f"Failed to check file size for {path.name}: {e}")
        return False
    
    key = cache_key(path)
    file_id = FILE_ID_CACHE.get(key)
    try:
        if file_id:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
            msg = await context.bot.send_document(chat_id=chat_id, document=file_id, caption=path.name)
            if msg.document and msg.document.file_id != file_id:
                FILE_ID_CACHE[key] = msg.document.file_id
                if save_cache_now:
                    await save_cache_async()
            return True
        
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
        with path.open("rb") as f:
            msg = await context.bot.send_document(chat_id=chat_id, document=f, caption=path.name)
        if msg.document:
            FILE_ID_CACHE[key] = msg.document.file_id
            if save_cache_now:
                await save_cache_async()
        return True
    except Exception as e:
        logger.exception(f"Failed to send {path.name}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Failed: {path.name}")
        return False


async def cleanup_sending_lock(chat_id: int, delay: int = 60):
    """Clean up sending lock after delay."""
    await asyncio.sleep(delay)
    SENDING_LOCKS.pop(chat_id, None)


async def send_all_files_rate_limited(chat_id: int, files: List[Path], context: ContextTypes.DEFAULT_TYPE):
    """Send multiple files with rate limiting and progress updates."""
    lock = SENDING_LOCKS.setdefault(chat_id, asyncio.Lock())
    if lock.locked():
        await context.bot.send_message(chat_id=chat_id, text="⏳ A send is already in progress here.")
        return
    
    try:
        async with lock:
            total = len(files)
            success_count = 0
            
            for i, path in enumerate(files, start=1):
                if i % 5 == 1 and total > 5:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"📤 Sending file {i}/{total}..."
                    )
                
                if await send_document_with_cache(chat_id, path, context, save_cache_now=False):
                    success_count += 1
                
                await asyncio.sleep(RATE_SLEEP_PER_MSG)
            
            await save_cache_async()
            
            if success_count == total:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ Successfully sent all {total} files!"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ Sent {success_count}/{total} files (some failed)"
                )
    finally:
        # Schedule lock cleanup
        asyncio.create_task(cleanup_sending_lock(chat_id))


# ─── Command Handlers ───────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_rate_limit(update.effective_user.id):
        await update.message.reply_text("⚠️ Too many requests. Please wait a moment.")
        return
    
    welcome_message = """
🎓 *Welcome to ECE 6th Semester Bot!* 🎓

📚 *Your Complete ECE Study Companion*

Choose your study materials:
    """
    keyboard = [
        [InlineKeyboardButton("📘 Browse Notes", callback_data="sub|notes|_")],
        [InlineKeyboardButton("📄 Previous Year Papers", callback_data="sub|papers|_")],
        [InlineKeyboardButton("🔍 Search Files", callback_data="search_quick")],
        [InlineKeyboardButton("📖 Subjects Overview", callback_data="subjects_overview")],
        [InlineKeyboardButton("❓ Help & Commands", callback_data="help_quick")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_markdown(
        welcome_message,
        reply_markup=reply_markup
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/notes – Browse notes\n"
        "/papers – Browse previous year papers\n"
        "/search <text> – Search across all subjects\n"
        "Tips: Use Back and Home to navigate, and Send all to batch download."
    )


async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_rate_limit(update.effective_user.id):
        await update.message.reply_text("⚠️ Too many requests. Please wait a moment.")
        return
    
    await update.message.reply_text(
        "📘 Select a subject for notes:",
        reply_markup=subject_keyboard("notes")
    )


async def papers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_rate_limit(update.effective_user.id):
        await update.message.reply_text("⚠️ Too many requests. Please wait a moment.")
        return
    
    await update.message.reply_text(
        "📄 Select a subject for previous year question papers:",
        reply_markup=subject_keyboard("papers")
    )


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_rate_limit(update.effective_user.id):
        await update.message.reply_text("⚠️ Too many requests. Please wait a moment.")
        return
    
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("🔎 Usage: /search <text>")
        return
    query_lower = query.lower()
    results: List[Tuple[str, Path]] = []
    found_enough = False

    for act in ("notes", "papers"):
        if found_enough:
            break
        for sk in SUBJECTS.keys():
            if found_enough:
                break
            folder = folder_for(act, sk)
            for f in list_files(folder):
                if query_lower in f.name.lower():
                    results.append((f"{act}/{sk}", f))
                    if len(results) >= 30:
                        found_enough = True
                        break
    if not results:
        await update.message.reply_text(f'📭 No matches for "{query}".')
        return

    context.user_data['search_results'] = results

    buttons: List[List[InlineKeyboardButton]] = []
    for i, (where, path) in enumerate(results[:ITEMS_PER_PAGE]):
        label = path.name[:48] + ("…" if len(path.name) > 48 else "")
        buttons.append([InlineKeyboardButton(f"📄 {label}", callback_data=f"search_file|{i}")])
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="home|")])
    await update.message.reply_text(
        f'🔎 Results for "{query}" (showing {min(len(results), ITEMS_PER_PAGE)} of {len(results)}):',
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ─── Callback Handler ───────────────────────────────────────────────────────
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if not query:
        logger.warning("Callback query is None")
        return
    
    await query.answer()

    data = query.data or ""
    parts = data.split("|")

    # Home
    if parts[0] == "home":
        await query.edit_message_text("Choose:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📘 Notes", callback_data="sub|notes|_"),
             InlineKeyboardButton("📄 Papers", callback_data="sub|papers|_")],
        ]))
        return

    # Handle search result file selection
    if parts[0] == "search_file":
        try:
            if not query.message:
                logger.warning("Callback query has no message")
                return
            
            if len(parts) < 2:
                await query.edit_message_text("⚠️ Invalid search result selection.")
                return
            
            idx = int(parts[1])
            search_results = context.user_data.get('search_results', [])
            
            if idx >= len(search_results):
                await query.edit_message_text("⚠️ Search result not found.")
                return
            
            where, target_file = search_results[idx]
            act, sk = where.split("/")
            base_folder = folder_for(act, sk)
            
            if not target_file.exists():
                await query.edit_message_text("⚠️ File not found.")
                return
            
            if not validate_file_path(target_file, base_folder):
                await query.edit_message_text("⚠️ Invalid file path.")
                return
            
            await query.edit_message_text(f"📤 Sending: {target_file.name}")
            await send_document_with_cache(query.message.chat.id, target_file, context)
            
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text="Choose another option:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Home", callback_data="home|")]
                ])
            )
        except Exception as e:
            logger.exception(f"Error in search_file callback: {e}")
            await query.edit_message_text("⚠️ An error occurred.")
        return

    # Quick search from start menu
    if parts[0] == "search_quick":
        search_help = """
🔍 *Search Files Guide*

📝 *How to Search:*
• Type: `/search <your text>`
• Example: `/search python module 3`
• Example: `/search arm microcontroller`

🎯 *Search Tips:*
• Searches across ALL subjects and modules
• Finds files containing your search term
• Case-insensitive (Python = python)
• Searches in filenames and folder names
• Returns up to 30 matching files

📋 *Search Examples:*
• `/search module 1` - Find all Module 1 files
• `/search assignment` - Find assignments
• `/search notes` - Find note files
• `/search pdf` - Find PDF documents
• `/search java` - Find Java-related files

💡 *Pro Tips:*
• Use specific keywords for better results
• Combine terms: `/search python gui`
• Check file labels for module info
        """
        await query.edit_message_text(search_help, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Try Search", callback_data="search_prompt")],
            [InlineKeyboardButton("📘 Browse Notes", callback_data="sub|notes|_")],
            [InlineKeyboardButton("🏠 Home", callback_data="home|")]
        ]), parse_mode='Markdown')
        return

    # Search prompt for easy access
    if parts[0] == "search_prompt":
        await query.edit_message_text("🔍 *Ready to search!*\n\nPlease send me your search term:\nExample: `/search python module 3`", parse_mode='Markdown')
        return

    # Subjects overview
    if parts[0] == "subjects_overview":
        subjects_info = """
📖 *ECE 6th Semester Subjects*

🔧 *ARM & Embedded Systems*
• ARM 32-bit Microcontroller
• Embedded System Components
• ARM Cortex-M3 Instruction Set
• Embedded Firmware Design

📡 *Advanced Communication Systems*
• Digital Communication Techniques
• Coding and Error Control
• Spread Spectrum Communications
• Fading Channels

🤖 *AI & Machine Learning*
• Machine Learning Fundamentals
• Neural Networks
• Deep Learning
• AI Applications

🐍 *Python Applications*
• Python Programming
• GUI Development
• NumPy & Pandas
• Data Science Tools

☕ *Java Programming*
• Core Java Concepts
• Object-Oriented Programming
• Java Applications
• Advanced Java Features
        """
        await query.edit_message_text(subjects_info, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📘 Browse Notes", callback_data="sub|notes|_")],
            [InlineKeyboardButton("📄 Papers", callback_data="sub|papers|_")],
            [InlineKeyboardButton("🏠 Home", callback_data="home|")]
        ]), parse_mode='Markdown')
        return

    # Quick help from start menu
    if parts[0] == "help_quick":
        help_info = """
❓ *ECE Bot Help & Commands*

📋 *Available Commands:*
• /start - Welcome message & quick access
• /notes - Browse study notes by subject
• /papers - Previous year question papers
• /search <text> - Search across all files
• /help - Detailed command reference

🎯 *Quick Tips:*
• Use the inline buttons for easy navigation
• Click "Send all" for batch downloads
• Use pagination buttons (Prev/Next) for large lists
• Search feature finds files across all subjects

📚 *File Organization:*
• Files are organized by Subject → Module → Files
• Module folders are clearly labeled in file names
• All file types supported (PDF, DOC, PPT, etc.)
        """
        await query.edit_message_text(help_info, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📘 Browse Notes", callback_data="sub|notes|_")],
            [InlineKeyboardButton("📄 Papers", callback_data="sub|papers|_")],
            [InlineKeyboardButton("🏠 Home", callback_data="home|")]
        ]), parse_mode='Markdown')
        return

    # Subject chosen
    if parts[0] == "sub":
        _, action, subject_key = parts
        if subject_key == "_":
            if query.message:
                await query.edit_message_text(
                    "📘 Select a subject for notes:" if action == "notes" else "📄 Select a subject for previous year question papers:",
                    reply_markup=subject_keyboard(action)
                )
            return
        subject_name = SUBJECTS.get(subject_key, "Unknown")
        folder = folder_for(action, subject_key)
        files = list_files(folder)
        if not files:
            await query.edit_message_text(f"⚠️ No files found for {subject_name}.")
            return
        if query.message:
            await query.edit_message_text(
                f"📁 {subject_name}\nSelect a file or send all:",
                reply_markup=files_keyboard(action, subject_key, files, page=1)
            )
        return

    # Pagination
    if parts[0] == "pg":
        _, action, subject_key, page_str = parts
        folder = folder_for(action, subject_key)
        files = list_files(folder)
        page = max(1, int(page_str))
        if not files:
            await query.edit_message_text("⚠️ No files in this folder.")
            return
        await query.edit_message_text(
            "📁 Choose a file or send all:",
            reply_markup=files_keyboard(action, subject_key, files, page)
        )
        return

    # Send single file
    if parts[0] == "fil":
        try:
            if len(parts) < 4:
                await query.edit_message_text("⚠️ Invalid file selection.")
                return
            
            if not query.message:
                logger.warning("Callback query has no message")
                return
            
            _, action, subject_key, file_id = parts
            base_folder = folder_for(action, subject_key)

            target_file = decode_file_id(file_id, base_folder)

            if not target_file or not target_file.exists():
                await query.edit_message_text("⚠️ File not found.")
                logger.warning(f"File not found for ID: {file_id}")
                return

            if not validate_file_path(target_file, base_folder):
                await query.edit_message_text("⚠️ Invalid file path.")
                logger.warning(f"Path validation failed for: {target_file}")
                return

            await query.edit_message_text(f"📤 Sending: {target_file.name}")
            await send_document_with_cache(query.message.chat.id, target_file, context)

            files = list_files(base_folder)
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text="Choose another file or go back:",
                reply_markup=files_keyboard(action, subject_key, files, page=1)
            )
        except Exception as e:
            logger.exception(f"Error in file send callback: {e}")
            await query.edit_message_text("⚠️ An error occurred.")
        return

    # Send all files (page or full scope)
    if parts[0] == "all":
        try:
            if not query.message:
                logger.warning("Callback query has no message")
                return
            
            if len(parts) < 5:
                _, action, subject_key, page_str = parts
                mode = "page"
            else:
                _, action, subject_key, page_str, mode = parts
            
            folder = folder_for(action, subject_key)
            files = list_files(folder)
            page = max(1, int(page_str))
            
            if mode == "full":
                batch = files
            else:
                start = (page - 1) * ITEMS_PER_PAGE
                end = start + ITEMS_PER_PAGE
                batch = files[start:end]
            
            if not batch:
                await query.edit_message_text("⚠️ No files to send.")
                return
            
            await query.edit_message_text(f"📦 Sending {len(batch)} file(s)...")
            await send_all_files_rate_limited(query.message.chat.id, batch, context)
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text="Done. Choose more or go back:",
                reply_markup=files_keyboard(action, subject_key, files, page=page)
            )
        except ValueError as e:
            logger.error(f"Invalid page number in callback: {e}")
            await query.edit_message_text("⚠️ Invalid page number.")
        except Exception as e:
            logger.exception(f"Error in send all callback: {e}")
            await query.edit_message_text("⚠️ An error occurred.")
        return

    # Back to subject list
    if parts[0] == "back":
        _, action = parts
        await query.edit_message_text(
            "📘 Select a subject for notes:" if action == "notes" else "📄 Select a subject for previous year question papers:",
            reply_markup=subject_keyboard(action)
        )
        return


# ─── Shutdown Handler ───────────────────────────────────────────────────────
async def shutdown(app: Application) -> None:
    """Save cache on shutdown."""
    logger.info("Shutting down, saving cache...")
    save_cache()


# ─── Initialize Bot Application ─────────────────────────────────────────────
def init_application(use_polling: bool = False) -> Application:
    """Initialize and configure the bot application."""
    from telegram.request import HTTPXRequest
    
    # Configure request with longer timeouts for large file uploads
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=10.0,
        read_timeout=60.0,  # 60 seconds for large file uploads
        write_timeout=60.0,
    )
    
    builder = ApplicationBuilder().token(TOKEN).request(request)
    
    # For polling mode, we need to explicitly configure the updater
    # The default builder for polling includes an updater automatically
    app = builder.build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("notes", notes))
    app.add_handler(CommandHandler("papers", papers))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CallbackQueryHandler(on_callback))
    
    return app


# ─── FastAPI App for Vercel ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global application

    # Startup
    logger.info("🚀 Initializing bot for webhook mode")
    load_cache()

    # Initialize application
    application = init_application()
    await application.initialize()
    await application.start()

    # Set webhook
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        await application.bot.set_webhook(url=webhook_url)
        # Redact query parameters from log
        safe_url = webhook_url.split('?')[0]
        logger.info(f"✅ Webhook set to {safe_url}")
    else:
        logger.warning("⚠️ WEBHOOK_URL not set")

    yield  # App runs here

    # Shutdown
    if application:
        logger.info("Shutting down webhook mode, saving cache...")
        save_cache()
        await application.stop()
        await application.shutdown()

# Create FastAPI app with lifespan
web_app = FastAPI(lifespan=lifespan)


@web_app.post("/webhook")
async def webhook(request: Request):
    """Handle webhook requests from Telegram."""
    global application

    if not application:
        logger.error("Application not initialized")
        return Response("Bot not initialized", status_code=503)

    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response("OK", status_code=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response("Error", status_code=500)


@web_app.get("/")
async def health_check():
    """Health check endpoint for Vercel."""
    return {"status": "Bot is running", "mode": "webhook"}


@web_app.get("/set-webhook")
async def set_webhook_endpoint():
    """Endpoint to set webhook URL."""
    global application

    if not application:
        return {"error": "Application not initialized"}

    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        return {"error": "WEBHOOK_URL not set"}

    try:
        await application.bot.set_webhook(url=webhook_url)
        return {"status": "Webhook set successfully", "url": webhook_url}
    except Exception as e:
        return {"error": str(e)}


# ─── Main (Local Polling Mode) ──────────────────────────────────────────────
def main() -> None:
    """Main function for local polling mode."""
    global application
    
    load_cache()
    
    # Create and configure application for polling mode
    application = init_application(use_polling=True)
    
    logger.info("🔄 Running in polling mode for local development")
    logger.info("Press Ctrl+C to stop the bot")
    
    # Run the bot with polling
    # The ApplicationBuilder automatically includes an Updater when using run_polling()
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    
    # Save cache on exit
    logger.info("Bot stopped, saving cache...")
    save_cache()


if __name__ == "__main__":
    if not os.getenv("VERCEL"):
        main()
    else:
        logger.info("Running in Vercel mode, use ASGI handler")
