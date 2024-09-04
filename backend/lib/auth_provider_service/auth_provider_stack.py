#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
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
            parent_stack_name=parent_stack_name,
            verification_message_body=verification_message_body,
            verification_message_subject=verification_message_subject
        )
        
        build_cmds = [
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider',
            "cp -r /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils/',
            "cp -r /asset-input/utils/* /asset-output/multi_tenant_full_stack_rag_application/utils/",
        ]

        self.auth_provider_function = lambda_.Function(
            self, 'AuthProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.auth_provider.cognito_auth_provider.handler',
            timeout=Duration.seconds(30),
            environment={},
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            security_groups=[app_security_group]
        )

        self.auth_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}/*"
            ]
        ))

        self.auth_provider_function.grant_invoke(self.cognito_stack.identity_pool.authenticated_role)

        auth_provider_integration_fn = apigwi.HttpLambdaIntegration(
            "AuthProviderLambdaIntegration",
            self.auth_provider_function
        )

        api_name = 'auth_provider'

        self.http_api = apigw.HttpApi(self, 'AuthProviderHttpApi',
            api_name=api_name,
            create_default_stage=True
        )

        authorizer = apigwa.HttpJwtAuthorizer(
            "AuthProviderAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{self.cognito_stack.user_pool.user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[self.cognito_stack.user_pool_client.user_pool_client_id]
        )

        self.http_api.add_routes(
            path='/auth_provider',
            methods=[
                apigw.HttpMethod.GET
            ],
            authorizer=authorizer,
            integration=auth_provider_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=auth_provider_integration_fn
        )

        auth_provider_api_url_param = ssm.StringParameter(
            self, "AuthProviderApiUrlParam",
            parameter_name=f"/{parent_stack_name}/auth_provider_api_url",
            string_value=self.http_api.url
        )
        auth_provider_api_url_param.apply_removal_policy(RemovalPolicy.DESTROY)

        CfnOutput(self, "AuthProviderApiUrl",
            value=self.http_api.url,
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
