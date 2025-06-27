import aiosqlite

async def init_moderation_db():
    async with aiosqlite.connect("moderation.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mutes (
                guild_id INTEGER,
                user_id INTEGER,
                unmute_at TEXT,
                PRIMARY KEY(guild_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mod_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                timestamp TEXT
            )
        """)
        await db.commit()


async def init_ticket_db():
    async with aiosqlite.connect("ticket_system.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ticket_settings (
                guild_id INTEGER PRIMARY KEY,
                admin_role_id INTEGER NOT NULL,
                opened_tickets_category_id INTEGER NOT NULL,
                closed_tickets_category_id INTEGER NOT NULL,
                log_channel_id INTEGER NOT NULL
            )
        ''')
        await db.commit()

async def init_economy_db():
    async with aiosqlite.connect("economy.db") as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS jobs (
            name TEXT PRIMARY KEY,
            payout_min INTEGER,
            payout_max INTEGER
        );

        CREATE TABLE IF NOT EXISTS items (
            name TEXT PRIMARY KEY,
            price INTEGER
        );

        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_name TEXT,
            quantity INTEGER,
            PRIMARY KEY (user_id, item_name)
        );

        CREATE TABLE IF NOT EXISTS robberies (
            name TEXT PRIMARY KEY,
            success_chance REAL,
            reward_min INTEGER,
            reward_max INTEGER
        );

        CREATE TABLE IF NOT EXISTS role_income (
            role_id INTEGER PRIMARY KEY,
            income_amount INTEGER
        );

        CREATE TABLE IF NOT EXISTS last_claims (
            user_id INTEGER PRIMARY KEY,
            last_claim TIMESTAMP
        );
        """)
        await db.commit()