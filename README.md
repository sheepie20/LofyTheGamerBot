# 🎮 LofyTheGamer Discord Bot

A powerful multipurpose Discord bot built for **LofyTheGamer** featuring economy, moderation, shop, jobs, crime, and more.

## 📦 Features

- 💰 Full economy system (balance, jobs, crime, shop, role income)
- 🛠️ Admin tools to configure jobs, roles, items, and robberies
- 🔨 Advanced moderation (kick, ban, mute, timeout, unban, logs)
- 🎫 Easy and advanced ticketing system.
- 📜 Slash command support
- 🗄️ SQLite-powered data storage
- 🔒 Database-safe with async locking

---

## 🚀 Installation Guide

### 1. Clone the Repository

```bash
git clone https://github.com/sheepie20/LofyTheGamerBot.git
cd LofyTheGamerBot
````

### 2. Set Up Python Environment

Make sure you have **Python 3.10+** installed.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# OR
source .venv/bin/activate     # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the root directory with the following:

```env
TOKEN=your-bot-token-here
```

> 🔒 Keep your token secret and never commit it to GitHub.

## ⚙️ Bot Structure

```
📁 LofyTheGamerBot/
├── cogs/
│   ├── economy.py
│   └── moderation.py
├── .env
├── economy.db
├── moderation.db
├── main.py
└── README.md
```

---

## ▶️ Running the Bot

```bash
python main.py
```

You should see:

```
Tree loaded successfully
logged in as [bot name]#[bot discriminator] (Bot ID)
```

---

## 🧪 Slash Commands Setup

This bot uses [discord.py's command tree system](https://discordpy.readthedocs.io/en/stable/ext/commands/commands.html#app-commands):

* All commands are registered on startup.
* Use `/sync-tree` manually or automatically register on launch.
* Some commands are permission-locked (e.g., `/addjob`, `/ban`).

---

## 📁 Economy Commands

| Command      | Description                     |
| ------------ | ------------------------------- |
| `/balance`   | Check your wallet               |
| `/work`      | Earn a random amount from a job |
| `/claim`     | Collect role-based income       |
| `/crime`     | Attempt a risky crime           |
| `/rob`       | Rob another user                |
| `/shop`      | View purchasable items          |
| `/buy`       | Buy an item                     |
| `/inventory` | Check your owned items          |

Admin-only:

* `/addjob`
* `/additem`
* `/addrobbery`
* `/addroleincome`

---

## 🛡️ Moderation Commands

| Command    | Description                     |
| ---------- | ------------------------------- |
| `/kick`    | Kick a member                   |
| `/ban`     | Ban a member                    |
| `/unban`   | Unban by username#discrim       |
| `/banlist` | List all logged bans            |
| `/mute`    | Mute a member (role or timeout) |
| `/unmute`  | Unmute a member                 |
| `/timeout` | Temporarily mute a member       |
| `/purge`   | Bulk delete messages            |

All actions are logged in the `moderation.db` for record keeping.

---

## 📚 Database Tables

**economy.db:**

* `users`
* `jobs`
* `robberies`
* `items`
* `inventory`
* `role_income`
* `last_claims`

**moderation.db:**

* `mod_actions` (all mod logs)
* `mutes` (for unmute tracking)

**ticket_system.db:**

* `ticket_settings` (server configurations)

---

## 🛠️ Customization

You can edit values such as income rates, item prices, and more via the `/add...` commands or directly through the database if needed.

---

## 🧑‍💻 Credits

Built by [sheepie20](https://github.com/sheepie20) for **LofyTheGamer**.

---

## 📄 License

MIT License — free for personal and commercial use.

