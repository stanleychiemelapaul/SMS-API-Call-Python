import mysql.connector
import requests
import mimetypes
from codecs import encode

# Database connection 
db_config = {
    'user': 'DB_USERNAME',
    'password': 'DB_PASSWORD',
    'host': 'localhost',
    'database': 'openmrs'
}

# KudiSMS API 
api_config = {
    'api_host': "my.kudisms.net",
    'api_endpoint': "/api/corporate",
    'api_key': "Your_API_KEY",
    'sender_id': "YOUR_APPROVED_SENDER_ID"
}


def send_sms(phone_number, message):
    apikey = api_config['api_key']
    senderid = api_config['sender_id']
    url = f"https://{api_config['api_host']}{api_config['api_endpoint']}"

    # Set up the multipart form data
    boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
    dataList = []
    
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name="token"'))
    dataList.append(encode('Content-Type: text/plain'))
    dataList.append(encode(''))
    dataList.append(encode(apikey))

    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name="senderID"'))
    dataList.append(encode('Content-Type: text/plain'))
    dataList.append(encode(''))
    dataList.append(encode(senderid))

    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name="recipients"'))
    dataList.append(encode('Content-Type: text/plain'))
    dataList.append(encode(''))
    dataList.append(encode(phone_number))

    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name="message"'))
    dataList.append(encode('Content-Type: text/plain'))
    dataList.append(encode(''))
    dataList.append(encode(message))

    dataList.append(encode('--'+boundary+'--'))
    dataList.append(encode(''))

    body = b'\r\n'.join(dataList)
    headers = {
        'Content-type': f'multipart/form-data; boundary={boundary}'
    }

    print(f"Sending request to {url}")
    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status()
        print(f"Response received: {response.text}")
        return response.json()  # Return the JSON response directly
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return {"status": "failed", "error_code": "HTTP_ERROR", "msg": str(http_err)}
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
        return {"status": "failed", "error_code": "CONNECTION_ERROR", "msg": str(conn_err)}
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
        return {"status": "failed", "error_code": "TIMEOUT_ERROR", "msg": str(timeout_err)}
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")
        return {"status": "failed", "error_code": "REQUEST_ERROR", "msg": str(req_err)}


def update_sms_status(cursor, phone_number, status):
    print(f"Updating SMS status for {phone_number} to '{status}'")
    update_query = """
    UPDATE BulkSMS
    SET SMS_Status = %s
    WHERE Phone_Number = %s
    """
    cursor.execute(update_query, (status, phone_number))


def process_bulk_sms():
    print("Starting process_bulk_sms function")
    try:
        # Establish database connection
        print("Connecting to the database...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        print("Database connection established")
        
        # Fetch clients from BulkSMS table
        print("Fetching clients from BulkSMS table...")
        fetch_query = "SELECT Phone_Number, Next_visit_date, PatientuiqueID FROM BulkSMS WHERE SMS_Status IS NULL"
        cursor.execute(fetch_query)
        clients = cursor.fetchall()
        print(f"Fetched {len(clients)} clients")

        # Loop through each client and send SMS
        for client in clients:
            phone_number = client['Phone_Number']
            message = f"Reminder: Your next visit is scheduled for {client['PatientuiqueID']}."
            print(f"Processing SMS for {phone_number}")
            
            # Send SMS and get the response
            response = send_sms(str(phone_number), message)
            
            # Interpret the API response
            status_code = response.get("error_code")
            
            if status_code == "000":
                update_sms_status(cursor, phone_number, "Sent")
            else:
                error_msg = {
                    "009": "Max SMS length exceeded",
                    "401": "Request could not be completed",
                    "100": "Invalid token",
                    "101": "Account deactivated",
                    "103": "Invalid gateway",
                    "104": "Blocked keyword(s)",
                    "105": "Blocked sender ID",
                    "106": "Sender ID does not exist",
                    "107": "Invalid phone number",
                    "108": "Batch size exceeded",
                    "109": "Insufficient balance",
                    "111": "Unapproved promotional Sender ID",
                    "114": "No package attached",
                    "187": "Request could not be processed",
                    "188": "Unapproved sender ID",
                    "300": "Missing parameters",
                    "HTTP_ERROR": "HTTP error occurred",
                    "CONNECTION_ERROR": "Connection error occurred",
                    "TIMEOUT_ERROR": "Timeout occurred",
                    "REQUEST_ERROR": "General request error"
                }.get(response.get("error_code"), "Unknown error")

                print(f"Failed to send SMS to {phone_number}: {error_msg} (Error code: {status_code})")
                update_sms_status(cursor, phone_number, "Failed")
        
        print("Committing changes to the database...")
        conn.commit()
        print("Changes committed successfully")
    
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
    
    finally:
        if conn.is_connected():
            print("Closing database connection...")
            cursor.close()
            conn.close()
            print("Database connection closed")


if __name__ == "__main__":
    print("Starting SMS processing script...")
    process_bulk_sms()
    print("SMS processing script completed")

