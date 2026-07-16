"""
BankID Authentication Lambda
Initiate BankID authentication for Finnish customers during Amazon Connect calls.

This Lambda function:
1. Receives a personal number from Amazon Connect
2. Initiates BankID authentication via the BankID API
3. Returns orderRef for status polling

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

def lambda_handler(event, context):
    """
    Main Lambda handler for BankID authentication initiation.
    
    Expected event structure from Amazon Connect:
    {
        "Details": {
            "Parameters": {
                "personalNumber": "198509221234",
                "endUserIp": "192.0.2.1"  # Optional
            }
        }
    }
    
    Returns:
        dict: Authentication response with orderRef or error
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract parameters from Amazon Connect
        parameters = event.get('Details', {}).get('Parameters', {})
        personal_number = parameters.get('personalNumber', '')
        end_user_ip = parameters.get('endUserIp', '192.0.2.1')  # Default IP
        
        # Validate input
        if not personal_number:
            return {
                "status": "error",
                "error": "Missing personalNumber parameter"
            }
        
        print(f"Initiating BankID auth for personalNumber: {personal_number[:4]}****")
        
        # Get BankID credentials from Secrets Manager
        credentials = get_bankid_credentials()
        
        # Create SSL context
        ssl_context = create_ssl_context(
            credentials['cert_pem'],
            credentials['key_pem']
        )
        
        # Prepare BankID authentication request
        payload = {
            "personalNumber": personal_number,
            "endUserIp": end_user_ip,
            "requirement": {
                "pinCode": True  # Require PIN code for security
            }
        }
        
        # Make API request to BankID
        req = urllib.request.Request(
            f"{BANKID_API_URL}/auth",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method="POST"
        )
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            print(f"BankID auth initiated successfully. OrderRef: {result.get('orderRef')}")
            
            # Return success response for Amazon Connect
            return {
                "status": "pending",
                "orderRef": result.get("orderRef"),
                "autoStartToken": result.get("autoStartToken"),
                "qrStartToken": result.get("qrStartToken"),
                "message": "Authentication initiated successfully"
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
            "error": "Internal error during authentication",
            "details": str(e)
        }
