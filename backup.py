import os
import psycopg
import csv
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def backup_inquiries():
    """
    Backup PostgreSQL inquiries table to CSV and optionally upload to cloud storage
    """
    try:
        print("🔄 Starting database backup...")
        
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            print("❌ DATABASE_URL not found")
            return False

        # Connect to database
        conn = psycopg.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # Get all inquiries
            cur.execute("""
                SELECT id, user_id, username, first_name, last_name, 
                       message, response, created_at, status, contact_info
                FROM inquiries 
                ORDER BY created_at DESC
            """)
            inquiries = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
        
        conn.close()
        
        if not inquiries:
            print("📭 No data to backup")
            return True

        # Create backup directory if it doesn't exist
        os.makedirs('backups', exist_ok=True)
        
        # Create backup file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backups/inquiries_backup_{timestamp}.csv"
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(inquiries)
        
        print(f"✅ Local backup created: {filename}")
        print(f"📊 Records backed up: {len(inquiries)}")
        
        # Upload to AWS S3 (optional)
        if upload_to_s3(filename):
            print("☁️ Backup uploaded to S3")
        
        # Clean up old local backups (keep last 7 days)
        cleanup_old_backups()
        
        return True
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def upload_to_s3(filename):
    """
    Optional: Upload backup to AWS S3
    """
    try:
        AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")
        
        if not all([AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_BUCKET]):
            print("⚠️ S3 credentials not configured - skipping cloud upload")
            return False
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        s3_filename = f"techsynergy-backups/{os.path.basename(filename)}"
        s3.upload_file(filename, AWS_BUCKET, s3_filename)
        return True
        
    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        return False

def cleanup_old_backups(days_to_keep=7):
    """
    Clean up backup files older than specified days
    """
    try:
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            return
        
        current_time = datetime.now().timestamp()
        cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
        
        deleted_count = 0
        for filename in os.listdir(backup_dir):
            if filename.startswith('inquiries_backup_') and filename.endswith('.csv'):
                filepath = os.path.join(backup_dir, filename)
                file_time = os.path.getmtime(filepath)
                
                if file_time < cutoff_time:
                    os.remove(filepath)
                    deleted_count += 1
                    print(f"🗑️ Deleted old backup: {filename}")
        
        if deleted_count > 0:
            print(f"🧹 Cleaned up {deleted_count} old backup files")
            
    except Exception as e:
        print(f"❌ Backup cleanup failed: {e}")

def export_recent_inquiries(days=30):
    """
    Export recent inquiries for quick review
    """
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = psycopg.connect(DATABASE_URL)
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, first_name, message, created_at, status, contact_info
                FROM inquiries 
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY created_at DESC
            """, (days,))
            
            inquiries = cur.fetchall()
            columns = ['username', 'first_name', 'message', 'created_at', 'status', 'contact_info']
        
        conn.close()
        
        if inquiries:
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"backups/recent_inquiries_{timestamp}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(inquiries)
            
            print(f"✅ Recent inquiries exported: {filename}")
            return filename
        
        return None
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("🔐 TechSynergy Database Backup System")
    print("=" * 50)
    
    # Run full backup
    success = backup_inquiries()
    
    # Export recent inquiries for quick review
    export_recent_inquiries(7)  # Last 7 days
    
    if success:
        print("🎉 Backup completed successfully!")
    else:
        print("❌ Backup failed!")
    
    print("=" * 50)