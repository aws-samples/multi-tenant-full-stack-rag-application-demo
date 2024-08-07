#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    Stack,
    aws_ec2 as ec2,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
)
from constructs import Construct

class InitializationHandlerApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        auth_role_arn: str,
        system_settings_table: dynamodb.ITable,
        user_pool_client_id: str,
        user_pool_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'IhCognitoAuthRoleRef', auth_role_arn)

        bundling_cmds = [
            "pip3 install -t /asset-output/ -r /asset-input/initialization_handler/initialization_handler_requirements.txt",
            "pip3 install -t /asset-output/ -r /asset-input/bedrock_provider/bedrock_provider_requirements.txt",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/bedrock_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/initialization_handler",
            "cp /asset-input/initialization_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/initialization_handler",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider", 
            "cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils"
        ]

        self.initialization_handler_function = lambda_.Function(self, 'InitializationHandlerApiFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(bundling_cmds)
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.initialization_handler.initialization_handler.handler',
            timeout=Duration.seconds(60),
            environment={
                "SYSTEM_SETTINGS_TABLE": system_settings_table.table_name
            }
        )

        self.initialization_handler_function.grant_invoke(cognito_auth_role)
        system_settings_table.grant_read_write_data(self.initialization_handler_function)
        
        self.initialization_handler_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs"
            ]
        ))

        initialization_handler_integration_fn = apigwi.HttpLambdaIntegration(
            "InitializationHandlerLambdaIntegration", 
            self.initialization_handler_function,
        )

        api_name = 'initialization'

        self.http_api = apigw.HttpApi(self, "InitializationHandlerApi",
            api_name=api_name,
            create_default_stage=True
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "InitializationHandlerAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/initialization',
            methods=[
                apigw.HttpMethod.POST
            ],
            authorizer=authorizer,
            integration=initialization_handler_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=initialization_handler_integration_fn
        )

        CfnOutput(self, "InitializationHandlerHttpApiUrl", value=self.http_api.url)