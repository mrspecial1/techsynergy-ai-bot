import os
import logging
import psycopg2
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import openai
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate environment variables
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is not set!")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY environment variable is not set!")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL environment variable is not set!")

# Database connection
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def create_inquiries_table():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS inquiries (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                message TEXT,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'new'
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database table created successfully")
    except Exception as e:
        print(f"❌ Error creating table: {e}")

def save_inquiry(update: Update, user_message: str, bot_response: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO inquiries (user_id, username, first_name, last_name, message, response)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            update.effective_user.id,
            update.effective_user.username,
            update.effective_user.first_name,
            update.effective_user.last_name or '',
            user_message,
            bot_response
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Inquiry saved for user {update.effective_user.first_name}")
    except Exception as e:
        print(f"❌ Error saving inquiry: {e}")

# Initialize database on startup
create_inquiries_table()

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# === Custom Keyboard Menu ===
main_menu = ReplyKeyboardMarkup(
    [
        ["💼 About Us", "🧠 Services"],
        ["📞 Contact", "❓ Help"]
    ],
    resize_keyboard=True
)

# === Command Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    welcome_message = (
        f"👋 Hello {user_first_name}!\n\n"
        "Welcome to *TechSynergy AI Assistant* 🤖\n\n"
        "I'm your smart business assistant from *TechSynergy Solutions Limited* — "
        "a leading provider of IT solutions, digital innovation, and technology consultancy.\n\n"
        "You can use the menu below or type your question to begin."
    )
    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=main_menu
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💼 *About TechSynergy Solutions Limited*\n\n"
        "TechSynergy Solutions is a full-service IT and innovation company providing professional services in:\n"
        "🌐 Web & Software Development\n"
        "📱 Mobile App Development\n"
        "☁️ Cloud & Infrastructure\n"
        "🔒 Cybersecurity Solutions\n"
        "🤖 AI & Automation\n"
        "🎥 Virtual & Hybrid Event Management\n\n"
        "Visit: https://techsynergyhq.com",
        parse_mode="Markdown"
    )

async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 *Our Core Services Include:*\n\n"
        "1️⃣ Web & Software Development\n"
        "2️⃣ Mobile App Development\n"
        "3️⃣ IT Consulting & Cloud Solutions\n"
        "4️⃣ Cybersecurity & Data Protection\n"
        "5️⃣ AI & Process Automation\n"
        "6️⃣ Virtual & Hybrid Events\n"
        "7️⃣ General Contracting & Real Estate Tech\n\n"
        "Need a custom solution? Just tell me your requirements!",
        parse_mode="Markdown"
    )

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Contact TechSynergy Solutions Limited*\n\n"
        "🌍 Website: https://techsynergyhq.com\n"
        "📧 Email: info@techsynergyhq.com\n"
        "📍 HQ: Port Harcourt, Rivers State, Nigeria\n"
        "☎️ Phone: +234 816 035 7708",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Help Menu*\n\n"
        "Use the menu below or type:\n"
        "/about - Learn about TechSynergy\n"
        "/services - View services\n"
        "/contact - Get contact details\n"
        "/help - Show help again",
        parse_mode="Markdown",
        reply_markup=main_menu
    )

# === AI Chat Handler with Database Saving ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    # Map button text to commands
    if user_message == "💼 About Us":
        return await about(update, context)
    elif user_message == "🧠 Services":
        return await services(update, context)
    elif user_message == "📞 Contact":
        return await contact(update, context)
    elif user_message == "❓ Help":
        return await help_command(update, context)

    try:
        # Show typing action
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Use OpenAI client
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """You are TechSynergy AI Assistant, a professional chatbot representing TechSynergy Solutions Limited. 
                    The company provides IT services including web development, mobile apps, cloud solutions, cybersecurity, AI automation, and virtual events.
                    Be helpful, professional, and concise. Always represent the company well."""
                },
                {"role": "user", "content": user_message},
            ],
            max_tokens=500,
            temperature=0.7
        )

        bot_response = response.choices[0].message.content.strip()
        
        # Save inquiry to database
        save_inquiry(update, user_message, bot_response)
        
        await update.message.reply_text(bot_response, parse_mode="Markdown")

    except Exception as e:
        print(f"OpenAI Error: {e}")
        await update.message.reply_text("⚠️ Sorry, I'm having trouble connecting to our AI service. Please try again in a moment.")

# === Admin Command to View Inquiries ===
async def view_inquiries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Replace with your actual Telegram user ID
    ADMIN_USER_ID = 6347949152  # ⚠️ CHANGE THIS TO YOUR TELEGRAM USER ID
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT username, first_name, message, created_at, status 
            FROM inquiries 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        inquiries = cur.fetchall()
        cur.close()
        conn.close()
        
        if not inquiries:
            await update.message.reply_text("📭 No inquiries yet.")
            return
        
        response = "📋 Recent Inquiries:\n\n"
        for inquiry in inquiries:
            response += f"👤 {inquiry[1]} (@{inquiry[0] or 'N/A'})\n"
            response += f"💬 {inquiry[2][:100]}...\n"
            response += f"⏰ {inquiry[3].strftime('%Y-%m-%d %H:%M')}\n"
            response += f"📊 Status: {inquiry[4]}\n"
            response += "─" * 30 + "\n"
        
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching inquiries: {e}")

# === Error Handler ===
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by Updates."""
    print(f"Update {update} caused error {context.error}")

# === Main Function ===
def main():
    print("🤖 TechSynergy AI Bot is starting...")
    
    # Create Application instance
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("services", services))
    application.add_handler(CommandHandler("contact", contact))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("inquiries", view_inquiries))  # Admin command
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start polling
    print("✅ TechSynergy AI Bot is now running...")
    application.run_polling()

if __name__ == "__main__":
    main()