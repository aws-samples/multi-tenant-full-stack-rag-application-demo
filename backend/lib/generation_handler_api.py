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
    aws_neptune_alpha as neptune,
)
from constructs import Construct

class GenerationHandlerApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        allowed_email_domains: [str],
        auth_provider_py_path: str,
        auth_role_arn: str,
        cognito_identity_pool_id: str,
        cognito_user_pool_id: str,
        embeddings_provider_args: [str],
        embeddings_provider_extra_env: dict,
        embeddings_provider_py_path: str,
        embeddings_provider_req_paths: [str],
        inference_role: iam.IRole,
        ingestion_status_table: dynamodb.ITable,
        neptune_endpoint: str,
        system_settings_table: dynamodb.ITable,
        user_settings_table: dynamodb.ITable,
        req_paths: [str],
        user_pool_client_id: str,
        user_pool_id: str,
        vector_store_endpoint: str,
        vector_store_provider_py_path,
        vector_store_req_paths,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'GhCognitoAuthRoleRef', auth_role_arn)

        bundling_cmds = []
        for path in req_paths:
            bundling_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
        for path in embeddings_provider_req_paths:
            bundling_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
        for path in vector_store_req_paths:
            bundling_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        bundling_cmds += [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/generation_handler",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "cp /asset-input/bedrock_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/bedrock_provider/*.json /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider/",
            "cp /asset-input/document_collections_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler/",
            "cp /asset-input/embeddings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider/",
            "cp /asset-input/enrichment_pipelines/entity_extraction/neptune_client.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction/",
            "cp /asset-input/generation_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/generation_handler/",
            "cp /asset-input/ingestion_status_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider/",
            "cp /asset-input/prompt_template_handler/prompt_templates/*.txt /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates/",
            "cp /asset-input/prompt_template_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/",
            "cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider/",
            "cp /asset-input/user_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            "cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider/",
        ]

        self.generation_handler_function = lambda_.Function(self, 'GenerationHandlerApiFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(bundling_cmds)
                    ]
                )
            ),
            memory_size=768,
            role=inference_role,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.generation_handler.generation_handler.handler',
            timeout=Duration.seconds(120),
            # insights_version=lambda_.LambdaInsightsVersion.VERSION_1_0_229_0,
            environment={
                'ALLOWED_EMAIL_DOMAINS': ",".join(allowed_email_domains),
                'EMBEDDINGS_PROVIDER_ARGS': json.dumps(embeddings_provider_args),
                'EMBEDDINGS_PROVIDER_PY_PATH': embeddings_provider_py_path,
                'INGESTION_STATUS_TABLE': ingestion_status_table.table_name,
                'NEPTUNE_ENDPOINT': neptune_endpoint,
                'SERVICE_REGION': self.region,
                'SYSTEM_SETTINGS_TABLE': system_settings_table.table_name,
                'USER_SETTINGS_TABLE': user_settings_table.table_name,
                'VECTOR_STORE_ENDPOINT': vector_store_endpoint,
                'VECTOR_STORE_PROVIDER_PY_PATH': vector_store_provider_py_path,
                **embeddings_provider_extra_env
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            )
        )
        system_settings_table.grant_read_data(self.generation_handler_function.grant_principal)
        self.generation_handler_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/frontendOrigin",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs"
            ]
        ))

        self.generation_handler_function.grant_invoke(cognito_auth_role)
        user_settings_table.grant_read_data(self.generation_handler_function.grant_principal)
        self.generation_handler_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:*"],
            resources=["*"]
        ))

        generation_handler_integration_fn = apigwi.HttpLambdaIntegration(
            "GenerationHandlerLambdaIntegration", 
            self.generation_handler_function,
        )

        api_name = 'generation'

        self.http_api = apigw.HttpApi(self, "GenerationHandlerApi",
            api_name=api_name,
            create_default_stage=True,
            # cors_preflight=apigw.CorsPreflightOptions(
            #     allow_origins=["*"],
            #     allow_methods=[apigw.CorsHttpMethod.ANY]
            # )
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "GenerationHandlerAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/generation',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.POST
            ],
            authorizer=authorizer,
            integration=generation_handler_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=generation_handler_integration_fn
        )

        CfnOutput(self, "GenerationHandlerHttpApiUrl", value=self.http_api.url)