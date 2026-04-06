import requests
import json
import os

# Your API credentials
#api_key = "4sdk51vjxptswokxo3gg1ptrxmeg3xlm"
api_key = os.getenv("API_KEY")
sender = "Ntswane"

# API endpoint
url = "https://restapi.easysendsms.app/v1/rest/sms/send"


def send_sms_message(to_number, message):
    try:
        # Headers
        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Request body
        payload = {
            "from": sender,
            "to": to_number,
            "text": message,
            "type": "0"
        }

        # Send POST request
        response = requests.post(url, json=payload, headers=headers)
        response = response.json()
        json_string = json.dumps(response)
        provider_message_id = response.get("messageIds")[0].split("OK: ")[-1].strip() if response else None
        # Print response
        print(provider_message_id)
        #print(response.json())  # Assuming JSON response
        return True, json_string, provider_message_id   # New add for meesage id
    except Exception as e:
        # Print response
        print(str(e))  # Assuming JSON response
        return False, str(e), None

