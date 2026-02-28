# TELEGRAM-BOT

A feature-rich Telegram bot for ECE study resources, including search, notes browsing, previous year papers, and robust performance/security enhancements.

## 🚀 Features

- **Subjects Supported:**
  - ARM & Embedded Systems
  - Advanced Communication Systems
  - AI & Machine Learning
  - Python Applications
  - Java Programming

- **User Commands:**
  - `/start`: Welcome & quick access
  - `/notes`: Browse study notes by subject and module
  - `/papers`: Download previous year question papers
  - `/search <text>`: Search materials across all subjects
  - Inline buttons for navigation, pagination, and batch downloads

- **Performance & Security:**
  - 📂 Cache with auto-refresh (5 min TTL)
  - ⏱️ Rate limiting (30 req/min)
  - 🚫 Path validation against directory traversal
  - 💾 20MB file size limit
  - 🔒 Secure logging (no secrets)

- **Deployment Highlights:**
  - Fully async I/O, serverless webhook support
  - Easy deployment to Vercel with environment variables
  - Local polling mode for development

## 🛠️ Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/shreyasTalwar/TELEGRAM-BOT.git
    cd TELEGRAM-BOT
    ```
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3. Set environment variables:
    - Copy `.env.example` to `.env` and set `TELEGRAM_TOKEN`.
    - For Vercel deployment, set `WEBHOOK_URL`.

## 📦 Usage

- **Start bot in local development:**
    ```bash
    python BOT2.PY
    ```
- **Deployment:**
    - Refer to `DEPLOYMENT_GUIDE.md` for instructions on Vercel deployment, webhook setup and troubleshooting.

## 💡 Tips

- Use `/search <keyword>` for fast file lookup.
- Check `QUICK_START.md` for performance and security tips.
- To add subjects, update the `SUBJECTS` dictionary and corresponding folders in `data/`.

## 📝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you’d like to change.

## 📄 License

*(Not specified yet)*

## 📚 More Info

- [QUICK_START.md](QUICK_START.md)
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md)

---

Happy coding! 🚀
