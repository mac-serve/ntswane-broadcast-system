from twilio.rest import Client
import os

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

FROM_NUMBER = "whatsapp:+14155238886"

client = Client(ACCOUNT_SID, AUTH_TOKEN)


def send_whatsapp_message(to_number, message):
    try:
        msg = client.messages.create(
            from_=FROM_NUMBER,
            body=message,
            to=f"whatsapp:{to_number}"
        )
        return True, None
    except Exception as e:
        return False, str(e)
