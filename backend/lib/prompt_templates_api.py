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
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_notifications as s3_notif,
    aws_sqs as sqs
)
from constructs import Construct

class PromptTemplatesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        cognito_auth_role_arn: str,
        identity_pool_id: str,
        user_pool_client_id: str,
        user_pool_id: str,
        user_settings_table: ddb.ITable,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'PTCognitoAuthRole', cognito_auth_role_arn)
        self.prompt_templates_handler_function = lambda_.Function(self, 'PromptTemplatesHandlerFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join([
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
                            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
                            "cp /asset-input/bedrock_provider/bedrock_model_params.json /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
                            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates",
                            "cp /asset-input/prompt_template_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/",
                            "cp /asset-input/prompt_template_handler/prompt_templates/default*.txt /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates/",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider",
                            "cp /asset-input/user_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils"
                        ])
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.prompt_template_handler.prompt_template_handler.handler',
            timeout=Duration.seconds(60),
            environment={
                'AWS_ACCOUNT': self.account,
                'IDENTITY_POOL_ID': identity_pool_id,
                'USER_POOL_ID': user_pool_id,
                'USER_SETTINGS_TABLE': user_settings_table.table_name
            }
        )
        user_settings_table.grant_read_write_data(self.prompt_templates_handler_function.grant_principal)
    
        self.prompt_templates_handler_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/frontendOrigin",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs"
            ]
        ))
        self.prompt_templates_handler_function.grant_invoke(cognito_auth_role)

        prompt_templates_handler_integration_fn = apigwi.HttpLambdaIntegration(
            "PromptTemplatesHandlerLambdaIntegration",
            self.prompt_templates_handler_function
        )

        api_name = 'prompt_templates'

        self.http_api = apigw.HttpApi(self, 'PromptTemplatesHttpApi',
            api_name=api_name,
            create_default_stage=True
        )

        authorizer = apigwa.HttpJwtAuthorizer(
            "PromptTemplatesHandlerAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id]
        )

        self.http_api.add_routes(
            path='/prompt_templates',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.POST,
                apigw.HttpMethod.PUT,
                apigw.HttpMethod.DELETE
            ],
            authorizer=authorizer,
            integration=prompt_templates_handler_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=prompt_templates_handler_integration_fn
        )

        CfnOutput(self, "PromptTemplatesHttpApiUrl", value=self.http_api.url)