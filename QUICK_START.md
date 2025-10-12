# Quick Start Guide - ECE Study Materials Bot

## 🚀 Getting Started

### Prerequisites
- Python 3.9+ (required for `Path.is_relative_to()`)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Installation

1. **Install Dependencies:**
```bash
pip install python-telegram-bot python-dotenv fastapi
```

2. **Set Up Environment:**
Create a `.env` file in the project root:
```env
TELEGRAM_TOKEN=your_bot_token_here
```

3. **Organize Your Files:**
```
data/
├── notes/
│   ├── arm/
│   ├── acs/
│   ├── aiml/
│   ├── python/
│   └── java/
└── papers/
    ├── arm/
    ├── acs/
    ├── aiml/
    ├── python/
    └── java/
```

---

## 🖥️ Local Development (Polling Mode)

### Run the Bot:
```bash
python BOT2.PY
```

### Expected Output:
```
2024-01-15 10:30:00 | INFO | 🔄 Running in polling mode for local development
2024-01-15 10:30:01 | INFO | Bot started successfully
```

### Test Commands:
1. Open Telegram and find your bot
2. Send `/start` - Should show welcome menu
3. Click "📘 Browse Notes" - Should show subjects
4. Select a subject - Should show files
5. Click a file - Should receive the file
6. Try `/search test` - Should show search results

---

## ☁️ Vercel Deployment (Webhook Mode)

### 1. Prepare for Deployment

Create `vercel.json`:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "BOT2.PY",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "BOT2.PY"
    }
  ],
  "env": {
    "TELEGRAM_TOKEN": "@telegram_token",
    "VERCEL": "1"
  }
}
```

### 2. Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

### 3. Set Environment Variables

In Vercel Dashboard:
1. Go to your project settings
2. Add environment variables:
   - `TELEGRAM_TOKEN` = your bot token
   - `VERCEL` = 1
   - `WEBHOOK_URL` = https://your-app.vercel.app/webhook

### 4. Register Webhook

Visit: `https://your-app.vercel.app/set-webhook`

Should return:
```json
{
  "status": "Webhook set successfully",
  "url": "https://your-app.vercel.app/webhook"
}
```

### 5. Test

Send `/start` to your bot - it should respond via webhook!

---

## 📁 File Organization Tips

### Recommended Structure:
```
data/
├── notes/
│   ├── python/
│   │   ├── Module 1/
│   │   │   ├── Introduction.pdf
│   │   │   └── Basics.pdf
│   │   ├── Module 2/
│   │   │   └── Advanced.pdf
│   │   └── Assignments/
│   │       └── Assignment1.pdf
│   └── java/
│       └── ...
└── papers/
    ├── python/
    │   ├── 2023_QP.pdf
    │   └── 2022_QP.pdf
    └── ...
```

### File Naming Best Practices:
- ✅ Use descriptive names: `Module1_Introduction.pdf`
- ✅ Include module/topic: `ARM_Microcontroller_Basics.pdf`
- ✅ Use underscores or spaces: `Python GUI Programming.pdf`
- ❌ Avoid special characters: `file@#$.pdf`
- ❌ Don't use very long names (>100 chars)

---

## 🔧 Configuration

### Adjust Settings in BOT2.PY:

```python
# Number of files per page
ITEMS_PER_PAGE = 10  # Change to 5, 15, 20, etc.

# Rate limiting (messages per second)
RATE_SLEEP_PER_MSG = 1.1  # Increase for slower sending

# File size limit (20MB default)
MAX_FILE_SIZE = 20 * 1024 * 1024  # Change if needed

# Subjects
SUBJECTS = {
    "arm": "🔧 ARM & Embedded",
    "acs": "📡 Advanced Comm",
    "aiml": "🤖 AI & ML",
    "python": "🐍 Python Application",
    "java": "☕ Java Programming",
}
# Add more subjects as needed
```

---

## 🐛 Troubleshooting

### Bot doesn't start
**Error:** `RuntimeError: Please set TELEGRAM_TOKEN in your .env file.`
**Solution:** Create `.env` file with your token

### Files not showing
**Check:**
1. Files exist in correct folders
2. Folder names match subject keys in `SUBJECTS`
3. Files are not hidden (don't start with `.`)

### "File not found" error
**Causes:**
1. File was deleted after bot started
2. File path has special characters
3. Permission issues

**Solution:** Restart bot to refresh file list

### Webhook not working
**Check:**
1. `VERCEL=1` is set in environment
2. `WEBHOOK_URL` is correct
3. Visit `/set-webhook` endpoint
4. Check Vercel logs for errors

### "Another instance is already running"
**Cause:** Instance lock is active
**Solution:** 
```bash
# Remove lock file
rm data/cache/bot.lock
```

---

## 📊 Monitoring

### Check Bot Status:

**Local Mode:**
- Watch console output for errors
- Check `data/cache/file_ids.json` for cache

**Webhook Mode:**
- Visit `https://your-app.vercel.app/` for health check
- Check Vercel logs for errors
- Monitor Telegram bot API errors

### Common Log Messages:

```
✅ Good:
INFO | Bot started successfully
INFO | Webhook set to https://...
INFO | Sending file 5/10...

⚠️ Warning:
WARNING | Cache file has invalid format, resetting
WARNING | Permission denied accessing folder
WARNING | instance_lock module not found

❌ Error:
ERROR | Failed to send file.pdf: ...
ERROR | Webhook error: ...
ERROR | Another instance is already running!
```

---

## 🔐 Security Notes

### Best Practices:
1. ✅ Never commit `.env` file to git
2. ✅ Use environment variables for tokens
3. ✅ Keep bot token secret
4. ✅ Regularly update dependencies
5. ✅ Monitor bot usage for abuse

### File Security:
- Path validation prevents directory traversal
- File size limits prevent abuse
- Only files in `data/` folder are accessible

---

## 📈 Performance Tips

### For Large File Collections:
1. **Organize by modules** - Easier navigation
2. **Limit files per subject** - Keep under 100 files
3. **Use descriptive names** - Better search results
4. **Compress large PDFs** - Faster uploads

### For High Traffic:
1. **Use webhook mode** - More scalable than polling
2. **Enable caching** - Reduces upload time
3. **Monitor rate limits** - Avoid Telegram API bans
4. **Consider CDN** - For very large files

---

## 🆘 Getting Help

### Check Documentation:
- `CHANGES_SUMMARY.md` - All fixes applied
- `FILE_ID_SYSTEM.md` - How file IDs work
- `instance_lock.py` - Instance locking system

### Common Issues:
1. **Bot not responding** - Check token and internet
2. **Files not sending** - Check file size and permissions
3. **Search not working** - Check file names and folders
4. **Webhook errors** - Check Vercel logs and environment variables

### Debug Mode:
Enable detailed logging:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format="%(asctime)s | %(levelname)s | %(message)s"
)
```

---

## ✅ Checklist Before Going Live

- [ ] Bot token is set correctly
- [ ] All files are organized in `data/` folder
- [ ] Tested all commands locally
- [ ] Tested file selection and download
- [ ] Tested search functionality
- [ ] Tested pagination
- [ ] Tested "send all" feature
- [ ] Cache is working (files send faster on second try)
- [ ] Instance lock prevents multiple instances
- [ ] Webhook is set (for Vercel deployment)
- [ ] Environment variables are configured
- [ ] Logs are being monitored

---

## 🎉 You're Ready!

Your ECE Study Materials Bot is now ready to serve students!

**Features:**
- ✅ Browse notes by subject
- ✅ Browse previous year papers
- ✅ Search across all files
- ✅ Pagination for large lists
- ✅ Bulk file sending
- ✅ Progress updates
- ✅ File caching for speed
- ✅ Dual-mode deployment (local/cloud)

**Next Steps:**
1. Add more subjects as needed
2. Organize files by modules
3. Share bot with students
4. Monitor usage and feedback
5. Update files regularly

Happy bot running! 🚀