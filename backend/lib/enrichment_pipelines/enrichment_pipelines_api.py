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
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)
from constructs import Construct

class EnrichmentPipelinesApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        auth_role_arn: str,
        enrichment_pipelines_ssm_param: ssm.StringParameter,
        user_pool_client_id: str,
        user_pool_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'GhCognitoAuthRoleRef', auth_role_arn)

        bundling_cmds = []
        # for path in req_paths:
        #     bundling_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
        # for path in embeddings_provider_req_paths:
        #     bundling_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
        # for path in vector_store_req_paths:
        #     bundling_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        bundling_cmds += [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction",
            "cp /asset-input/enrichment_pipelines/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/",
            # "cp /asset-input/enrichment_pipelines/entity_extraction/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/generation_handler",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
            # "cp /asset-input/bedrock_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            # "cp /asset-input/bedrock_provider/*.json /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            # "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider/",
            # "cp /asset-input/document_collections_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler/",
            # "cp /asset-input/embeddings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider/",
            # "cp /asset-input/enrichment_pipelines/entity_extraction/neptune_client.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction/",
            # "cp /asset-input/generation_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/generation_handler/",
            # "cp /asset-input/ingestion_status_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider/",
            # "cp /asset-input/prompt_template_handler/prompt_templates/*.txt /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates/",
            # "cp /asset-input/prompt_template_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/",
            # "cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider/",
            # "cp /asset-input/user_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider/",
            # "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            # "cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider/",
        ]

        self.enrichment_pipelines_handler = lambda_.Function(self, 'EnrichmentPipelinesApiFunction',
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
            handler='multi_tenant_full_stack_rag_application.enrichment_pipelines.enrichment_pipelines.handler',
            timeout=Duration.seconds(60),
            environment={
                'ENRICHMENT_PIPELINES_SSM_PARAM_NAME': enrichment_pipelines_ssm_param.parameter_name
            }
        )
        self.enrichment_pipelines_handler.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/enabled_enrichment_pipelines",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/frontendOrigin",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
            ]
        ))

        self.enrichment_pipelines_handler.grant_invoke(cognito_auth_role)

        enrichment_pipelines_integration_fn = apigwi.HttpLambdaIntegration(
            "EnrichmentPipelinesambdaIntegration", 
            self.enrichment_pipelines_handler,
        )

        api_name = 'enrichment_pipelines'

        self.http_api = apigw.HttpApi(self, "EnrichmentPipelinesHandlerApi",
            api_name=api_name,
            create_default_stage=True
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "EnrichmentPipelinesAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/enrichment_pipelines',
            methods=[
                apigw.HttpMethod.GET
            ],
            authorizer=authorizer,
            integration=enrichment_pipelines_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=enrichment_pipelines_integration_fn
        )

        CfnOutput(self, "EnrichmentPipelinesHttpApiUrl", value=self.http_api.url)