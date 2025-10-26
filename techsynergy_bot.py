import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate environment variables
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is not set!")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY environment variable is not set!")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

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

# === AI Chat Handler ===
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
        
        response = client.chat.completions.create(
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

        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception as e:
        print(f"OpenAI Error: {e}")
        await update.message.reply_text("⚠️ Sorry, I'm having trouble connecting to our AI service. Please try again in a moment.")

# === Error Handler ===
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by Updates."""
    print(f"Update {update} caused error {context.error}")

# === Main Function ===
async def main():
    print("🤖 TechSynergy AI Bot is starting...")
    
    # Create Application instance
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("services", services))
    application.add_handler(CommandHandler("contact", contact))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start polling
    print("✅ TechSynergy AI Bot is now running...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())