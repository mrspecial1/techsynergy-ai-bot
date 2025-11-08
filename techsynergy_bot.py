import os
import logging
import psycopg
import smtplib
import re
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "info@techsynergyhq.com")

# Validate environment variables
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is not set!")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY environment variable is not set!")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL environment variable is not set!")

# Replace with your actual Telegram user ID
ADMIN_USER_ID = 6347949152  # ⚠️ CHANGE THIS TO YOUR TELEGRAM USER ID

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Database connection
def get_db_connection():
    return psycopg.connect(DATABASE_URL)

def create_inquiries_table():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
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
                    status VARCHAR(50) DEFAULT 'new',
                    contact_info TEXT
                )
            ''')
        conn.commit()
        conn.close()
        print("✅ Database table created successfully")
    except Exception as e:
        print(f"❌ Error creating table: {e}")

# === BACKUP FUNCTIONS ===
def backup_inquiries():
    """Backup all inquiries to a CSV file"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, user_id, username, first_name, last_name, 
                       message, response, created_at, status, contact_info
                FROM inquiries 
                ORDER BY created_at DESC
            ''')
            inquiries = cur.fetchall()
        
        # Create backup directory if it doesn't exist
        os.makedirs('backups', exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backups/inquiries_backup_{timestamp}.csv"
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Write header
            f.write("ID,User ID,Username,First Name,Last Name,Message,Response,Created At,Status,Contact Info\n")
            
            # Write data
            for inquiry in inquiries:
                # Escape commas and quotes in text fields
                escaped_fields = []
                for field in inquiry:
                    if field is None:
                        escaped_fields.append('')
                    else:
                        field_str = str(field).replace('"', '""').replace('\n', ' ')
                        if ',' in field_str or '"' in field_str:
                            escaped_fields.append(f'"{field_str}"')
                        else:
                            escaped_fields.append(field_str)
                
                f.write(','.join(escaped_fields) + '\n')
        
        conn.close()
        print(f"✅ Backup created: {filename} with {len(inquiries)} records")
        return True
        
    except Exception as e:
        print(f"❌ Backup error: {e}")
        return False

def export_recent_inquiries(days=7):
    """Export recent inquiries from the last N days"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, user_id, username, first_name, last_name, 
                       message, response, created_at, status, contact_info
                FROM inquiries 
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY created_at DESC
            ''', (days,))
            inquiries = cur.fetchall()
        
        # Create exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exports/recent_inquiries_{days}days_{timestamp}.csv"
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Write header
            f.write("ID,User ID,Username,First Name,Last Name,Message,Response,Created At,Status,Contact Info\n")
            
            # Write data
            for inquiry in inquiries:
                # Escape commas and quotes in text fields
                escaped_fields = []
                for field in inquiry:
                    if field is None:
                        escaped_fields.append('')
                    else:
                        field_str = str(field).replace('"', '""').replace('\n', ' ')
                        if ',' in field_str or '"' in field_str:
                            escaped_fields.append(f'"{field_str}"')
                        else:
                            escaped_fields.append(field_str)
                
                f.write(','.join(escaped_fields) + '\n')
        
        conn.close()
        print(f"✅ Export created: {filename} with {len(inquiries)} recent records")
        return True
        
    except Exception as e:
        print(f"❌ Export error: {e}")
        return False

# === BACKUP COMMAND ===
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        await update.message.reply_text("🔄 Starting database backup...")
        
        # Run backups
        backup_success = backup_inquiries()
        export_success = export_recent_inquiries(7)
        
        if backup_success:
            message = "✅ Backup completed successfully!\n"
            message += "• Full database backup created\n"
            if export_success:
                message += "• Recent inquiries exported\n"
            message += "📁 Check Render logs for file details"
        else:
            message = "❌ Backup failed. Check logs for details."
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Backup error: {e}")

# === INPUT VALIDATION FUNCTIONS ===
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_phone(phone):
    # Basic phone validation - accepts various formats
    pattern = r'^[\+]?[0-9\s\-\(\)]{10,}$'
    return re.match(pattern, phone) is not None

def contains_contact_info(message):
    """Check if message contains email or phone number"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    phone_pattern = r'[\+]?[0-9\s\-\(\)]{10,}'
    
    has_email = re.search(email_pattern, message) is not None
    has_phone = re.search(phone_pattern, message) is not None
    
    return has_email or has_phone, has_email, has_phone

# === EMAIL NOTIFICATION FUNCTION ===
def send_inquiry_notification(user_info, user_message, bot_response, contact_detected=False):
    if not all([EMAIL_USER, EMAIL_PASSWORD, NOTIFY_EMAIL]):
        print("⚠️ Email notifications disabled - missing email configuration")
        return
    
    try:
        subject = f"🔔 New Inquiry from {user_info['first_name']}"
        
        body = f"""
        🚀 NEW BUSINESS INQUIRY - TechSynergy Bot
        
        👤 CUSTOMER DETAILS:
        • Name: {user_info['first_name']} {user_info.get('last_name', '')}
        • Username: @{user_info.get('username', 'N/A')}
        • User ID: {user_info['user_id']}
        • Contact Info Detected: {'✅ Yes' if contact_detected else '❌ No'}
        
        💬 CUSTOMER MESSAGE:
        {user_message}
        
        🤖 BOT RESPONSE:
        {bot_response}
        
        📅 RECEIVED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        📊 STATUS: 🆕 NEW LEAD
        
        ⚡ ACTION REQUIRED: Please follow up with this potential client!
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = NOTIFY_EMAIL
        
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Notification email sent for user {user_info['user_id']}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

def save_inquiry(update: Update, user_message: str, bot_response: str):
    try:
        contact_detected, has_email, has_phone = contains_contact_info(user_message)
        contact_info = ""
        
        if has_email:
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', user_message)
            if email_match:
                contact_info = f"Email: {email_match.group()}"
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO inquiries (user_id, username, first_name, last_name, message, response, contact_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                update.effective_user.id,
                update.effective_user.username,
                update.effective_user.first_name,
                update.effective_user.last_name or '',
                user_message,
                bot_response,
                contact_info
            ))
        conn.commit()
        conn.close()
        
        # Send email notification
        user_info = {
            'user_id': update.effective_user.id,
            'username': update.effective_user.username,
            'first_name': update.effective_user.first_name,
            'last_name': update.effective_user.last_name or ''
        }
        send_inquiry_notification(user_info, user_message, bot_response, contact_detected)
        
        print(f"✅ Inquiry saved for user {update.effective_user.first_name}")
        return True
    except Exception as e:
        print(f"❌ Error saving inquiry: {e}")
        return False

# Initialize database on startup
create_inquiries_table()

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
    contact_message = (
        "📞 *Contact TechSynergy Solutions Limited*\n\n"
        "🌍 Website: https://techsynergyhq.com\n"
        "📧 Email: info@techsynergyhq.com\n"
        "📍 HQ: Port Harcourt, Rivers State, Nigeria\n"
        "☎️ Phone: +234 816 035 7708\n\n"
        "💡 *Pro Tip:* Include your email or phone number in your message for faster follow-up!"
    )
    await update.message.reply_text(contact_message, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Help Menu*\n\n"
        "Use the menu below or type:\n"
        "/about - Learn about TechSynergy\n"
        "/services - View services\n"
        "/contact - Get contact details\n"
        "/help - Show help again\n\n"
        "💼 *For Business Inquiries:*\n"
        "Simply tell me about your project needs and include your contact information for faster response!",
        parse_mode="Markdown",
        reply_markup=main_menu
    )

# === AI Chat Handler with Enhanced Features ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()

    # Input validation
    if not user_message or len(user_message) < 2:
        await update.message.reply_text("❌ Please provide a meaningful message (at least 2 characters).")
        return

    if len(user_message) > 1000:
        await update.message.reply_text("❌ Message too long. Please keep it under 1000 characters.")
        return

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
        
        # Enhanced system prompt to encourage contact info
        system_prompt = """You are TechSynergy AI Assistant. When users inquire about services:
        1. Be professional and helpful
        2. Ask clarifying questions about their project
        3. Gently encourage them to share contact information (email/phone) for faster follow-up
        4. Mention that our team will contact them promptly
        5. Keep responses concise but thorough"""
        
        # Use OpenAI client
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=500,
            temperature=0.7
        )

        bot_response = response.choices[0].message.content.strip()
        
        # Save inquiry to database
        save_success = save_inquiry(update, user_message, bot_response)
        
        # Send confirmation message to user
        contact_detected, _, _ = contains_contact_info(user_message)
        
        if contact_detected:
            confirmation = "✅ Thank you! Your project details and contact information have been received. Our TechSynergy team will contact you soon!"
        else:
            confirmation = "✅ Thank you for your inquiry! For faster follow-up, please share your email or phone number so our team can contact you directly."
        
        await update.message.reply_text(bot_response, parse_mode="Markdown")
        await update.message.reply_text(confirmation)
        
        # Additional prompt for contact info if not provided
        if not contact_detected and any(word in user_message.lower() for word in ['website', 'app', 'development', 'project', 'service', 'quote']):
            await update.message.reply_text(
                "📧 *Quick Follow-up:* Could you share your email or phone number so we can discuss your project in more detail?",
                parse_mode="Markdown"
            )

    except Exception as e:
        print(f"OpenAI Error: {e}")
        await update.message.reply_text("⚠️ Sorry, I'm having trouble connecting to our AI service. Please try again in a moment.")

# === ENHANCED ADMIN COMMANDS ===
async def view_inquiries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT username, first_name, message, created_at, status, contact_info
                FROM inquiries 
                ORDER BY created_at DESC 
                LIMIT 10
            ''')
            inquiries = cur.fetchall()
        conn.close()
        
        if not inquiries:
            await update.message.reply_text("📭 No inquiries yet.")
            return
        
        response = "📋 *Recent Inquiries (Last 10):*\n\n"
        for i, inquiry in enumerate(inquiries, 1):
            response += f"#{i} 👤 *{inquiry[1]}* (@{inquiry[0] or 'N/A'})\n"
            response += f"💬 {inquiry[2][:80]}...\n"
            response += f"⏰ {inquiry[3].strftime('%m/%d %H:%M')}\n"
            response += f"📊 Status: {inquiry[4]}\n"
            if inquiry[5]:
                response += f"📞 {inquiry[5]}\n"
            response += "─" * 30 + "\n"
        
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching inquiries: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Total inquiries
            cur.execute('SELECT COUNT(*) FROM inquiries')
            total = cur.fetchone()[0]
            
            # Today's inquiries
            cur.execute("SELECT COUNT(*) FROM inquiries WHERE DATE(created_at) = CURRENT_DATE")
            today = cur.fetchone()[0]
            
            # Inquiries with contact info
            cur.execute("SELECT COUNT(*) FROM inquiries WHERE contact_info != ''")
            with_contact = cur.fetchone()[0]
            
            # Status breakdown
            cur.execute("SELECT status, COUNT(*) FROM inquiries GROUP BY status")
            status_counts = cur.fetchall()
        
        conn.close()
        
        response = "📊 *Bot Statistics*\n\n"
        response += f"📈 Total Inquiries: {total}\n"
        response += f"📅 Today's Inquiries: {today}\n"
        response += f"📞 With Contact Info: {with_contact}\n\n"
        response += "📋 Status Breakdown:\n"
        for status, count in status_counts:
            response += f"• {status}: {count}\n"
        
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching stats: {e}")

# === Error Handler ===
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    application.add_handler(CommandHandler("inquiries", view_inquiries))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start polling
    print("✅ TechSynergy AI Bot is now running...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())