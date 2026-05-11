# Way Back Clipboard

> A secure, local-first clipboard history manager for Windows that remembers everything you copy — forever.

Way Back Clipboard continuously monitors and securely stores your clipboard history locally on your machine.  
It supports both text and images, allowing you to search and recover clipboard data from days, months, or even years ago.

---

# ✨ Features

- 📄 Track copied text history
- 🖼️ Track copied images and screenshots
- 🔍 Search historical clipboard data
- 🕒 Recover clipboard entries from specific dates
- 🔐 Encrypted local storage
- 💾 Compressed archives for low disk usage
- ⚡ Smart application-aware clipboard switching
- 🗂️ Automatic archive management
- 💾 Backup rotation support
- 🧠 Keyword replacement engine

---

# 🕰️ Clipboard Time Travel

Way Back Clipboard acts like a time machine for your clipboard.

Examples:

```text
"What did I copy on 17 July 2025?"
```

or

```text
"Recover the screenshot I copied 8 months ago."
```

Way Back Clipboard can retrieve it instantly from local encrypted archives.

---

# 🔐 Local, Secure & Private

Way Back Clipboard is built with a **local-first architecture**.

Your clipboard data:

✅ Never leaves your computer  
✅ Is stored locally only  
✅ Is encrypted before storage  
✅ Works completely offline  
✅ Requires no cloud account  
✅ Has no telemetry or tracking  

Everything stays under your control.

---

# 💾 Storage Efficient

Way Back Clipboard uses:

- SQLite storage
- Compression
- Encrypted archives
- Automatic archiving

This keeps storage usage extremely low even with years of clipboard history.

---

# ⚡ Smart Clipboard Switching

The application can automatically switch clipboard content based on the active application.

Example:

| App | Clipboard Content |
|------|------------------|
| Browser | Original text |
| CRM Tool | Sanitized text |
| Internal Software | Auto-replaced keywords |

Useful for:

- Data masking
- Privacy filtering
- Workflow automation
- Enterprise environments

---

# 🧠 Example Use Cases

## Recover Lost Clipboard Data

```text
"I copied an API key last year."
```

Recover it instantly.

---

## Restore Old Screenshots

```text
"I copied a screenshot from a client meeting months ago."
```

Retrieve it from local archives.

---

## Automatic Text Replacement

Example:

```text
Copied:
john.doe@company.com

Pasted as:
support@company.com
```

depending on the active application.

---

# 🛠️ Technologies Used

- Python
- SQLite
- Windows API
- PyWin32
- Cryptography (Fernet)
- Pillow
- Pyperclip
- Psutil

---

# 📦 Project Structure

```text
WayBackClipboard/
│
├── clipboard_live.db
├── secret.key
├── archive/
├── backups/
├── main.py
└── README.md
```

---

# 🔧 Installation

## Requirements

- Windows
- Python 3.9+
- pip

---

## Install Dependencies

```bash
pip install pyperclip pillow cryptography pywin32 psutil
```

---

## Run the Application

```bash
python main.py
```

---

# 📂 Data Storage

Clipboard history is stored locally using:

- SQLite database
- Encrypted archives
- Rotating backups

No internet connection required.

---

# 🔒 Security

Way Back Clipboard uses:

- Fernet encryption
- Compressed encrypted archives
- Local key storage
- Automatic backup rotation

Your clipboard data remains private and secure.

---

# ⚠️ Important Notes

Because the application continuously monitors clipboard activity:

- Some antivirus software may flag it initially
- Add exclusions if needed
- Always review the source code before production use

---

# 🚀 Future Plans

Planned features include:

- Full GUI
- Fast search engine
- Timeline history view
- Regex filtering
- Clipboard analytics
- Encrypted sync
- Indexed search

---

# ❤️ Why Way Back Clipboard?

Clipboard history is temporary.

Important copied content gets lost every day:

- Notes
- Commands
- Screenshots
- Wallet addresses
- API keys
- Research
- Links
- Snippets

Way Back Clipboard ensures your copied data is always recoverable — securely, privately, and locally.

---

# 📄 License

MIT License
