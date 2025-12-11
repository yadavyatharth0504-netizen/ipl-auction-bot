import os
import json
import logging
import sqlite3
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Flask

# --- 1. CONFIGURATION ---
# I have put your token directly here so it cannot fail
TOKEN = "8250315005:AAGDDZHqcYOp0_e7Ab6-aCzXx1-RDi6w_AY"

# Database setup
DB_URI = os.getenv("DATABASE_URL", "local_auction.db")
IS_ONLINE = "postgres" in DB_URI

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 2. DATABASE MANAGER ---
def get_db_connection():
    if IS_ONLINE:
        import psycopg2
        return psycopg2.connect(DB_URI)
    else:
        return sqlite3.connect("local_auction.db")

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
        CREATE TABLE IF NOT EXISTS auction_states (
            chat_id BIGINT PRIMARY KEY,
            data TEXT
        );
    """
    cur.execute(query)
    conn.commit()
    cur.close()
    conn.close()
    print("Database Initialized.")

def save_state(chat_id, data_dict):
    conn = get_db_connection()
    cur = conn.cursor()
    json_data = json.dumps(data_dict)
    
    if IS_ONLINE:
        query = """
            INSERT INTO auction_states (chat_id, data) VALUES (%s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET data = %s
        """
        cur.execute(query, (chat_id, json_data, json_data))
    else:
        query = """
            INSERT INTO auction_states (chat_id, data) VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET data = ?
        """
        cur.execute(query, (chat_id, json_data, json_data))
        
    conn.commit()
    cur.close()
    conn.close()

def load_state(chat_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    if IS_ONLINE:
        cur.execute("SELECT data FROM auction_states WHERE chat_id = %s", (chat_id,))
    else:
        cur.execute("SELECT data FROM auction_states WHERE chat_id = ?", (chat_id,))
        
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return None

# --- 3. BOT LOGIC ---
PLAYERS_DB = [
    {"name": "Virat Kohli", "role": "Batsman", "nat": "Indian", "base": 2.0},
    {"name": "Rohit Sharma", "role": "Batsman", "nat": "Indian", "base": 2.0},
    {"name": "Travis Head", "role": "Batsman", "nat": "Foreign", "base": 2.0},
]

async def start_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if load_state(chat_id):
        await update.message.reply_text("An auction is already active here!")
        return

    new_auction = {
        "admin": user_id,
        "state": "WAITING",
        "purse_limit": 100.0,
        "teams": {},
        "unsold": PLAYERS_DB.copy(),
        "sold": [],
        "current_bid": 0,
        "highest_bidder": None
    }
    
    save_state(chat_id, new_auction)
    await update.message.reply_text("Auction Initialized! You are the Auctioneer.\nUse /add_owner_team <TeamName> <UserID> to add teams.")

async def add_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    
    if not state: return
    if update.effective_user.id != state['admin']: return

    try:
        team_name = context.args[0]
        owner_id = int(context.args[1]) 
        
        state['teams'][team_name] = {
            "owner_id": owner_id,
            "spent": 0,
            "squad": [],
            "foreign_count": 0
        }
        
        save_state(chat_id, state)
        await update.message.reply_text(f"Team {team_name} added!")
    except:
        await update.message.reply_text("Usage: /add_owner_team Name ID")

async def get_team_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state(chat_id)
    
    if not state: return
    msg = "📋 Teams\n"
    for name, data in state['teams'].items():
        msg += f"\nTeam: {name}\nPurse Spent: {data['spent']}\nSquad: {data['squad']}\n"
        
    await update.message.reply_text(msg)

# --- 4. FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- 5. MAIN EXECUTION ---
if __name__ == '__main__':
    init_db()
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not found.")
    else:
        print("Bot Started... (Press Ctrl+C to stop)")
        application = ApplicationBuilder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start_auction", start_auction))
        application.add_handler(CommandHandler("add_owner_team", add_owner))
        application.add_handler(CommandHandler("teamlist", get_team_list))
        
        application.run_polling()