# 🚀 Deploy ECE Telegram Bot to Vercel

This guide will help you deploy your ECE 6th Semester Telegram Bot to Vercel using webhook mode.

## 📋 Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Telegram Bot Token**: Get from [@BotFather](https://t.me/botfather)
3. **Git Repository**: Push your code to GitHub/GitLab

## 🛠️ Deployment Steps

### Step 1: Prepare Your Environment

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file:**
   ```env
   TELEGRAM_TOKEN=7638559775:AAH7YU60NLyGP5xV7kuFzSsFU84LPRwczQA
   WEBHOOK_URL=https://your-app-name.vercel.app/api/webhook
   VERCEL=1
   ```

### Step 2: Deploy to Vercel

#### Option A: Vercel CLI (Recommended)

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel:**
   ```bash
   vercel login
   ```

3. **Deploy:**
   ```bash
   vercel --prod
   ```

#### Option B: GitHub Integration (Your Repository)

1. **Push to your GitHub repo:**
   ```bash
   git add .
   git commit -m "Add ECE Telegram Bot with Vercel deployment"
   git push origin main
   ```

2. **Connect to Vercel:**
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your repository: `https://github.com/shreyasTalwar/TELEGRAM-BOT.git`
   - Vercel will auto-detect the configuration

### Step 3: Set Environment Variables

In Vercel Dashboard:

1. Go to your project → Settings → Environment Variables
2. Add these variables:

| Name | Value | Environment |
|------|-------|-------------|
| `TELEGRAM_TOKEN` | `7638559775:AAH7YU60NLyGP5xV7kuFzSsFU84LPRwczQA` | Production, Preview, Development |
| `WEBHOOK_URL` | `https://your-app-name.vercel.app/api/webhook` | Production |
| `VERCEL` | `1` | Production, Preview, Development |

### Step 4: Set Telegram Webhook

After deployment, you need to set the webhook URL in Telegram:

1. **Get your deployed URL:**
   - Vercel will provide: `https://your-app-name.vercel.app`

2. **Set webhook using the endpoint:**
   - Visit: `https://your-app-name.vercel.app/set-webhook`
   - Or manually via Telegram: Send this to [@BotFather](https://t.me/botfather):
     ```
     /setwebhook?url=https://your-app-name.vercel.app/api/webhook
     ```

## 🔧 Project Structure

```
├── BOT2.PY              # Main bot logic with webhook support
├── api/
│   └── index.py         # Vercel serverless function entry point
├── data/                # Your ECE study materials
├── vercel.json          # Vercel configuration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── DEPLOYMENT_GUIDE.md  # This guide
```

## 🚀 Features Available After Deployment

✅ **Complete ECE Study Materials**
- ARM & Embedded Systems
- Advanced Communication Systems
- AI & Machine Learning
- Python Applications
- Java Programming

✅ **Interactive Features**
- Enhanced welcome message with quick access buttons
- Subjects overview with detailed module information
- Comprehensive search functionality
- File browsing with pagination
- Batch download capabilities

✅ **Webhook Mode Benefits**
- Faster response times
- No continuous polling
- Serverless deployment
- Automatic scaling

## 🛠️ Local Development

For local development with polling:

```bash
# Set environment variable for local mode
export VERCEL=

# Run locally
python BOT2.PY
```

## 🔍 Monitoring & Logs

- **Vercel Dashboard**: Check function logs in real-time
- **Health Check**: Visit `https://your-app-name.vercel.app/`
- **Bot Status**: Check if webhook is properly set

## 🆘 Troubleshooting

### Common Issues:

1. **Bot not responding:**
   - Check if `TELEGRAM_TOKEN` is correct
   - Verify webhook URL is accessible
   - Check Vercel function logs

2. **Files not found:**
   - Ensure `data/` folder is uploaded to Vercel
   - Check file paths in environment

3. **Timeout errors:**
   - Large files may timeout on serverless
   - Consider file size limits (20MB max)

### Debug Commands:

```bash
# Check webhook status
curl https://your-app-name.vercel.app/

# View logs
vercel logs --follow

# Check bot info
curl https://api.telegram.org/bot<TOKEN>/getMe
```

## 📞 Support

- **Vercel Docs**: [vercel.com/docs](https://vercel.com/docs)
- **Telegram Bot API**: [core.telegram.org/bots/api](https://core.telegram.org/bots/api)
- **BotFather**: [@BotFather](https://t.me/botfather)

---

🎓 **Your ECE students will now have 24/7 access to all study materials via a professionally deployed Telegram bot!**
