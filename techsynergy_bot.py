import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
def start(update: Update, context: CallbackContext):
    user_first_name = update.effective_user.first_name
    welcome_message = (
        f"👋 Hello {user_first_name}!\n\n"
        "Welcome to *TechSynergy AI Assistant* 🤖\n\n"
        "I’m your smart business assistant from *TechSynergy Solutions Limited* — "
        "a leading provider of IT solutions, digital innovation, and technology consultancy.\n\n"
        "You can use the menu below or type your question to begin."
    )

    update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=main_menu
    )

def about(update: Update, context: CallbackContext):
    update.message.reply_text(
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

def services(update: Update, context: CallbackContext):
    update.message.reply_text(
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

def contact(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📞 *Contact TechSynergy Solutions Limited*\n\n"
        "🌍 Website: https://techsynergyhq.com\n"
        "📧 Email: info@techsynergyhq.com\n"
        "📍 HQ: Port Harcourt, Rivers State, Nigeria\n"
        "☎️ Phone: +234 816 035 7708",
        parse_mode="Markdown"
    )

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
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
def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    chat_id = update.message.chat_id

    # Map button text to commands
    if user_message == "💼 About Us":
        return about(update, context)
    elif user_message == "🧠 Services":
        return services(update, context)
    elif user_message == "📞 Contact":
        return contact(update, context)
    elif user_message == "❓ Help":
        return help_command(update, context)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are TechSynergy AI Assistant, a professional, polite chatbot that represents TechSynergy Solutions Limited."},
                {"role": "user", "content": user_message},
            ],
        )

        reply = response.choices[0].message.content.strip()
        context.bot.send_message(chat_id=chat_id, text=reply)

    except Exception as e:
        print(f"Error: {e}")
        context.bot.send_message(chat_id=chat_id, text="⚠️ Sorry, something went wrong. Please try again later.")

# === Main Function ===
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("about", about))
    dp.add_handler(CommandHandler("services", services))
    dp.add_handler(CommandHandler("contact", contact))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    print("🤖 TechSynergy AI Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
