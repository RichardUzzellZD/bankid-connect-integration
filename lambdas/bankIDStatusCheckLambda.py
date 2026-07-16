"""
BankID Status Check Lambda
Poll BankID authentication status for Amazon Connect calls.

This Lambda function:
1. Receives an orderRef from Amazon Connect
2. Checks authentication status via BankID API
3. Returns status (pending/complete/failed) and user data if complete

Environment Variables:
- BANKID_API_URL: BankID API endpoint (test or production)
- BANKID_SECRET_NAME: AWS Secrets Manager secret containing certificates
"""

import json
import urllib.request
import urllib.error
import ssl
import os
import boto3
from botocore.exceptions import ClientError

# Configuration
BANKID_API_URL = os.environ.get("BANKID_API_URL", "https://appapi2.test.bankid.com/rp/v6.0")
BANKID_SECRET_NAME = os.environ.get("BANKID_SECRET_NAME", "finnish-bankid-test-credentials")

# Initialize AWS clients
secretsmanager_client = boto3.client('secretsmanager')

def get_bankid_credentials():
    """
    Retrieve BankID certificates from AWS Secrets Manager.
    
    Returns:
        dict: Contains cert_pem and key_pem
    """
    try:
        response = secretsmanager_client.get_secret_value(SecretId=BANKID_SECRET_NAME)
        secret = json.loads(response['SecretString'])
        return secret
    except ClientError as e:
        print(f"Error retrieving secrets: {e}")
        raise

def create_ssl_context(cert_pem, key_pem):
    """
    Create SSL context with BankID certificates.
    
    Args:
        cert_pem (str): Certificate in PEM format
        key_pem (str): Private key in PEM format
    
    Returns:
        ssl.SSLContext: Configured SSL context
    """
    # Write certificates to temp files (Lambda /tmp)
    cert_path = '/tmp/bankid-cert.pem'
    key_path = '/tmp/bankid-key.pem'
    
    with open(cert_path, 'w') as f:
        f.write(cert_pem)
    
    with open(key_path, 'w') as f:
        f.write(key_pem)
    
    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    
    return ssl_context

def get_user_message(hint_code):
    """
    Get user-friendly message based on BankID hint code.
    
    Args:
        hint_code (str): BankID hint code
    
    Returns:
        str: User-friendly message
    """
    messages = {
        "outstandingTransaction": "Waiting for you to open BankID app",
        "noClient": "BankID app not responding",
        "started": "Authentication started",
        "userSign": "Please confirm in your BankID app",
        "userCancel": "Authentication cancelled by user",
        "expiredTransaction": "Authentication timed out",
        "certificateErr": "Certificate error",
        "startFailed": "Failed to start BankID app"
    }
    return messages.get(hint_code, "Processing authentication")

def lambda_handler(event, context):
    """
    Main Lambda handler for BankID status checking.
    
    Expected event structure from Amazon Connect:
    {
        "Details": {
            "Parameters": {
                "orderRef": "131daac9-16c6-4618-beb0-365768f37288"
            }
        }
    }
    
    Returns:
        dict: Status response with user data (if complete) or error
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract orderRef from Amazon Connect
        parameters = event.get('Details', {}).get('Parameters', {})
        order_ref = parameters.get('orderRef', '')
        
        # Validate input
        if not order_ref:
            return {
                "status": "error",
                "error": "Missing orderRef parameter"
            }
        
        print(f"Checking BankID status for orderRef: {order_ref}")
        
        # Get BankID credentials from Secrets Manager
        credentials = get_bankid_credentials()
        
        # Create SSL context
        ssl_context = create_ssl_context(
            credentials['cert_pem'],
            credentials['key_pem']
        )
        
        # Prepare collect request
        payload = {
            "orderRef": order_ref
        }
        
        # Make API request to BankID
        req = urllib.request.Request(
            f"{BANKID_API_URL}/collect",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            status = result.get("status")
            print(f"BankID status: {status}")
            
            # Handle different status scenarios
            if status == "complete":
                # Authentication successful
                completion_data = result.get("completionData", {})
                user = completion_data.get("user", {})
                
                print(f"Authentication complete for: {user.get('givenName')} {user.get('surname')}")
                
                return {
                    "status": "complete",
                    "verified": "true",
                    "personalNumber": user.get("personalNumber"),
                    "givenName": user.get("givenName"),
                    "surname": user.get("surname"),
                    "fullName": user.get("name"),
                    "message": "Authentication completed successfully"
                }
            
            elif status == "pending":
                # Still waiting for user action
                hint_code = result.get("hintCode", "")
                
                return {
                    "status": "pending",
                    "hintCode": hint_code,
                    "message": get_user_message(hint_code)
                }
            
            elif status == "failed":
                # Authentication failed
                hint_code = result.get("hintCode", "")
                
                print(f"Authentication failed with hint: {hint_code}")
                
                return {
                    "status": "failed",
                    "hintCode": hint_code,
                    "message": get_user_message(hint_code)
                }
            
            else:
                # Unknown status
                return {
                    "status": "unknown",
                    "message": "Unknown status received from BankID"
                }
    
    except urllib.error.HTTPError as e:
        # Handle BankID API errors
        error_body = e.read().decode('utf-8')
        print(f"BankID API HTTP error {e.code}: {error_body}")
        
        return {
            "status": "error",
            "error": f"BankID API error: {e.code}",
            "details": error_body
        }
    
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error: {str(e)}")
        
        return {
            "status": "error",
            "error": "Internal error during status check",
            "details": str(e)
        }
