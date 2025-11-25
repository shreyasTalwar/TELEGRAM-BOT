# Quick Start Guide - ECE Telegram Bot

## ✅ Changes Applied Successfully!

All critical fixes from the code review have been implemented. Your bot is now more secure, performant, and reliable!

---

## 🚀 How to Run

### Local Development (Polling Mode)
```bash
# Make sure your .env file has TELEGRAM_TOKEN set
python BOT2.PY
```

You should see:
```
INFO | 🔄 Running in polling mode for local development
INFO | Press Ctrl+C to stop the bot
```

### Vercel Deployment (Webhook Mode)
The bot will automatically use webhook mode when `VERCEL` environment variable is detected.

---

## 🎯 Key Improvements

### 1. **Rate Limiting** (NEW!)
- Prevents spam: 30 requests per minute per user
- Automatic throttling with friendly error messages
- Protects your bot from abuse

### 2. **Better Performance**
- Async cache operations (no more blocking!)
- Smart caching with 5-minute auto-refresh
- Memory leak fixes in lock management

### 3. **Enhanced Security**
- Per-user rate limiting
- Secure logging (no sensitive data exposure)
- Proper error handling

### 4. **Bug Fixes**
- Fixed polling mode (works locally now!)
- Removed instance_lock dependency issues
- Fixed callback query null checks
- Fixed cache race conditions

---

## 📊 What Changed in the Code?

### Added Features
- ✅ `check_rate_limit()` - Per-user rate limiting
- ✅ `save_cache_async()` - Non-blocking cache saves
- ✅ `cleanup_sending_lock()` - Automatic lock cleanup
- ✅ TTL-based folder caching with auto-expiration
- ✅ Null checks for callback queries

### Removed/Fixed
- ❌ Removed unused `ThreadPoolExecutor` import
- ✅ Fixed `@lru_cache` that never expired
- ✅ Fixed blocking I/O in async functions
- ✅ Fixed memory leak in SENDING_LOCKS dictionary
- ✅ Simplified polling mode initialization

---

## 🧪 Testing Your Bot

### Test Rate Limiting
1. Send `/start` command 35 times quickly
2. After 30 requests, you should see:
   > ⚠️ Too many requests. Please wait a moment.

### Test Caching
1. Browse to any subject (e.g., `/notes` → ARM)
2. First load: Scans filesystem
3. Second load: Uses cache (faster!)
4. Wait 5+ minutes and browse again: Cache refreshes

### Test File Sending
1. Use `/notes` to browse materials
2. Select a subject and file
3. File should send with progress indicators
4. Try "Send all" for batch operations

---

## ⚙️ Configuration

### Required
```env
TELEGRAM_TOKEN=your_bot_token_here
```

### Optional
```env
WEBHOOK_URL=https://your-app.vercel.app/webhook  # For Vercel deployment
VERCEL=1  # Auto-detected on Vercel
```

### Adjustable Parameters (in code)
```python
MAX_REQUESTS_PER_MINUTE = 30  # Rate limit (line ~64)
CACHE_TTL = 300               # Cache expiry in seconds (5 min)
ITEMS_PER_PAGE = 10          # Files shown per page
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB limit
```

---

## 📁 File Structure

```
TELEGRAM-BOT/
├── BOT2.PY                    # ✨ Updated bot code (all fixes applied)
├── .env                       # Your bot token (keep secret!)
├── .env.example              # Example environment file
├── data/                     # Your study materials
│   ├── notes/               # Study notes by subject
│   └── papers/              # Previous year papers
├── cache/                    # Auto-generated file ID cache
│   └── file_ids.json        # Cached Telegram file IDs
├── IMPROVEMENTS_SUMMARY.md   # 📋 Detailed change log
└── QUICK_START.md           # 📖 This file
```

---

## ❓ Troubleshooting

### Bot doesn't start
```bash
# Check if dependencies are installed
pip install -r requirements.txt

# Verify token is set
echo $TELEGRAM_TOKEN  # Linux/Mac
echo %TELEGRAM_TOKEN%  # Windows
```

### "Too many requests" error immediately
- Adjust `MAX_REQUESTS_PER_MINUTE` in BOT2.PY (line ~64)
- Or wait 60 seconds for rate limit to reset

### Files not showing up
- Wait 5 minutes for cache to refresh
- Or restart the bot to clear cache
- Check that files exist in `data/notes/` or `data/papers/`

### Import errors
```bash
# Install missing dependencies
pip install python-telegram-bot fastapi aiofiles python-dotenv
```

---

## 🎓 How to Use (For Students)

### Browse Notes
1. Send `/start` or `/notes`
2. Select a subject (ARM, ACS, AIML, Python, Java)
3. Browse files organized by modules
4. Click a file to download
5. Use "Send all" to download multiple files

### Search Files
1. Send `/search <keyword>`
2. Example: `/search python module 3`
3. Results show matching files across all subjects

### Previous Year Papers
1. Send `/papers`
2. Select your subject
3. Download question papers

---

## 📈 Performance Tips

### For Better Performance
1. Let cache warm up (first access scans filesystem)
2. Use "Send all" for bulk downloads (optimized)
3. Search is fast (cached file lists)

### For Server Admins
1. Monitor cache hit rates in logs
2. Adjust `CACHE_TTL` based on how often files change
3. Set appropriate `MAX_REQUESTS_PER_MINUTE` for your users

---

## 🔒 Security Notes

### What's Protected
- ✅ Rate limiting prevents spam
- ✅ Path validation prevents directory traversal
- ✅ File size limits prevent memory exhaustion
- ✅ Secure logging (no secrets in logs)

### What to Keep Secret
- 🔐 `TELEGRAM_TOKEN` - Never commit to git!
- 🔐 `WEBHOOK_URL` if it contains secrets
- 🔐 `.env` file - Add to `.gitignore`

---

## 🚀 Deployment Checklist

### Before Deploying
- [ ] Set `TELEGRAM_TOKEN` in environment
- [ ] Test locally with `/start`
- [ ] Verify file sending works
- [ ] Check rate limiting works
- [ ] Test search functionality

### For Vercel Deployment
- [ ] Set `WEBHOOK_URL` environment variable
- [ ] Set `TELEGRAM_TOKEN` in Vercel env vars
- [ ] Deploy and test webhook endpoint
- [ ] Verify bot responds in Telegram

---

## 📞 Support

### Getting Help
1. Check `IMPROVEMENTS_SUMMARY.md` for detailed technical info
2. Review error messages in console/logs
3. Verify all dependencies are installed
4. Ensure TOKEN is correct and bot is active

### Common Questions

**Q: Can I change the rate limit?**  
A: Yes! Edit `MAX_REQUESTS_PER_MINUTE` in BOT2.PY (line ~64)

**Q: How do I add more subjects?**  
A: Update the `SUBJECTS` dictionary (line ~50) and add corresponding folders in `data/`

**Q: Cache not refreshing?**  
A: Cache refreshes every 5 minutes. Adjust `CACHE_TTL` if needed.

---

## ✨ What's New

### Compared to Original Code
| Feature | Before | After |
|---------|--------|-------|
| Rate Limiting | ❌ None | ✅ 30 req/min |
| Cache System | ❌ Never expires | ✅ 5-min TTL |
| Async I/O | ❌ Blocking | ✅ Fully async |
| Memory Leaks | ⚠️ Lock leaks | ✅ Auto cleanup |
| Error Handling | ⚠️ Basic | ✅ Robust |
| Local Mode | ❌ Broken | ✅ Works perfectly |

---

## 🎉 You're All Set!

Your bot is now:
- ✅ **Faster** - Better caching and async operations
- ✅ **Safer** - Rate limiting and security fixes
- ✅ **Stabler** - No memory leaks or blocking operations
- ✅ **Smarter** - Auto-refreshing cache and error recovery

**Happy coding! 🚀**

---

*For detailed technical information, see `IMPROVEMENTS_SUMMARY.md`*