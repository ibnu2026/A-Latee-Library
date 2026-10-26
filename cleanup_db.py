#!/usr/bin/env python3
"""
Clean up database - delete all visitors and fingerprints
Useful untuk start fresh tanpa data duplikat
"""

import sqlite3
import os
from LibraryDekstopApp import get_database_path

DB_FILE = get_database_path()

def cleanup_db():
    """Delete all visitors and fingerprints"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        print(f"[CLEANUP] Database: {DB_FILE}")
        
        # Check current data
        c.execute("SELECT COUNT(*) FROM visitors")
        visitor_count = c.fetchone()[0]
        print(f"[BEFORE] Visitors: {visitor_count}")
        
        c.execute("SELECT COUNT(*) FROM santri_fingerprints")
        fp_count = c.fetchone()[0]
        print(f"[BEFORE] Fingerprints: {fp_count}")
        
        # Delete all
        print("\n[ACTION] Deleting all visitors...")
        c.execute("DELETE FROM visitors")
        print(f"[ACTION] Deleted {c.rowcount} visitors")
        
        print("[ACTION] Deleting all fingerprints...")
        c.execute("DELETE FROM santri_fingerprints")
        print(f"[ACTION] Deleted {c.rowcount} fingerprints")
        
        # Reset ID sequences
        print("\n[ACTION] Resetting ID sequences...")
        c.execute("DELETE FROM sqlite_sequence WHERE name='visitors'")
        c.execute("DELETE FROM sqlite_sequence WHERE name='santri_fingerprints'")
        
        conn.commit()
        
        # Verify
        c.execute("SELECT COUNT(*) FROM visitors")
        visitor_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM santri_fingerprints")
        fp_count = c.fetchone()[0]
        
        print(f"\n[AFTER] Visitors: {visitor_count}")
        print(f"[AFTER] Fingerprints: {fp_count}")
        print("\n✅ Database cleaned successfully!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE CLEANUP - DELETE ALL VISITORS & FINGERPRINTS")
    print("=" * 60)
    print()
    
    response = input("⚠️  Are you sure? This will DELETE ALL DATA. Type 'YES' to confirm: ")
    if response.upper() == "YES":
        cleanup_db()
    else:
        print("Aborted.")
