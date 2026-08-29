import os
import sys
sys.path.insert(0, "backend")

from app.services.email_service import send_confirmation_email
from dotenv import load_dotenv

load_dotenv("backend/.env")

# Grab the key to verify it loaded
api_key = os.getenv("MAILJET_API_KEY")
if not api_key:
    print("[Error] MAILJET_API_KEY is missing from backend/.env")
else:
    print("[Success] MAILJET_API_KEY found! Attempting to send test email...")
    
    # Send a test email to yourself
    # The first parameter is your email address where you want to RECEIVE the email
    customer_email = "gamersplayground437@gmail.com" # Change this if needed!
    
    try:
        send_confirmation_email(
            customer_email=customer_email, 
            action_type="TRANSFER_MONEY", 
            amount=5000.0
        )
    except Exception as e:
        print(f"Test failed: {e}")
