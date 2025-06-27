import discord
from discord.ext import commands
import aiosqlite
import random
from datetime import datetime, timedelta, timezone
import asyncio

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_lock = asyncio.Lock()

    async def get_balance(self, user_id: int):
        async with aiosqlite.connect("economy.db", timeout=10) as db:
            await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0))
            await db.commit()
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0]

    async def update_balance(self, user_id: int, amount: int, db=None):
        # Use provided db connection if available to prevent concurrent writes
        if db is None:
            async with aiosqlite.connect("economy.db", timeout=10) as new_db:
                await new_db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0))
                await new_db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
                await new_db.commit()
        else:
            await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))

    @commands.hybrid_command(name="balance", description="Check your balance.")
    async def balance(self, ctx):
        balance = await self.get_balance(ctx.author.id)
        await ctx.send(f"💰 {ctx.author.mention}, you have **${balance:,}**")

    @commands.hybrid_command(name="work", description="Work a job for money.")
    async def work(self, ctx):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                async with db.execute("SELECT name, payout_min, payout_max FROM jobs") as cursor:
                    jobs = await cursor.fetchall()
                    if not jobs:
                        return await ctx.send("No jobs available. Ask an admin to add some using `/addjob`.")
                    job = random.choice(jobs)
                    payout = random.randint(job[1], job[2])
                    await self.update_balance(ctx.author.id, payout, db)
                    await db.commit()
                    await ctx.send(f"🛠️ You worked as a **{job[0]}** and earned **${payout:,}**!")

    @commands.hybrid_command(name="claim", description="Claim income from your roles.")
    async def claim(self, ctx: commands.Context):
        await ctx.defer()
        now = datetime.now(timezone.utc)
        user_id = ctx.author.id
        print("1. Claim command invoked by user:", user_id)

        async with self.db_lock:
            try:
                async with aiosqlite.connect("economy.db", timeout=10) as db:
                    # Ensure the user exists in the last_claims table
                    await db.execute("INSERT OR IGNORE INTO last_claims (user_id, last_claim) VALUES (?, ?)", (user_id, None))

                    # Check last claim time
                    async with db.execute("SELECT last_claim FROM last_claims WHERE user_id = ?", (user_id,)) as cursor:
                        result = await cursor.fetchone()
                        last_claim_raw = result[0] if result else None
                        print("2. Last claim fetched for user:", user_id, "Last claim time:", last_claim_raw)

                        if last_claim_raw is not None:
                            last_claim = datetime.fromisoformat(last_claim_raw).replace(tzinfo=timezone.utc)
                            if now - last_claim < timedelta(hours=24):
                                return await ctx.send("🕒 You already claimed your role income today. Come back later!")

                    # Update the last claim timestamp
                    await db.execute("UPDATE last_claims SET last_claim = ? WHERE user_id = ?", (now.isoformat(), user_id))
                    print("3. Last claim updated for user:", user_id, "New claim time:", now.isoformat())

                    # Calculate role-based income with detailed logging
                    total_income = 0
                    roles_with_income = []
                    roles_checked = []

                    for role in ctx.author.roles:
                        if role == ctx.guild.default_role:
                            continue

                        async with db.execute("SELECT income_amount FROM role_income WHERE role_id = ?", (role.id,)) as cursor:
                            row = await cursor.fetchone()
                            income = row[0] if row else 0
                            roles_checked.append(f"{role.name}: ${income}")

                            if income > 0:
                                roles_with_income.append(f"{role.name}: ${income}")
                                total_income += income

                            print(f"4. Checking role {role.name} for user {user_id}: Income amount found: {row}")

                    # Log summary of all roles
                    print(f"4a. All roles checked for user {user_id}: {roles_checked}")
                    print(f"4b. Roles with income for user {user_id}: {roles_with_income}")
                    print(f"5. Total income calculated for user {user_id}: ${total_income}")

                    # Update balance with shared DB connection
                    await self.update_balance(user_id, total_income, db)
                    print(f"6. Balance updated for user {user_id}")

                    # Commit changes
                    await db.commit()
                    print(f"7. Database changes committed for user {user_id}")

            except Exception as e:
                print(f"Critical error in claim command for user {user_id}: {e}")
                return await ctx.send("❌ An error occurred while processing your claim. Please try again later.")

        # Final response
        if total_income == 0:
            await ctx.send("""✅ Claim successful, but none of your roles have income configured.
-# If you are an admin, use `/addroleincome` to set income for roles.""")
        else:
            await ctx.send(f"💼 You claimed **${total_income:,}** from your roles.")

    @commands.hybrid_command(name="rob", description="Rob another user.")
    async def rob(self, ctx, target: discord.Member):
        if target.id == ctx.author.id:
            return await ctx.send("You can't rob yourself.")
        async with self.db_lock:
            target_balance = await self.get_balance(target.id)
            if target_balance < 100:
                return await ctx.send("Target doesn't have enough money.")
            success = random.random() < 0.5
            amount = random.randint(50, min(500, target_balance))
            if success:
                await self.update_balance(ctx.author.id, amount)
                await self.update_balance(target.id, -amount)
                await ctx.send(f"💰 You successfully robbed {target.mention} for **${amount:,}**!")
            else:
                await self.update_balance(ctx.author.id, -amount)
                await ctx.send(f"🚓 You got caught and lost **${amount:,}**!")

    @commands.hybrid_command(name="crime", description="Attempt a crime for money.")
    async def crime(self, ctx):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                async with db.execute("SELECT name, success_chance, reward_min, reward_max FROM robberies") as cursor:
                    crimes = await cursor.fetchall()
                    if not crimes:
                        return await ctx.send("No crimes available. Ask an admin to add some using `/addrobbery`.")
                    crime = random.choice(crimes)
                    success = random.random() < (crime[1] / 100)  # <-- fix here
                    reward = random.randint(crime[2], crime[3])
                    if success:
                        await self.update_balance(ctx.author.id, reward, db)
                        await ctx.send(f"🦹‍♂️ You succeeded in **{crime[0]}** and earned **${reward:,}**!")
                    else:
                        await self.update_balance(ctx.author.id, -reward, db)
                        await ctx.send(f"👮 You failed in **{crime[0]}** and lost **${reward:,}**!")
                await db.commit()


    @commands.hybrid_command(name="addjob", description="Admin: Add a job.")
    @commands.has_permissions(administrator=True)
    async def add_job(self, ctx, name: str, min_pay: int, max_pay: int):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                await db.execute("INSERT OR REPLACE INTO jobs (name, payout_min, payout_max) VALUES (?, ?, ?)", (name, min_pay, max_pay))
                await db.commit()
                await ctx.send(f"✅ Job **{name}** added with payout range ${min_pay:,}–${max_pay:,}")

    @commands.hybrid_command(name="removejob", description="Admin: Remove a job.")
    @commands.has_permissions(administrator=True)
    async def remove_job(self, ctx, name: str):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                result = await db.execute("DELETE FROM jobs WHERE name = ?", (name,))
                await db.commit()
                if result.rowcount == 0:
                    await ctx.send(f"❌ No job named **{name}** found.")
                else:
                    await ctx.send(f"🗑️ Job **{name}** removed.")

    @commands.hybrid_command(name="addrobbery", description="Admin: Add a robbery scenario.")
    @commands.has_permissions(administrator=True)
    async def add_robbery(self, ctx, name: str, success_chance: float, min_reward: int, max_reward: int):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                await db.execute("INSERT OR REPLACE INTO robberies (name, success_chance, reward_min, reward_max) VALUES (?, ?, ?, ?)", (name, success_chance, min_reward, max_reward))
                await db.commit()
                await ctx.send(f"✅ Robbery **{name}** added with success chance {success_chance:.2f}")

    @commands.hybrid_command(name="removerobbery", description="Admin: Remove a robbery scenario.")
    @commands.has_permissions(administrator=True)
    async def remove_robbery(self, ctx, name: str):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                result = await db.execute("DELETE FROM robberies WHERE name = ?", (name,))
                await db.commit()
                if result.rowcount == 0:
                    await ctx.send(f"❌ No robbery named **{name}** found.")
                else:
                    await ctx.send(f"🗑️ Robbery **{name}** removed.")

    @commands.hybrid_command(name="additem", description="Admin: Add a shop item.")
    @commands.has_permissions(administrator=True)
    async def add_item(self, ctx, name: str, price: int):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                await db.execute("INSERT OR REPLACE INTO items (name, price) VALUES (?, ?)", (name.lower(), price))
                await db.commit()
                await ctx.send(f"🛍️ Added item **{name}** for ${price:,}")

    @commands.hybrid_command(name="removeitem", description="Admin: Remove a shop item.")
    @commands.has_permissions(administrator=True)
    async def remove_item(self, ctx, name: str):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                result = await db.execute("DELETE FROM items WHERE name = ?", (name.lower(),))
                await db.commit()
                if result.rowcount == 0:
                    await ctx.send(f"❌ No item named **{name}** found.")
                else:
                    await ctx.send(f"🗑️ Item **{name}** removed.")

    @commands.hybrid_command(name="addroleincome", description="Admin: Set income for a role.")
    @commands.has_permissions(administrator=True)
    async def add_role_income(self, ctx, role: discord.Role, amount: int):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                await db.execute("INSERT OR REPLACE INTO role_income (role_id, income_amount) VALUES (?, ?)", (role.id, amount))
                await db.commit()
                await ctx.send(f"✅ Set role {role.mention} to receive ${amount:,} on claim.")

    @commands.hybrid_command(name="removeroleincome", description="Admin: Remove income for a role.")
    @commands.has_permissions(administrator=True)
    async def remove_role_income(self, ctx, role: discord.Role):
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                result = await db.execute("DELETE FROM role_income WHERE role_id = ?", (role.id,))
                await db.commit()
                if result.rowcount == 0:
                    await ctx.send(f"❌ No income set for role {role.mention}.")
                else:
                    await ctx.send(f"🗑️ Removed income for role {role.mention}.")

    @commands.hybrid_command(name="shop", description="View available items.")
    async def shop(self, ctx):
        async with aiosqlite.connect("economy.db", timeout=10) as db:
            async with db.execute("SELECT name, price FROM items") as cursor:
                items = await cursor.fetchall()
                if not items:
                    return await ctx.send("No items in the shop.")
                embed = discord.Embed(title="🛒 Shop")
                for item in items:
                    embed.add_field(name=item[0].title(), value=f"${item[1]:,}", inline=False)
                await ctx.send(embed=embed)

    @commands.hybrid_command(name="buy", description="Buy an item from the shop.")
    async def buy(self, ctx, item_name: str, quantity: int = 1):
        item_name = item_name.lower()
        async with self.db_lock:
            async with aiosqlite.connect("economy.db", timeout=10) as db:
                async with db.execute("SELECT price FROM items WHERE name = ?", (item_name,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return await ctx.send("Item not found.")
                    total_cost = row[0] * quantity
                    balance = await self.get_balance(ctx.author.id)
                    if balance < total_cost:
                        return await ctx.send("You don't have enough money.")
                    await self.update_balance(ctx.author.id, -total_cost, db)
                    await db.execute(
                        "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?) "
                        "ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?",
                        (ctx.author.id, item_name, quantity, quantity)
                    )
                    await db.commit()
                    await ctx.send(f"✅ You bought {quantity}x **{item_name.title()}** for **${total_cost:,}**")

    @commands.hybrid_command(name="inventory", description="Check your inventory.")
    async def inventory(self, ctx):
        async with aiosqlite.connect("economy.db", timeout=10) as db:
            async with db.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (ctx.author.id,)) as cursor:
                items = await cursor.fetchall()
                if not items:
                    return await ctx.send("Your inventory is empty.")
                embed = discord.Embed(title=f"{ctx.author.name}'s Inventory")
                for item in items:
                    embed.add_field(name=item[0].title(), value=f"x{item[1]}", inline=False)
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
