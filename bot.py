import os
import json
import logging
import random
import psycopg2
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Flask

# --- CONFIGURATION ---
TOKEN = "8250315005:AAGDDZHqcYOp0_e7Ab6-aCzXx1-RDi6w_AY"  # Your Token
DB_URI = os.getenv("DATABASE_URL")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- MOCK IPL 2026 PLAYER LIST ---
# Includes ID, Name, Role, Nationality, Base Price
MASTER_PLAYER_LIST = [
    {"id": 1, "name": "Virat Kohli", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 2, "name": "Rohit Sharma", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 3, "name": "Jasprit Bumrah", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 4, "name": "Suryakumar Yadav", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 5, "name": "Hardik Pandya", "role": "All-Rounder", "nat": "Indian", "base": 2.0},
    {"id": 6, "name": "Ravindra Jadeja", "role": "All-Rounder", "nat": "Indian", "base": 2.0},
    {"id": 7, "name": "Rishabh Pant", "role": "Wicketkeeper", "nat": "Indian", "base": 2.0},
    {"id": 8, "name": "Travis Head", "role": "Batter", "nat": "Foreign", "base": 2.0},
    {"id": 9, "name": "Pat Cummins", "role": "Bowler", "nat": "Foreign", "base": 2.0},
    {"id": 10, "name": "Heinrich Klaasen", "role": "Wicketkeeper", "nat": "Foreign", "base": 2.0},
    {"id": 11, "name": "Rashid Khan", "role": "Bowler", "nat": "Foreign", "base": 2.0},
    {"id": 12, "name": "Andre Russell", "role": "All-Rounder", "nat": "Foreign", "base": 2.0},
    {"id": 13, "name": "Matheesha Pathirana", "role": "Bowler", "nat": "Foreign", "base": 1.5},
    {"id": 14, "name": "Shubman Gill", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 15, "name": "Yashasvi Jaiswal", "role": "Batter", "nat": "Indian", "base": 2.0},
    {"id": 16, "name": "Rinku Singh", "role": "Batter", "nat": "Indian", "base": 1.0},
    {"id": 17, "name": "Mohammed Shami", "role": "Bowler", "nat": "Indian", "base": 2.0},
    {"id": 18, "name": "Jos Buttler", "role": "Wicketkeeper", "nat": "Foreign", "base": 2.0},
    {"id": 19, "name": "Trent Boult", "role": "Bowler", "nat": "Foreign", "base": 2.0}
    
]

# --- DATABASE MANAGER ---
def get_db_connection():
    return psycopg2.connect(DB_URI)

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS auction_states (
                chat_id BIGINT PRIMARY KEY,
                data TEXT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB Setup Error: {e}")

def save_state(chat_id, data_dict):
    conn = get_db_connection()
    cur = conn.cursor()
    json_data = json.dumps(data_dict)
    cur.execute("""
        INSERT INTO auction_states (chat_id, data) VALUES (%s, %s)
        ON CONFLICT (chat_id) DO UPDATE SET data = %s
    """, (chat_id, json_data, json_data))
    conn.commit()
    cur.close()
    conn.close()

def load_state(chat_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT data FROM auction_states WHERE chat_id = %s", (chat_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return json.loads(row[0]) if row else None

# --- HELPERS ---
def is_admin(user_id, state):
    return user_id == state['admin']

def get_player_by_arg(arg, player_list):
    """Finds a player by ID (int) or Name (string) in the given list"""
    arg_str = str(arg).lower()
    for p in player_list:
        if str(p['id']) == arg_str or p['name'].lower() == arg_str:
            return p
    return None

# --- COMMANDS ---

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
📚 **Auction Bot Commands**

**Auctioneer Only:**
/start_auction - Initialize the auction
/pause_auction - Pause bidding
/resume_auction - Resume bidding
/end_auction - Generate results and close
/add_owner <TeamName> - Reply to a user to add them
/remove_owner <TeamName> - Removes team, returns players to pool
/replace_owner <TeamName> - Reply to new user to swap owner
/new_player - Bring random player to auction
/player <Name/ID> - Bring specific player
/sold - Sell current player to highest bidder
/auctioneer_change - Reply to user to transfer admin rights

**Team Owners:**
/bid <amount> - Place a bid (in Crores)
/purse - Check funds
/teamlist - View squad and remaining purse
    """
    await update.message.reply_text(msg, parse_mode="Markdown")

async def start_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if load_state(chat_id):
        await update.message.reply_text("⚠ Auction already running! Use /end_auction first if you want to restart.")
        return

    # Initial State
    state = {
        "admin": user_id,
        "status": "IDLE", # IDLE, BIDDING, PAUSED
        "purse_limit": 100.0,
        "teams": {},
        "unsold": MASTER_PLAYER_LIST.copy(),
        "current_player": None,
        "current_bid": 0,
        "highest_bidder": None
    }
    save_state(chat_id, state)
    await update.message.reply_text(f"🚀 **Auction Started!**\nAuctioneer: {update.effective_user.first_name}\nUse /add_owner to set up teams.")

async def control_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state or not is_admin(update.effective_user.id, state): return
    
    cmd = update.message.text.split()[0] # /pause_auction, etc
    
    if "/pause" in cmd:
        state['status'] = "PAUSED"
        await update.message.reply_text("⏸ Auction Paused.")
    elif "/resume" in cmd:
        state['status'] = "IDLE" if state['current_player'] is None else "BIDDING"
        await update.message.reply_text("▶ Auction Resumed.")
    elif "/end" in cmd:
        # Generate PDF logic would go here
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM auction_states WHERE chat_id = %s", (chat_id,))
        conn.commit()
        await update.message.reply_text("🛑 Auction Ended. Data cleared.")
        return # Don't save state after delete

    save_state(chat_id, state)

async def add_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state or not is_admin(update.effective_user.id, state): return

    try:
        team_name = context.args[0]
        # Check if replied to a user
        if update.message.reply_to_message:
            target_id = update.message.reply_to_message.from_user.id
            target_name = update.message.reply_to_message.from_user.first_name
        else:
            # Fallback: try to read ID from 2nd arg
            target_id = int(context.args[1])
            target_name = "User"

        state['teams'][team_name] = {
            "owner_id": target_id,
            "owner_name": target_name,
            "spent": 0.0,
            "squad": []
        }
        save_state(chat_id, state)
        await update.message.reply_text(f"✅ Team **{team_name}** added for {target_name}!")
    except:
        await update.message.reply_text("Usage: /add_owner <TeamName> (Reply to the user!)")

async def remove_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state or not is_admin(update.effective_user.id, state): return

    try:
        team_name = context.args[0]
        if team_name not in state['teams']:
            await update.message.reply_text("Team not found.")
            return

        # Return players to unsold pool
        players_to_return = state['teams'][team_name]['squad']
        for p_data in players_to_return:
            state['unsold'].append(p_data)
        
        del state['teams'][team_name]
        save_state(chat_id, state)
        await update.message.reply_text(f"❌ Team **{team_name}** removed. {len(players_to_return)} players returned to auction pool.")
    except:
        await update.message.reply_text("Usage: /remove_owner <TeamName>")

async def replace_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state or not is_admin(update.effective_user.id, state): return

    try:
        team_name = context.args[0]
        if team_name not in state['teams']: return
        
        if update.message.reply_to_message:
            new_id = update.message.reply_to_message.from_user.id
            new_name = update.message.reply_to_message.from_user.first_name
            state['teams'][team_name]['owner_id'] = new_id
            state['teams'][team_name]['owner_name'] = new_name
            save_state(chat_id, state)
            await update.message.reply_text(f"🔄 Owner for **{team_name}** changed to {new_name}.")
        else:
            await update.message.reply_text("⚠ Please reply to the NEW owner with this command.")
    except:
        await update.message.reply_text("Usage: /replace_owner <TeamName> (Reply to user)")

async def auctioneer_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state or not is_admin(update.effective_user.id, state): return

    if update.message.reply_to_message:
        new_admin_id = update.message.reply_to_message.from_user.id
        new_admin_name = update.message.reply_to_message.from_user.first_name
        state['admin'] = new_admin_id
        save_state(chat_id, state)
        await update.message.reply_text(f"👑 Auctioneer changed! New Admin: {new_admin_name}")
    else:
        await update.message.reply_text("⚠ Reply to the user you want to make Auctioneer.")

async def bring_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state or not is_admin(update.effective_user.id, state): return
    if state['status'] == "PAUSED": 
        await update.message.reply_text("Auction is Paused.")
        return

    command = update.message.text.split()[0]
    player = None

    # Logic for random or specific player
    if "/new_player" in command:
        if not state['unsold']:
            await update.message.reply_text("No players left!")
            return
        player = random.choice(state['unsold'])
    elif "/player" in command:
        try:
            query = " ".join(context.args)
            player = get_player_by_arg(query, state['unsold'])
            if not player:
                await update.message.reply_text("Player not found in Unsold list.")
                return
        except:
            await update.message.reply_text("Usage: /player <Name or ID>")
            return

    # Set Global State
    state['current_player'] = player
    state['current_bid'] = player['base']
    state['highest_bidder'] = None
    state['status'] = "BIDDING"
    
    # Remove from unsold list (temporarily, add back if unsold)
    state['unsold'] = [p for p in state['unsold'] if p['id'] != player['id']]
    
    save_state(chat_id, state)
    
    msg = (f"🏏 **PLAYER ON AUCTION** 🏏\n"
           f"Name: {player['name']} (ID: {player['id']})\n"
           f"Role: {player['role']}\n"
           f"Nat: {player['nat']}\n"
           f"Base Price: {player['base']} Cr\n\n"
           f"Owners use /bid <amount> to buy!")
    await update.message.reply_text(msg, parse_mode="Markdown")

async def bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    state = load_state(chat_id)
    
    if not state: return
    if state['status'] != "BIDDING":
        await update.message.reply_text("🚫 Bidding is closed or paused.")
        return

    # Identify Team
    my_team_name = None
    for t_name, t_data in state['teams'].items():
        if t_data['owner_id'] == user_id:
            my_team_name = t_name
            break
            
    if not my_team_name:
        await update.message.reply_text("🚫 You are not a team owner.")
        return

    try:
        amount = float(context.args[0])
        team_data = state['teams'][my_team_name]
        
        # LOGIC CHECKS
        if amount <= state['current_bid']:
            await update.message.reply_text(f"⚠ Bid must be higher than {state['current_bid']} Cr.")
            return
        
        remaining_purse = state['purse_limit'] - team_data['spent']
        if amount > remaining_purse:
            await update.message.reply_text(f"💸 Insufficient funds! You have {remaining_purse:.2f} Cr.")
            return

        # Success
        state['current_bid'] = amount
        state['highest_bidder'] = my_team_name
        save_state(chat_id, state)
        await update.message.reply_text(f"💰 **{my_team_name}** bids {amount} Cr!")
        
    except:
        await update.message.reply_text("Usage: /bid <amount>")

async def sold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state or not is_admin(update.effective_user.id, state): return
    
    if state['status'] != "BIDDING" or not state['current_player']:
        await update.message.reply_text("No active player to sell.")
        return

    player = state['current_player']
    winner = state['highest_bidder']
    price = state['current_bid']

    if not winner:
        # Mark Unsold
        state['unsold'].append(player)
        await update.message.reply_text(f"❌ **{player['name']}** is UNSOLD.")
    else:
        # Process Sale
        state['teams'][winner]['spent'] += price
        # Add full player details to squad
        player['sold_price'] = price
        state['teams'][winner]['squad'].append(player)
        await update.message.reply_text(f"🔨 **SOLD!**\n{player['name']} to {winner} for {price} Cr!")

    # Reset Round
    state['current_player'] = None
    state['current_bid'] = 0
    state['highest_bidder'] = None
    state['status'] = "IDLE"
    save_state(chat_id, state)

async def view_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    if not state: return

    cmd = update.message.text.split()[0]
    
    if "/purse" in cmd:
        msg = "💰 **Purse Status**\n"
        for t_name, t_data in state['teams'].items():
            rem = state['purse_limit'] - t_data['spent']
            msg += f"{t_name}: {rem:.2f} Cr remaining\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    elif "/teamlist" in cmd:
        msg = "📋 **Squads**\n"
        for t_name, t_data in state['teams'].items():
            rem = state['purse_limit'] - t_data['spent']
            msg += f"\n🏆 **{t_name}** (Purse: {rem:.2f} Cr)\n"
            for p in t_data['squad']:
                msg += f"- {p['name']} ({p['sold_price']} Cr)\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

# --- FLASK SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "IPL 2026 Bot Alive"
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- MAIN ---
if __name__ == '__main__':
    init_db()
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    app_bot = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    app_bot.add_handler(CommandHandler("help", help_command))
    app_bot.add_handler(CommandHandler("start_auction", start_auction))
    app_bot.add_handler(CommandHandler("pause_auction", control_auction))
    app_bot.add_handler(CommandHandler("resume_auction", control_auction))
    app_bot.add_handler(CommandHandler("end_auction", control_auction))
    
    app_bot.add_handler(CommandHandler("add_owner", add_owner))
    app_bot.add_handler(CommandHandler("remove_owner", remove_owner))
    app_bot.add_handler(CommandHandler("replace_owner", replace_owner))
    app_bot.add_handler(CommandHandler("auctioneer_change", auctioneer_change))
    
    app_bot.add_handler(CommandHandler("new_player", bring_player))
    app_bot.add_handler(CommandHandler("player", bring_player))
    
    app_bot.add_handler(CommandHandler("bid", bid))
    app_bot.add_handler(CommandHandler("sold", sold))
    
    app_bot.add_handler(CommandHandler("purse", view_info))
    app_bot.add_handler(CommandHandler("teamlist", view_info))
    
    print("Bot Started...")
    app_bot.run_polling()

