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
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_cognito as cognito,
    aws_cognito_identitypool_alpha as idp_alpha,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3, 
    aws_ssm as ssm,
)
from constructs import Construct
# from lib.shared.utils_permissions import UtilsPermissions


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
        
        # TODO Move this to the sharing handler where it belongs
        # self.post_confirmation_trigger = lambda_.Function(self, 'PostConfirmationTrigger',
        #     code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
        #         bundling=BundlingOptions(
        #             image=lambda_.Runtime.PYTHON_3_11.bundling_image,
        #             bundling_file_access=BundlingFileAccess.VOLUME_COPY,
        #             command=[
        #                 "bash", "-c", " && ".join([
        #                     'pip3 install -t /asset-output -r /asset-input/sharing_handler/sharing_handler_requirements.txt',
        #                     'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider',
        #                     'cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider',
        #                     'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/sharing_handler',
        #                     'cp /asset-input/sharing_handler/post_confirmation_hook.py /asset-output/multi_tenant_full_stack_rag_application/sharing_handler/',
        #                     'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils',
        #                     'cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/'
        #                 ])
        #             ]
        #         )
        #     ),
        #     dead_letter_queue_enabled=True,
        #     handler='multi_tenant_full_stack_rag_application.sharing_handler.post_confirmation_hook.handler',
        #     runtime=lambda_.Runtime.PYTHON_3_11,
        #     memory_size=128,
        #     architecture=lambda_.Architecture.X86_64,
        #     timeout=Duration.seconds(60),
        #     environment={
        #         # "INGESTION_STATUS_TABLE": ingestion_status_table.table_name,
        #         # TODO_TEST This needs to go to a parameter so it can be decoupled at deployment time
        #         "STACK_NAME": parent_stack_name,
        #         # "SYSTEM_SETTINGS_TABLE": system_settings_table.table_name,
        #     }
        # )
        # ingestion_status_table.grant_read_data(self.post_confirmation_trigger.grant_principal)
        # TODO_IN_PROGRESS If this gets decoupled, then the permissions will need to be updated
        # by a trigger function at the end of the install.
        # system_settings_table.grant_read_write_data(self.post_confirmation_trigger.grant_principal)

        # self.post_confirmation_trigger.add_to_role_policy(iam.PolicyStatement(
        #     effect=iam.Effect.ALLOW,
        #     actions=['ssm:GetParameter','ssm:GetParametersByPath'],
        #     resources=[
        #         f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"""
        #         f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"
        #     ]
        # ))

        # the pre-signup trigger checks a user's email domain to verify that
        # it's an allowed email domain. The allowed_email_domains are configured
        # at deployment time by user-provided input (for CloudFormation) or 
        # by cdk.context.json (for CDK).
        
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

        # TODO_IN_PROGRESS this could be moved to a trigger function at the end to remove
        # the dependency on ingestion_bucket just for the arn.
        # self.identity_pool.authenticated_role.add_to_policy(iam.PolicyStatement(
        #     effect=iam.Effect.ALLOW,
        #     actions=[
        #         's3:DeleteObject',
        #         's3:GetObject',
        #         's3:Listbucket',
        #         's3:PutObject',
        #     ],
        #     resources=[
        #         ingestion_bucket.bucket_arn
        #     ],
        #     conditions={
        #         "StringLike": {
        #             "s3:prefix": ["${cognito-identity.amazonaws.com:sub}/*"]
        #         }
        #     }
        # ))

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
        
        # TODO move to sharing handler with post_confirmation_trigger function above
        # self.post_confirmation_trigger.add_to_role_policy(iam.PolicyStatement(
        #     effect=iam.Effect.ALLOW,
        #     actions=['ssm:GetParameter','ssm:GetParametersByPath'],
        #     resources=[
        #         f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"
        #         f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"
        #         f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"
        #     ]
        # ))
        self.cognito_auth_provider_function = lambda_.Function(self, 'CognitoAuthProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join([
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
                            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output/"
                        ])
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
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

        # UtilsPermissions(self, 'UtilsPermissions', self.cognito_auth_provider_function.role)
        
        auth_provider_integration_fn = apigwi.HttpLambdaIntegration(
            "AuthProviderLambdaIntegration",
            self.cognito_auth_provider_function
        )

        api_name = 'auth'

        self.http_api = apigw.HttpApi(self, 'AuthProviderHttpApi',
            api_name=api_name,
            create_default_stage=True
        )

        authorizer = apigwa.HttpIamAuthorizer()
        # authorizer = apigwa.HttpJwtAuthorizer(
        #     "AuthProviderAuthorizer",
        #     f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool.user_pool_id}",
        #     identity_source=["$request.header.Authorization"],
        #     jwt_audience=[self.user_pool_client.user_pool_client_id]
        # )

        self.http_api.add_routes(
            path='/auth/{operation}',
            methods=[
                apigw.HttpMethod.POST,
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

        auth_provider_function_name_param = ssm.StringParameter(
            self, "AuthProviderFunctionNameParam",
            parameter_name=f"/{parent_stack_name}/auth_provider_function_name",
            string_value=self.cognito_auth_provider_function.function_name
        )
        
        auth_provider_function_name_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        
        
    