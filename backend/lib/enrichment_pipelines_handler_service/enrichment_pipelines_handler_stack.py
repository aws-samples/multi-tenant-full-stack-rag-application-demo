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
    aws_ec2 as ec2,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)
from constructs import Construct
from .entity_extraction_provider_function import EntityExtractionProviderFunction

class EnrichmentPipelinesHandlerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_role_arn: str,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_id: str,
        vpc=ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)

        bundling_cmds = []

        bundling_cmds += [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_handler/entity_extraction",
            "cp /asset-input/enrichment_pipelines_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_handler/",
            # "cp /asset-input/enrichment_pipelines_handler/entity_extraction/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_handler/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/"
        ]

        self.enrichment_pipelines_handler = lambda_.Function(self, 'EnrichmentPipelinesHandlerFunction',
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
            handler='multi_tenant_full_stack_rag_application.enrichment_pipelines_handler.enrichment_pipelines_handler.handler',
            timeout=Duration.seconds(60),
            environment={
                "STACK_NAME": parent_stack_name,
            }
        )
        self.enrichment_pipelines_handler.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}/*"
            ]
        ))

        self.enrichment_pipelines_handler.grant_invoke(cognito_auth_role)

        enrichment_pipelines_integration_fn = apigwi.HttpLambdaIntegration(
            "EnrichmentPipelinesLambdaIntegration", 
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
                apigw.HttpMethod.GET,
                apigw.HttpMethod.POST,
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
        
        ep_url_param = ssm.StringParameter(self, 'EnrichmentPipelinesHttpApiUrlParam',
            parameter_name=f'/{parent_stack_name}/enrichment_pipelines_handler_api_url',
            string_value=self.http_api.url
        )
        ep_url_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        CfnOutput(self, "EnrichmentPipelinesHttpApiUrl", value=self.http_api.url)

        entity_extraction_stack = EntityExtractionProviderFunction(self, 'EntityExtractionProviderFunction',
            account=self.account,
            app_security_group=app_security_group,
            extraction_model_id=self.node.try_get_context("extraction_model_id"),
            parent_stack_name=self.stack_name,
            region=self.region,
            vpc=vpc
        )

        ssm.StringParameter(self, 'EntityExtractionProviderFunctionName',
            parameter_name=f'/{parent_stack_name}/enrichment_pipelines/entity_extraction_provider_function_name',
            string_value=entity_extraction_stack.entity_extraction_function.function_name
        )
        