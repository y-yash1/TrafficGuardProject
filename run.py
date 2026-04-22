#!/usr/bin/env python3
"""
Traffic Guard TVM — Application Startup Script
Run this file to start the server: python3 run.py
"""
import os, sys

# ─── Validate Python version ───
if sys.version_info < (3, 8):
    print("❌ Python 3.8+ is required.")
    sys.exit(1)

# ─── Check Flask ───
try:
    import flask
except ImportError:
    print("❌ Flask not found. Install it with:\n   pip install flask\n   or\n   pip install -r requirements.txt")
    sys.exit(1)

# ─── Init DB then start server ───
from database.schema import init_db
init_db()

from app import app

if __name__ == '__main__':
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'
    
    print("\n" + "="*55)
    print("  🚦  TRAFFIC GUARD TVM  —  FULL STACK APP")
    print("="*55)
    print(f"\n  🌐  Open: http://127.0.0.1:{PORT}")
    print(f"\n  📋  Login Credentials:")
    print(f"       Citizen:  citizen1  /  1234")
    print(f"       Officer:  officer1  /  officer123")
    print(f"       Admin:    admin     /  admin123")
    print(f"\n  📁  Database:  database/traffic_guard.db")
    print(f"  🔑  Debug mode: {DEBUG}")
    print("="*55 + "\n")
    
    app.run(debug=DEBUG, host=HOST, port=PORT)
