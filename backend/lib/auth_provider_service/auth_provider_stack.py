#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_dynamodb as ddb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_evts,
    aws_ssm as ssm,
)

from constructs import Construct

from lib.auth_provider_service.cognito import CognitoStack

 
class AuthProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        allowed_email_domains: [str], 
        app_security_group: ec2.ISecurityGroup,
        parent_stack_name: str,
        verification_message_body: str,
        verification_message_subject: str,
        vpc=ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.cognito_stack = CognitoStack(self, 'CognitoStack',
            allowed_email_domains=allowed_email_domains,
            app_security_group=app_security_group,
            parent_stack_name=parent_stack_name,
            verification_message_body=verification_message_body,
            verification_message_subject=verification_message_subject,
            vpc=vpc,
            **kwargs,
        )
        
        CfnOutput(self, "AuthProviderFunctionName",
            value=self.cognito_stack.cognito_auth_provider_function.function_name
        )

        CfnOutput(self, "IdentityPoolId",
            value=self.cognito_stack.identity_pool.identity_pool_id
        )

        CfnOutput(self, "UserPoolId",
            value=self.cognito_stack.user_pool.user_pool_id
        )

        CfnOutput(self, "UserPoolClientId",
            value=self.cognito_stack.user_pool_client.user_pool_client_id
        )
        
