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
    aws_cognito as cognito,
    aws_cognito_identitypool_alpha as idp_alpha,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_ssm as ssm
)
from constructs import Construct


class CognitoStack(Stack):
    user_pool: cognito.UserPool
    user_pool_client: cognito.UserPoolClient
    user_pool_domain: cognito.UserPoolDomain

    def __init__(self, scope: Construct, construct_id: str,
        allowed_email_domains: [str], 
        cognito_domain_prefix: str, 
        ingestion_bucket: s3.IBucket,
        # ingestion_status_table: dynamodb.ITable,
        system_settings_table: dynamodb.ITable,
        verification_message_body: str,
        verification_message_subject: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.post_confirmation_trigger = lambda_.Function(self, 'PostConfirmationTrigger',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join([
                            'pip3 install -t /asset-output -r /asset-input/sharing_handler/sharing_handler_requirements.txt',
                            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider',
                            'cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider',
                            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider',
                            'cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider',
                            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/sharing_handler',
                            'cp /asset-input/sharing_handler/post_confirmation_hook.py /asset-output/multi_tenant_full_stack_rag_application/sharing_handler/',
                            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils',
                            'cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/'
                        ])
                    ]
                )
            ),
            handler='multi_tenant_full_stack_rag_application.sharing_handler.post_confirmation_hook.handler',
            runtime=lambda_.Runtime.PYTHON_3_11,
            memory_size=128,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.seconds(60),
            environment={
                # "INGESTION_STATUS_TABLE": ingestion_status_table.table_name,
                "SYSTEM_SETTINGS_TABLE": system_settings_table.table_name,
            }
        )
        # ingestion_status_table.grant_read_data(self.post_confirmation_trigger.grant_principal)
        system_settings_table.grant_read_write_data(self.post_confirmation_trigger.grant_principal)

        self.post_confirmation_trigger.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs"
            ]
        ))

        self.pre_signup_trigger = lambda_.Function(self, 'PreSignupTrigger',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
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
            runtime=lambda_.Runtime.PYTHON_3_11,
            memory_size=128,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.seconds(60),
            environment={
                "ALLOWED_EMAIL_DOMAINS": ",".join(allowed_email_domains)
            }
        )
        
        
        self.user_pool = cognito.UserPool(
            self,
            'UserPool',
            removal_policy=RemovalPolicy.DESTROY,
            user_pool_name='MultiTenantRagUserPool',
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
                post_confirmation=self.post_confirmation_trigger
            )
        )
        self.user_pool_client = cognito.UserPoolClient(self, 'UserPoolClient',
            user_pool=self.user_pool
        )

        self.user_pool_domain = cognito.UserPoolDomain(self, 'UserPoolDomain',
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"{cognito_domain_prefix}" if cognito_domain_prefix else None,
            ),
            user_pool=self.user_pool
        )

        self.identity_pool = idp_alpha.IdentityPool(self, 'CognitoIdentityPool',
            allow_unauthenticated_identities=False,
            authentication_providers= idp_alpha.IdentityPoolAuthenticationProviders(
                user_pools=[idp_alpha.UserPoolAuthenticationProvider(
                    user_pool=self.user_pool,
                    user_pool_client=self.user_pool_client
                )]
            ),
        )

        self.identity_pool.authenticated_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['execute-api:*'],
            resources=['*']
        ))

        self.identity_pool.authenticated_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                's3:DeleteObject',
                's3:GetObject',
                's3:Listbucket',
                's3:PutObject',
            ],
            resources=[
                ingestion_bucket.bucket_arn
            ],
            conditions={
                "StringLike": {
                    "s3:prefix": ["${cognito-identity.amazonaws.com:sub}/*"]
                }
            }
        ))
        
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
       
        # self.post_confirmation_trigger.add_to_role_policy(iam.PolicyStatement(
        #     effect=iam.Effect.ALLOW,
        #     actions=['ssm:GetParameter'],
        #     resources=[
        #         f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/frontendOrigin",
        #         f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs",
        #         f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
        #     ]
        # ))

        self.auth_provider_args = [
            self.account,
            self.identity_pool.identity_pool_id,
            self.user_pool.user_pool_id,
            self.region
        ]

        self.ssm_param_auth_provider_args =  ssm.StringParameter(self, "SsmParamAuthProviderArgs",
            parameter_name='/multitenantrag/authProviderArgs',
            string_value=json.dumps(self.auth_provider_args)
        )
        self.ssm_param_auth_provider_args =  ssm.StringParameter(self, "SsmParamAuthProviderPyPath",
            parameter_name='/multitenantrag/authProviderPyPath',
            string_value='multi_tenant_full_stack_rag_application.auth_provider.CognitoAuthProvider'
        )
        self.authenticated_role_arn = self.identity_pool.authenticated_role.role_arn


        CfnOutput(self, "IdentityPoolId",
            value=self.identity_pool.identity_pool_id
        )
        CfnOutput(self, "UserPoolId",
            value=self.user_pool.user_pool_id
        )
        CfnOutput(self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id
        )
        CfnOutput(self, "CognitoAuthenticatedUserRole",
            value=self.identity_pool.authenticated_role.role_arn
        )
        
    