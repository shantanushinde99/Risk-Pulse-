import os
import resend
from dotenv import load_dotenv

load_dotenv()

# We get the API key from the environment
resend.api_key = os.getenv("RESEND_API_KEY")

def send_confirmation_email(customer_email: str, action_type: str, amount: float):
    if not resend.api_key or not customer_email:
        print("[Email Service] Skipping email: API key missing or customer has no email on file.")
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
            This is an automated confirmation that your <strong>{action_label}</strong> was successfully processed by our AI Voice Agent after passing all security guardrails.
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
    
    try:
        resend.Emails.send({
            "from": "RiskPulse Alerts <onboarding@resend.dev>",
            "to": [customer_email],
            "subject": f"RiskPulse: {action_label.title().replace('Of', 'of')} Successful",
            "html": html_content
        })
        print(f"[Email Service] Successfully sent confirmation email to {customer_email}")
    except Exception as e:
        print(f"[Email Service] Failed to send email: {e}")
