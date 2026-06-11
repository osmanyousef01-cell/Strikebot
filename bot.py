import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import discord
from discord.ext import commands
import aiohttp
import asyncio

# ==========================================
# DUMMY SERVER TO BYPASS RENDER PORT TIMEOUT
# ==========================================
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    # Quiet the log spam from Render's automatic pings
    def log_message(self, format, *args):
        return

def run_dummy_server():
    # Render automatically tells the bot what port to use via the PORT variable
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Spin up the server in a separate background thread so the bot can still run
threading.Thread(target=run_dummy_server, daemon=True).start()
# ==========================================

# ⚠️ YOUR SECRET DISCORD BOT TOKEN IS EMBEDDED BELOW:
TOKEN = os.getenv('MTQ1MTQxNDIxMzYzNjY1NzE5Mw.GXJhLl.WDGtLBct3NwBYMqf83zDUI-FarW_ssrVtior4Q')

# Your server's exact unique leaderboard registry ID
REGISTRY_ID = "obgEpL"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='^', intents=intents)

# Local dictionary tracking active strikes { member_id: strike_count }
strike_database = {}

# Tracks individuals who have historically hit the limit and served a 5d mute { member_id: True }
historical_mutes = {}

# Dynamic strike threshold limit (Defaults to 4, can be altered via command)
STRIKE_LIMIT = 4

# Helper function to find a member in the server by their plain text name or nickname
def find_member_by_name(guild, name_str: str):
    member = discord.utils.find(
        lambda m: name_str.lower() in [m.name.lower(), m.display_name.lower()], 
        guild.members
    )
    return member

@bot.event
async def on_ready():
    print(f'⚡ Strikebot is fully online and synced as {bot.user}')
    print(f'🏎️ Linked to Lorenzi Registry: {REGISTRY_ID}')
    print(f'⚙️ Current Strike Cap set to: {STRIKE_LIMIT}')


# ==================== AUTOMATED ROLE INTERCEPTORS ====================

async def auto_sync_highest_mmr(ctx, players_list):
    """Intercepts player lists dynamically to calculate and hand out the crown role automatically."""
    if not players_list:
        return

    valid_players = [p for p in players_list if p.get('mmr') is not None]
    if not valid_players:
        return
        
    highest_score = max(p['mmr'] for p in valid_players)
    top_player_names = [p['name'] for p in valid_players if p['mmr'] == highest_score]
    
    role_name = "Highest MMR 🏆"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    
    if not role:
        try:
            role = await ctx.guild.create_role(
                name=role_name, 
                color=discord.Color.from_rgb(155, 38, 182),
                hoist=True
            )
        except discord.Forbidden:
            return

    target_members = []
    for name in top_player_names:
        member = find_member_by_name(ctx.guild, name)
        if member:
            target_members.append(member)

    for old_holder in role.members:
        if old_holder not in target_members:
            try:
                await old_holder.remove_roles(role)
            except discord.Forbidden:
                pass

    for new_holder in target_members:
        if role not in new_holder.roles:
            try:
                await new_holder.add_roles(role)
                await ctx.send(f"👑 **Notice:** {new_holder.display_name} has taken the peak leaderboard spot (MMR: {highest_score}) and has been awarded the **{role_name}** role!")
            except discord.Forbidden:
                pass


# ==================== LORENZI LEADERBOARD INTEGRATIONS ====================

@bot.command(name='pavg10')
async def partner_average_10(ctx, username: str):
    """Calculates the score average of a user's teammates/partners across their last 10 events."""
    await ctx.send(f"📊 Fetching recent played match history data for `{username}`...")
    
    url = f"https://gb.hlorenzi.com/reg/{REGISTRY_ID}/matches?json=1"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send("❌ Error contacting the Lorenzi interface. Please try again later.")
                return
            
            all_matches = await response.json()
            partner_scores = []
            matches_counted = 0
            
            for match in all_matches:
                if matches_counted >= 10:
                    break
                    
                teams = match.get('teams', [])
                target_team = None
                
                for team in teams:
                    for player in team.get('players', []):
                        if player.get('name', '').lower() == username.lower():
                            target_team = team
                            break
                    if target_team:
                        break
                
                if target_team:
                    team_partners = []
                    for player in target_team.get('players', []):
                        if player.get('name', '').lower() != username.lower():
                            score = player.get('score')
                            if score is not None and str(score).strip() != "" and int(score) > 0:
                                team_partners.append(int(score))
                    
                    if team_partners:
                        partner_scores.extend(team_partners)
                        matches_counted += 1

            if matches_counted == 0:
                await ctx.send(f"❌ Could not find any recent completed team-based events with recorded scores for player `{username}`.")
                return
                
            if not partner_scores:
                await ctx.send(f"❌ Found upcoming or blank scheduled slots for `{username}`, but no historical score numbers are filled yet.")
                return
                
            avg_partner_score = sum(partner_scores) / len(partner_scores)
            
            await ctx.send(
                f"📈 **Partner Average (Last {matches_counted} Played Events) for {username}:**\n"
                f"➔ **{avg_partner_score:.2f}** score average per partner."
            )


@bot.command(name='leaderboard')
async def show_leaderboard(ctx):
    """Prints a direct link to your active server leaderboard rankings."""
    await ctx.send(f"🏆 **View our current server standings here:**\nhttps://gb.hlorenzi.com/reg/{REGISTRY_ID}")


@bot.command(name='stats')
async def get_player_stats(ctx, username: str):
    """Looks up a player's active competitive standing and syncs roles automatically."""
    await ctx.send(f"🔍 Searching for `{username}` in the registry standings...")
    
    url = f"https://gb.hlorenzi.com/reg/{REGISTRY_ID}?json=1"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                players_list = data.get('players', [])
                
                await auto_sync_highest_mmr(ctx, players_list)
                
                player_data = None
                for p in players_list:
                    if p.get('name', '').lower() == username.lower():
                        player_data = p
                        break
                
                if player_data:
                    mmr = player_data.get('mmr', 'Unrated')
                    rank = player_data.get('rank', 'N/A')
                    wins = player_data.get('wins', 0)
                    losses = player_data.get('losses', 0)
                    
                    embed = discord.Embed(title=f"🏁 Player Profile: {username}", color=discord.Color.blue())
                    embed.add_field(name="Current MMR", value=f"⭐ {mmr}", inline=True)
                    embed.add_field(name="Registry Rank", value=f"🏅 #{rank}", inline=True)
                    embed.add_field(name="Record (W/L)", value=f"📊 {wins}W - {losses}L", inline=True)
                    embed.set_footer(text=f"Registry ID: {REGISTRY_ID}")
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ User `{username}` hasn't joined or registered on this specific leaderboard ladder yet.")
            else:
                await ctx.send("❌ Unable to connect to the Lorenzi system interface right now.")


@bot.command(name='updatechampion')
@commands.has_any_role("moderator", "admin")
async def update_champion(ctx, username: str):
    """Automates competitive roles by assigning the top ranking server title."""
    member = find_member_by_name(ctx.guild, username)
    if not member:
        await ctx.send(f"❌ Could not find a user named '{username}' in this server.")
        return

    role_name = "CT Champion"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        role = await ctx.guild.create_role(name=role_name, color=discord.Color.gold(), hoist=True)
        await ctx.send(f"✨ Created missing competitive role: **{role_name}**")

    for old_champ in role.members:
        await old_champ.remove_roles(role)
        
    await member.add_roles(role)
    await ctx.send(f"🏆 **{member.display_name} has been crowned the new {role_name}!**")


# ==================== DISCIPLINARY STRIKE FEATURES ====================

@bot.command(name='setlimit')
@commands.has_any_role("moderator", "admin")
async def set_strike_limit(ctx, limit: int):
    """Changes the maximum strike threshold dynamically."""
    global STRIKE_LIMIT
    if limit <= 0:
        await ctx.send("❌ **Error:** The strike limit must be at least 1.")
        return
        
    STRIKE_LIMIT = limit
    await ctx.send(f"Strike limit has been updated to **{STRIKE_LIMIT}**.")


@bot.command()
async def addstrike(ctx, member: str, amount: int = 1, *, reason: str = "No reason provided"):
    # This keeps 'member' required, but lets amount default to 1 and reason default to blank!
    # Safety check if they just typed ^addstrike with nothing else
    if member is None:
        await ctx.send("❌ **Error:** Please specify a player name. Example: `^addstrike Lumis`")
        return

    # --- YOUR ORIGINAL STRIKE LOGIC STARTS HERE ---
    # (Keep whatever database or array saving lines you originally had below this)

    member_id = member.id
    strike_database[member_id] = strike_database.get(member_id, 0) + 1
    total_strikes = strike_database[member_id]
    
    # MATCHES EXPLICIT SNAPSHOT PATTERN EXACTLY
    await ctx.send(f"Strike added to **{member.display_name}**. New Count: **{total_strikes}/{STRIKE_LIMIT}**")

    if total_strikes >= STRIKE_LIMIT:
        mute_role_name = "Muted"
        mute_role = discord.utils.get(ctx.guild.roles, name=mute_role_name)
        
        if not mute_role:
            try:
                mute_role = await ctx.guild.create_role(
                    name=mute_role_name, 
                    color=discord.Color.dark_grey(), 
                    reason="Required for automated strike threshold enforcement."
                )
                await ctx.send(f"ℹ️ Created missing role: **{mute_role_name}**")
            except discord.Forbidden:
                await ctx.send("❌ **System Error:** Bot lacks permissions to generate roles.")
                return

        try:
            await member.add_roles(mute_role)
            await ctx.send(f"🔒 **{member.display_name} has hit the strike limit and has been Muted for 5 days.**")
            
            try:
                await member.send("You have been muted for 5d. Reason: Exceeded Strike Limit")
                print(f"📬 Dispatched mute infraction notification DM to {member.display_name}")
            except discord.Forbidden:
                print(f"⚠️ Could not DM profile {member.display_name} because their DMs are completely restricted.")

            async def unmute_countdown(target_member, target_role):
                await asyncio.sleep(432000)
                try:
                    await target_member.remove_roles(target_role)
                    
                    if target_member.id not in historical_mutes:
                        historical_mutes[target_member.id] = True
                        strike_database[target_member.id] = 1
                        print(f"🔓 First-offense timeout over for {target_member.display_name}. Reset to 1/{STRIKE_LIMIT} strikes.")
                    else:
                        del strike_database[target_member.id]
                        print(f"🔓 Repeat timeout over for {target_member.display_name}. Account cleared completely.")
                        
                except Exception as e:
                    print(f"⚠️ Error executing scheduled unmute profile action: {e}")

            asyncio.create_task(unmute_countdown(member, mute_role))
            
        except discord.Forbidden:
            await ctx.send("❌ **System Error:** Bot cannot assign the mute role. Move the bot's position higher in Server Settings > Roles!")


@bot.command(name='removestrike')
@commands.has_any_role("moderator", "admin")
async def remove_strike(ctx, username: str):
    """Removes a single strike using a plain username. Only accessible by staff."""
    member = find_member_by_name(ctx.guild, username)
    if not member:
        await ctx.send(f"❌ Could not find a user named '{username}' in this server.")
        return

    member_id = member.id
    current_strikes = strike_database.get(member_id, 0)

    if current_strikes == 0:
        await ctx.send(f"✅ {member.display_name} has a clean record! No strikes to remove.")
        return

    strike_database[member_id] -= 1
    new_total = strike_database[member_id]

    # MATCHES EXPLICIT SNAPSHOT PATTERN EXACTLY
    if new_total == 0:
        del strike_database[member_id]
        await ctx.send(f"Removed strike from **{member.display_name}**. New Count: **0/{STRIKE_LIMIT}**")
    else:
        await ctx.send(f"Removed strike from **{member.display_name}**. New Count: **{new_total}/{STRIKE_LIMIT}**")


@bot.command(name='strikes')
async def check_strikes(ctx, username: str = None):
    """Checks active strikes. Defaults to the message author if username is omitted."""
    if username is None:
        member = ctx.author
    else:
        member = find_member_by_name(ctx.guild, username)
        if not member:
            await ctx.send(f"❌ Could not find a user named '{username}' in this server.")
            return

    total_strikes = strike_database.get(member.id, 0)
    
    # Clean, compact field setup to match misete width
    embed = discord.Embed(color=discord.Color.from_rgb(31, 139, 212))
    embed.add_field(name=f"**{member.display_name}**", value=f"**{total_strikes}/{STRIKE_LIMIT}**", inline=False)
    
    # High-stability gaming wiki icon asset link
    LOGO_URL = "https://wiki.tockdom.com/w/images/e/e3/CTGP-R_Icon.png"
    embed.set_author(name="Strikes", icon_url=LOGO_URL)
    
    await ctx.send(embed=embed)


# ==================== ERROR HANDLING & SAFETY NETS ====================

@addstrike.error
@remove_strike.error
@update_champion.error
@set_strike_limit.error
async def strike_permission_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("🔒 **Error:** You do not have permission to manage competitive server states.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ **Error:** Missing input details. Check your command parameters.")

@get_player_stats.error
async def username_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ **Error:** Please specify a username to search.")


bot.run("MTQ1MTQxNDIxMzYzNjY1NzE5Mw.GXJhLl.WDGtLBct3NwBYMqf83zDUI-FarW_ssrVtior4Q")
