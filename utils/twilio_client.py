from twilio.rest import Client

account_sid = 'AC847b514e17b0bcd06432f0701f49c6fd'
auth_token = '8ebb3a7a1bcc8e8fb2d7ea36f6a2b8d9'

client = Client(account_sid, auth_token)

def send_whatsapp_message(to_number: str, message: str):
    try:
        msg = client.messages.create(
            from_='whatsapp:+14155238886',
            body=message,
            to=f'whatsapp:{to_number}'
        )
        return msg.sid
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")
        return None
