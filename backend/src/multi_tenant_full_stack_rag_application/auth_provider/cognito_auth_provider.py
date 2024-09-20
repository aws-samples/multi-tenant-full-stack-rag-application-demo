#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
import time
from .auth_provider import AuthProvider
from .cognito_auth_provider_event import CognitoAuthProviderEvent
from multi_tenant_full_stack_rag_application import utils 

cognito_auth_provider = None

# Event structure:
#  "operation": [get_creds | get_userid_from_token]
#        "origin": the origin of the caller (either the frontend origin or the fn name of 
#                   the calling Lambda function)
#       "args":
#           get_creds_from_token: get sts creds for a given cognito identity pool identity ID and a jwt.
#               Request:
#                   user_id: cognito identity pool identity id,
#                   auth_token: cognito auth token
#               Response:
#                   credentials: boto credentials
#           get_userid_from_token: return the cognito idp user id given the jwt.
#               Request:
#                   auth_token: cognito auth_token
#               Response:
#                   user_id: cognito identity pool identity id,


class CognitoAuthProvider(AuthProvider):
    def __init__(self, 
        cognito_identity_pool_id: str,
        cognito_user_pool_id: str, 
        region: str=os.getenv('AWS_REGION', ''),
        cognito_identity_client=None,
        cognito_idp_client=None,
        ssm_client=None
    ):
        self.utils = utils
        self.account_id = os.getenv('AWS_ACCOUNT_ID')
        print(f"Account id is {self.account_id}")
        if not cognito_identity_client:
            self.cognito_identity = self.utils.BotoClientProvider.get_client('cognito-identity')
        else:
            self.cognito_identity = cognito_identity_client
       
        if not cognito_idp_client:
            self.cognito_idp = self.utils.BotoClientProvider.get_client('cognito-idp')
        else:
            self.cognito_idp = cognito_idp_client

        self.cognito_url = f"cognito-idp.{region}.amazonaws.com/{cognito_user_pool_id}"
        self.identity_pool_id = cognito_identity_pool_id
        self.user_pool_id = cognito_user_pool_id
        if not ssm_client:
            self.ssm = utils.BotoClientProvider.get_client('ssm', region) 
        else:
            self.ssm = ssm_client
        
        self.allowed_origins = self.utils.get_allowed_origins()
        print(f"Got allowed_origins: {self.allowed_origins}")

        # allowed_origins = utils.get_ssm_params('origin_frontend')
        # if not '://' in origin_domain_name:
        #     origin_domain_name = f'https://{origin_domain_name}'
        # self.frontend_origins = [   
        #     origin_domain_name
        # ]

    # def get_cognito_keys(self):
    #     if not self.cognito_keys:
    #         keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(self.region, self.user_pool_id)
    #         # instead of re-downloading the public keys every time
    #         # we download them only on cold start
    #         # https://aws.amazon.com/blogs/compute/container-reuse-in-lambda/
    #         with request.urlopen(keys_url) as f:
    #             response = f.read()
    #         self.cognito_keys = json.loads(response.decode('utf-8'))['keys']
    #     return self.cognito_keys

    # def get_creds_from_token(self, user_id, auth_token, cognito_id_client=None):
    #     print(f"get_creds_from_token got {user_id}, {auth_token}")
    #     if not cognito_id_client:
    #         cognito_id_client = self.cognito_identity
    #     creds = cognito_id_client.get_credentials_for_identity(
    #         IdentityId=user_id,
    #         Logins={
    #             f'cognito-idp.{os.getenv("AWS_REGION")}.amazonaws.com/{self.user_pool_id}': auth_token
    #         }
    #     )['Credentials']
    #     return creds

    def get_userid_from_token(self, auth_token):
        print(F"get_userid_from_token got account_id {self.account_id}, auth token:\n{auth_token}\n.")
        return self.cognito_identity.get_id(
            AccountId=self.account_id,
            IdentityPoolId=self.identity_pool_id,
            Logins = {
                self.cognito_url: auth_token
            }
        )['IdentityId']        

    def handler(self, event, context):
        print(f"CognitoAuthProvider.handler got event {event}")
        print(f"CognitoAuthProvider.handler got context {context}")
        print(f"Invoked function arn is {context[0].invoked_function_arn}")
        self.account_id = context.invoked_function_arn.split(':')[4] if hasattr(context, 'invoked_function_arn') else ''
        handler_evt = CognitoAuthProviderEvent().from_lambda_event(event)
        handler_evt.account_id = self.account_id
    
        status = 200

        if hasattr(handler_evt, 'auth_token') and handler_evt.auth_token is not None:
            handler_evt.user_id = self.get_userid_from_token(handler_evt.auth_token)

        if handler_evt.origin not in self.allowed_origins:
            status = 403
            result = 'forbidden'
            
        elif handler_evt.operation == 'get_userid_from_token':
            result = {"user_id": handler_evt.user_id}
            print(f"Got user id {result} from token")

        else: 
            result = "ERROR: Unexpected method or path sent"
            status = 400

        return self.utils.format_response(status, result, '', dont_sanitize_fields=['user_id'])
        
def handler(event, context):
    global cognito_auth_provider
    if not cognito_auth_provider:
        cognito_auth_provider = CognitoAuthProvider(
            cognito_identity_pool_id=os.getenv('IDENTITY_POOL_ID', ''),
            cognito_user_pool_id=os.getenv('USER_POOL_ID', ''),
            region=os.getenv('AWS_REGION', '')
        )
    return cognito_auth_provider.handler(event, context)


    