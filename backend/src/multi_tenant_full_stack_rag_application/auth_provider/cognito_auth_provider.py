#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
from .auth_provider import AuthProvider

class CognitoAuthProvider(AuthProvider):
    def __init__(self, account_id: str, cognito_identity_pool_id: str,
        cognito_user_pool_id: str, region: str):
        self.account_id = account_id
        self.cognito = boto3.client('cognito-identity', region)
        self.cognito_url = f"cognito-idp.{region}.amazonaws.com/{cognito_user_pool_id}"
        self.identity_pool_id = cognito_identity_pool_id
        self.user_pool_id = cognito_user_pool_id

    def get_userid_from_token(self, auth_token):
        return self.cognito.get_id(
            AccountId=self.account_id,
            IdentityPoolId=self.identity_pool_id,
            Logins = {
                self.cognito_url: auth_token
            }
        )['IdentityId']