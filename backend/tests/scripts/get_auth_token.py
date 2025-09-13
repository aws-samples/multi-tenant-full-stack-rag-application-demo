# get_auth_token.py
import boto3
import os
import json
import argparse
import sys

def get_token(client_id=None, username=None, password=None):
    """Get Cognito access token using provided or environment credentials"""
    # Use provided values or get from environment
    client_id = client_id or os.environ.get("COGNITO_CLIENT_ID")
    username = username or os.environ.get("COGNITO_USERNAME") 
    password = password or os.environ.get("COGNITO_PASSWORD")
    
    # Check if we have all required values
    if not all([client_id, username, password]):
        missing = []
        if not client_id: missing.append("COGNITO_CLIENT_ID")
        if not username: missing.append("COGNITO_USERNAME")
        if not password: missing.append("COGNITO_PASSWORD")
        
        print(f"Error: Missing required credentials: {', '.join(missing)}")
        print("Please provide them as arguments or environment variables.")
        sys.exit(1)
    
    try:
        # Create Cognito client
        client = boto3.client('cognito-idp')
        
        # Authenticate with username and password
        response = client.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        # Extract the token
        token = response['AuthenticationResult']['AccessToken']
        
        # Print the token
        print("\nAccess Token (for Authorization: Bearer):")
        print(f"Bearer {token}")
        
        # Show how to use it with curl
        print("\nCurl example:")
        print(f'curl -H "Authorization: Bearer {token}" https://your-api-endpoint/health')
        
        
        return token
        
    except Exception as e:
        print(f"Error getting token: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Add command line arguments
    parser = argparse.ArgumentParser(description='Get Cognito access token')
    parser.add_argument('--client-id', help='Cognito client ID')
    parser.add_argument('--username', help='Cognito username')
    parser.add_argument('--password', help='Cognito password')
    parser.add_argument('--quiet', action='store_true', help='Only output the token')
    
    args = parser.parse_args()
    
    # Get token
    token = get_token(args.client_id, args.username, args.password)
    
    # If quiet mode, just print the token
    if args.quiet:
        print(token)