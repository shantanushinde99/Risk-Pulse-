import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
MAILJET_SECRET_KEY = os.getenv("MAILJET_SECRET_KEY")

# WARNING: This MUST match the email address you verified inside Mailjet!
SENDER_EMAIL = "h17847896@gmail.com" 

def send_confirmation_email(customer_email: str, action_type: str, amount: float):
    if not MAILJET_API_KEY or not MAILJET_SECRET_KEY or not customer_email:
        print("[Email Service] Skipping email: MAILJET keys missing or customer has no email on file.")
        return

    # Map the action type to a friendly name
    labels = {
        "TRANSFER_MONEY": f"transfer of ₹{amount:,.2f}",
        "CHANGE_PHONE": "phone number update",
        "CHANGE_EMAIL": "email address update",
        "ADD_BENEFICIARY": "new beneficiary addition",
        "RESET_PIN": "PIN reset"
    }
    
    action_label = labels.get(action_type, "recent request")
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eaeaea; border-radius: 8px; padding: 20px;">
        <h2 style="color: #059669; border-bottom: 1px solid #eaeaea; padding-bottom: 10px;">
            RiskPulse Bank - Security Alert
        </h2>
        <p style="color: #374151; font-size: 16px;">Hello,</p>
        <p style="color: #374151; font-size: 16px;">
            As per the request provided to our AI Voice Agent, we are writing to confirm that your <strong>{action_label}</strong> has been successfully processed after passing all required security guardrails.
        </p>
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 6px; margin: 20px 0;">
            <p style="margin: 0; color: #4b5563; font-size: 14px;">
                <strong>Status:</strong> <span style="color: #059669;">Approved & Processed</span>
            </p>
        </div>
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            If you did not authorize this action, please contact our fraud department immediately.
        </p>
        <br>
        <p style="color: #374151; font-size: 14px; margin-bottom: 0;">Stay secure,</p>
        <p style="color: #111827; font-weight: bold; margin-top: 5px;">RiskPulse Security Team</p>
    </div>
    """
    
    url = "https://api.mailjet.com/v3.1/send"
    
    payload = {
        "Messages": [
            {
                "From": {
                    "Email": SENDER_EMAIL,
                    "Name": "RiskPulse Alerts"
                },
                "To": [
                    {
                        "Email": customer_email
                    }
                ],
                "Subject": f"RiskPulse: {action_label.title().replace('Of', 'of')} Successful",
                "HTMLPart": html_content
            }
        ]
    }

    try:
        response = requests.post(
            url, 
            auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), 
            json=payload, 
            timeout=10
        )
        if response.status_code == 200:
            print(f"[Email Service] Successfully sent confirmation email via Mailjet to {customer_email}")
        else:
            print(f"[Email Service] Mailjet API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[Email Service] Failed to connect to Mailjet: {e}")
