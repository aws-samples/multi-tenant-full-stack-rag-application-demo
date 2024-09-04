#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
from .auth_provider import AuthProvider
from .cognito_auth_provider_event import CognitoAuthProviderEvent
from multi_tenant_full_stack_rag_application.utils import format_response
cognito_auth_provider = None

# API 
# GET /auth/get_userid_from_token

class CognitoAuthProvider(AuthProvider):
    def __init__(self, 
        # account_id: str, 
        cognito_identity_pool_id: str,
        cognito_user_pool_id: str, 
        region: str=os.getenv('AWS_REGION', ''),
        cognito_identity_client=None,
        ssm_client=None,
    ):
        # self.account_id = account_id
        if not cognito_identity_client:
            self.cognito = boto3.client('cognito-identity', region)
        else:
            self.cognito = cognito_identity_client
        self.cognito_url = f"cognito-idp.{region}.amazonaws.com/{cognito_user_pool_id}"
        self.identity_pool_id = cognito_identity_pool_id
        self.user_pool_id = cognito_user_pool_id
        if not ssm_client:
            self.ssm = BotoClientProvider.get_client('ssm', region) 
        else:
            self.ssm = ssm_client
        
        origin_domain_name = ssm_client.get_parameter(
            Name=f'/{os.getenv("STACK_NAME")}/frontend_origin'
        )['Parameter']['Value']
        if not origin_domain_name.startswith('http'):
            origin_domain_name = f'https://{origin_domain_name}'
        self.frontend_origins = [   
            origin_domain_name
        ]

    def get_userid_from_token(self, auth_token, account_id):
        return self.cognito.get_id(
            AccountId=account_id,
            IdentityPoolId=self.identity_pool_id,
            Logins = {
                self.cognito_url: auth_token
            }
        )['IdentityId']
    
    def handler(self, event, context):
        print(f"CognitoAuthProvider.handler got event {event}")
        handler_evt = CognitoAuthProviderEvent().from_lambda_event(event)
        method = handler_evt.method
        path = handler_evt.path

        if handler_evt.origin not in self.frontend_origins:
            error = f"{handler_evt.origin} not in {self.frontend_origins}"
            return format_response(403, {"error": error}, handler_evt.origin)
        
        status = 200
        user_id = None

        if handler_evt.method == 'OPTIONS':
            result = {}

        if hasattr(handler_evt, 'auth_token') and handler_evt.auth_token is not None:
            user_id = self.get_userid_from_token(handler_evt.auth_token, handler_evt.account_id)
            handler_evt.user_id = user_id

        if handler_evt.method == 'GET' and \
            handler_evt.path == '/auth_provider':
                result = user_id
        else: 
            result = "ERROR: Unexpected method or path sent"
            status = 400

        return format_response(status, result, handler_evt.origin)
        
def handler(event, context):
    global cognito_auth_provider
    if not cognito_auth_provider:
        cognito_auth_provider = CognitoAuthProvider(
            account_id=os.getenv('AWS_ACCOUNT', ''),
            cognito_identity_pool_id=os.getenv('IDENTITY_POOL_ID', ''),
            cognito_user_pool_id=os.getenv('USER_POOL_ID', ''),
            region=os.getenv('AWS_REGION', ''))
    return cognito_auth_provider.handler(event, context)


    