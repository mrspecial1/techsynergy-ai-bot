#!/usr/bin/env python3
"""
Quick manual backup script
Usage: python manual_backup.py
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from backup import backup_inquiries, export_recent_inquiries

if __name__ == "__main__":
    print("🚀 Running manual backup...")
    
    # Full backup
    if backup_inquiries():
        print("✅ Full backup completed!")
    else:
        print("❌ Full backup failed!")
    
    # Recent inquiries export
    if export_recent_inquiries(30):  # Last 30 days
        print("✅ Recent inquiries exported!")
    
    print("🎉 Manual backup process completed!")