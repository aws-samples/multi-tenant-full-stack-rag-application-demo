#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from aws_cdk import (
    CfnOutput,
    Stack,

)
from constructs import Construct

from lib.auth_provider_service.cognito import CognitoStack


class AuthProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        allowed_email_domains: [str], 
        parent_stack_name: str,
        verification_message_body: str,
        verification_message_subject: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.cognito_stack = CognitoStack(self, 'CognitoStack',
            allowed_email_domains=allowed_email_domains,
            parent_stack_name=parent_stack_name,
            verification_message_body=verification_message_body,
            verification_message_subject=verification_message_subject
        )
        
        CfnOutput(self, "CognitoIdentityPoolId",
            value=self.cognito_stack.identity_pool.identity_pool_id
        )
        CfnOutput(self, "UserPoolId",
            value=self.cognito_stack.user_pool.user_pool_id
        )
        CfnOutput(self, "UserPoolClientId",
            value=self.cognito_stack.user_pool_client.user_pool_client_id
        )
        CfnOutput(self, "CognitoAuthenticatedUserRole",
            value=self.cognito_stack.identity_pool.authenticated_role.role_arn
        )