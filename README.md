# 📚 Telegram Bot - ECE Study Resources

A feature-rich Telegram bot designed for ECE (Electronics and Communication Engineering) students, providing easy access to study materials, notes, and previous year question papers with robust performance and security features.

---

## ✨ Features

### 📖 Subjects Supported
- **ARM & Embedded Systems**
- **Advanced Communication Systems**
- **AI & Machine Learning**
- **Python Applications**
- **Java Programming**

### 🤖 User Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message & quick access menu |
| `/notes` | Browse study notes by subject and module |
| `/papers` | Download previous year question papers |
| `/search <text>` | Search materials across all subjects |

### 🎯 Interactive Features
- ✅ Inline buttons for easy navigation
- 📄 Pagination support for large file lists
- 📦 Batch download capabilities
- 🔍 Real-time search across all resources

### 🛡️ Performance & Security
- 📂 **Smart Caching**: Auto-refresh with 5-minute TTL
- ⏱️ **Rate Limiting**: 30 requests per minute per user
- 🚫 **Path Validation**: Protection against directory traversal attacks
- 💾 **File Size Limit**: 20MB maximum file size
- 🔒 **Secure Logging**: No sensitive data in logs
- ⚡ **Async I/O**: Fully asynchronous for optimal performance

### 🚀 Deployment Options
- 🌐 Serverless webhook support (Vercel, Heroku, etc.)
- 💻 Local polling mode for development
- 🔧 Environment-based configuration

---

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/shreyasTalwar/TELEGRAM-BOT.git
   cd TELEGRAM-BOT
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your configuration:
   ```env
   TELEGRAM_TOKEN=your_bot_token_here
   WEBHOOK_URL=https://your-domain.com/webhook  # For production
   ```

4. **Prepare data directory**
   ```bash
   mkdir -p data
   # Add your study materials to the data/ folder
   ```

---

## 📦 Usage

### Local Development (Polling Mode)

```bash
python BOT2.PY
```

The bot will start in polling mode and listen for messages.

### Production Deployment (Webhook Mode)

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions on:
- Deploying to Vercel
- Setting up webhooks
- Environment configuration
- Troubleshooting common issues

---

## 📁 Project Structure

```
TELEGRAM-BOT/
├── BOT2.PY                    # Main bot application
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── QUICK_START.md            # Quick start guide
├── DEPLOYMENT_GUIDE.md       # Deployment instructions
├── IMPROVEMENTS_SUMMARY.md   # Feature improvements log
├── data/                     # Study materials directory
│   ├── ARM_Embedded/
│   ├── Communication_Systems/
│   ├── AI_ML/
│   ├── Python/
│   └── Java/
└── logs/                     # Application logs (auto-created)
```

---

## 💡 Tips & Best Practices

### For Users
- 🔍 Use `/search <keyword>` for fast file lookup across all subjects
- 📱 Use inline buttons for easy navigation
- 💬 Provide feedback to improve the bot

### For Administrators
- 📊 Monitor `logs/` directory for bot activity
- 🔄 Cache refreshes automatically every 5 minutes
- 🛡️ Rate limiting prevents abuse (30 req/min per user)
- 📏 Keep files under 20MB for best performance

### Adding New Subjects
1. Update the `SUBJECTS` dictionary in `BOT2.PY`
2. Create corresponding folder in `data/` directory
3. Add study materials to the new folder
4. Restart the bot

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_TOKEN` | Bot token from BotFather | Yes | - |
| `WEBHOOK_URL` | Webhook URL for production | No | - |
| `MAX_FILE_SIZE` | Maximum file size in MB | No | 20 |
| `CACHE_TTL` | Cache refresh time in seconds | No | 300 |
| `RATE_LIMIT` | Requests per minute per user | No | 30 |

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
4. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### Contribution Guidelines
- Follow PEP 8 style guide for Python code
- Add comments for complex logic
- Update documentation for new features
- Test thoroughly before submitting PR

---

## 🐛 Troubleshooting

### Common Issues

**Bot not responding?**
- ✅ Check if `TELEGRAM_TOKEN` is correct
- ✅ Verify internet connection
- ✅ Check logs in `logs/` directory

**Files not loading?**
- ✅ Ensure files are in correct `data/` subdirectories
- ✅ Check file size (must be < 20MB)
- ✅ Verify file permissions

**Webhook not working?**
- ✅ Ensure `WEBHOOK_URL` is set correctly
- ✅ URL must be HTTPS
- ✅ Check deployment platform logs

For more help, check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## 📚 Documentation

- 📖 [Quick Start Guide](QUICK_START.md) - Get started quickly
- 🚀 [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment
- 📝 [Improvements Summary](IMPROVEMENTS_SUMMARY.md) - Feature changelog

---

## 📄 License

This project is currently unlicensed. Please contact the repository owner for usage permissions.

---

## 👥 Authors

- **Shreyas Talwar** - *Initial work* - [@shreyasTalwar](https://github.com/shreyasTalwar)

---

## 🙏 Acknowledgments

- Thanks to all ECE students who use and improve this bot
- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) library
- Inspired by the need for accessible study resources

---

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/shreyasTalwar/TELEGRAM-BOT/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/shreyasTalwar/TELEGRAM-BOT/discussions)
- 📧 **Contact**: Open an issue for support

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

Made with ❤️ for ECE students

</div>
