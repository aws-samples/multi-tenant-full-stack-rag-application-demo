#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
    NestedStack,
    aws_cognito as cognito,
    aws_cognito_identitypool_alpha as idp_alpha,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)
from constructs import Construct


class CognitoStack(NestedStack):
    def __init__(self, scope: Construct, construct_id: str,
        allowed_email_domains: [str], 
        app_security_group: ec2.ISecurityGroup,
        parent_stack_name: str,
        verification_message_body: str,
        verification_message_subject: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.pre_signup_trigger = lambda_.Function(self, 'PreSignupTrigger',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join([
                            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider',
                            'cp /asset-input/auth_provider/cognito_pre_signup_trigger.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider/',
                        ])
                    ]
                )
            ),
            handler='multi_tenant_full_stack_rag_application.auth_provider.cognito_pre_signup_trigger.handler',
            runtime=lambda_.Runtime.PYTHON_3_13,
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            timeout=Duration.seconds(60),
            environment={
                "ALLOWED_EMAIL_DOMAINS": ",".join(allowed_email_domains),
                "STACK_NAME": parent_stack_name
            },
            dead_letter_queue_enabled=True
        )
        
        removal_policy_str = self.node.get_context('removal_policy')
        if removal_policy_str:
            removal_policy = RemovalPolicy(removal_policy_str.upper())
        
        self.user_pool = cognito.UserPool(
            self,
            'UserPool',
            removal_policy=removal_policy,
            user_pool_name=f'{parent_stack_name}UserPool',
            self_sign_up_enabled=True,
            user_verification=cognito.UserVerificationConfig(
                email_subject=verification_message_subject,
                email_body=verification_message_body,
                email_style=cognito.VerificationEmailStyle.CODE,
                sms_message=verification_message_body
            ),
            auto_verify={
                'email': True
            },
            sign_in_aliases={
                'email': True
            },
            password_policy={
                'require_digits': True,
                'require_lowercase': True,
                'require_symbols': True,
                'require_uppercase': True,
                'min_length': 8
            },
            lambda_triggers=cognito.UserPoolTriggers(
                pre_sign_up=self.pre_signup_trigger,
                # post_confirmation=self.post_confirmation_trigger
            )
        )
        
        # Create Cognito User Pool Groups
        self.admins_group = cognito.UserPoolGroup(
            self,
            'AdminsGroup',
            user_pool=self.user_pool,
            group_name='Admins',
            description='Administrators group with full access'
        )
        
        self.agent_admins_group = cognito.UserPoolGroup(
            self,
            'AgentAdminsGroup',
            user_pool=self.user_pool,
            group_name='AgentAdmins',
            description='Agent administrators group'
        )
        
        self.mcp_admins_group = cognito.UserPoolGroup(
            self,
            'MCPAdminsGroup',
            user_pool=self.user_pool,
            group_name='MCPAdmins',
            description='MCP administrators group'
        )
        
        self.user_pool_client = cognito.UserPoolClient(self, 'UserPoolClient',
            user_pool=self.user_pool
        )
        self.cognito_domain_name = f"{parent_stack_name.lower()}-{self.account}-{self.region}"
        self.user_pool_domain = cognito.UserPoolDomain(self, 'UserPoolDomain',
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=self.cognito_domain_name,
            ),
            user_pool=self.user_pool
        )
        
        user_pool_id_param = ssm.StringParameter(self, 'CognitoUserPoolId',
            parameter_name=f'/{parent_stack_name}/user_pool_id',
            string_value=self.user_pool.user_pool_id
        )
        user_pool_id_param.apply_removal_policy(RemovalPolicy.DESTROY)

        self.identity_pool = idp_alpha.IdentityPool(self, 'CognitoIdentityPool',
            allow_unauthenticated_identities=False,
            authentication_providers= idp_alpha.IdentityPoolAuthenticationProviders(
                user_pools=[idp_alpha.UserPoolAuthenticationProvider(
                    user_pool=self.user_pool,
                    user_pool_client=self.user_pool_client
                )]
            ),
        )

        id_pool_id_param = ssm.StringParameter(self, 'CognitoIdentityPoolId',
            parameter_name=f'/{parent_stack_name}/identity_pool_id',
            string_value=self.identity_pool.identity_pool_id
        )

        id_pool_id_param.apply_removal_policy(RemovalPolicy.DESTROY)

        self.identity_pool.authenticated_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['execute-api:*'],
            resources=['*']
        ))

        #TODO Move this to OpenSearch stack.
        self.dashboard_role = iam.Role(self, 'CognitoOpenSearchDashboardRole',
            description='Default role for OpenSearch Dashboard users',
            assumed_by=iam.FederatedPrincipal(
                'cognito-identity.amazonaws.com',
                {
                'StringEquals': {
                    'cognito-identity.amazonaws.com:aud': self.identity_pool.identity_pool_id,
                },
                'ForAnyValue:StringLike': {
                    'cognito-identity.amazonaws.com:amr': 'authenticated',
                },
                },
                'sts:AssumeRoleWithWebIdentity',
            )
        )
        self.dashboard_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "cognito-identity:GetCredentialsForIdentity",
                "es:*",
            ],
            resources=["*"]
            
        ))
        
        self.cognito_auth_provider_function = lambda_.Function(self, 'CognitoAuthProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join([
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
                            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
                            'pip3 install -r /asset-input/auth_provider/cognito_auth_requirements.txt -t /asset-output',
                            "cp /asset-input/service_provider*.py /asset-output/multi_tenant_full_stack_rag_application",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output/"
                        ])
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,
            handler='multi_tenant_full_stack_rag_application.auth_provider.cognito_auth_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                'AWS_ACCOUNT_ID': self.account,
                'IDENTITY_POOL_ID': self.identity_pool.identity_pool_id,
                'STACK_NAME': parent_stack_name,
                'USER_POOL_ID': self.user_pool.user_pool_id
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[app_security_group],
            dead_letter_queue_enabled=True
        )
        
        self.authenticated_role = self.identity_pool.authenticated_role
        self.authenticated_role_arn = self.authenticated_role.role_arn

        self.cognito_auth_provider_function.grant_invoke(self.authenticated_role)

        self.cognito_auth_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*",            
            ]
        ))

        auth_provider_function_name_param = ssm.StringParameter(
            self, "AuthProviderFunctionNameParam",
            parameter_name=f"/{parent_stack_name}/auth_provider_function_name",
            string_value=self.cognito_auth_provider_function.function_name
        )
        
        auth_provider_function_name_param.apply_removal_policy(RemovalPolicy.DESTROY)
