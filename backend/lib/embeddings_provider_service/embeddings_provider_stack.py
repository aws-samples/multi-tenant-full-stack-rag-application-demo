#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os

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
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)

from constructs import Construct


class EmbeddingsProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        embeddings_model_id: str,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_id:str,
        vpc=ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        build_cmds = []
        embeddings_provider_req_paths =  [
            "embeddings_provider/bedrock_embeddings_provider_requirements.txt",
        ]
        
        for path in embeddings_provider_req_paths:
            build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
        
        # for path in vector_store_req_paths:
        #     build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        build_cmds += [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/embeddings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
        ]

        embeddings_provider_args = [
            embeddings_model_id
        ]
        
        embeddings_provider_py_path = 'multi_tenant_full_stack_rag_application_demo.embeddings_provider.bedrock_embeddings_provider.BedrockEmbeddingsProvider'
        
        self.embeddings_provider_function = lambda_.Function(self, 'EmbeddingsProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.embeddings_provider.bedrock_embeddings_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                # 'IDENTITY_POOL_ID': cognito_identity_pool_id,
                # 'USER_POOL_ID': cognito_user_pool_id,
                # 'INGESTION_BUCKET': ingestion_bucket.bucket_name,
                'EMBEDDINGS_MODEL_ID': embeddings_model_id,
                'EMBEDDINGS_PROVIDER_ARGS': json.dumps(embeddings_provider_args),
                'EMBEDDINGS_PROVIDER_PY_PATH': embeddings_provider_py_path,
                "STACK_NAME": parent_stack_name,
                # 'INGESTION_STATUS_TABLE': ingestion_status_table.table_name,
                # 'SQS_QUEUE_ARN': ingestion_queue.queue_arn,
                # 'SYSTEM_SETTINGS_TABLE': system_settings_table.table_name,
                # 'USER_SETTINGS_TABLE': user_settings_table.table_name,
                # 'VECTOR_STORE_ENDPOINT': vector_store_endpoint,
                # 'VECTOR_STORE_PROVIDER_PY_PATH': vector_store_provider_py_path
            }
        )

        self.embeddings_provider_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    # only use one of these two and comment out the other.
                    f"arn:aws:bedrock:{self.region}::foundation-model/*",
                    # f"arn:aws:bedrock:{self.region}::foundation-model/{embeddings_model_id}",
                ]
            )
        )

        self.embeddings_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}/*",            
            ]
        ))

        embeddings_provider_integration_fn = apigwi.HttpLambdaIntegration(
            "EmbeddingsProviderLambdaIntegration",
            self.embeddings_provider_function
        )

        api_name = 'embeddings_provider'

        self.http_api = apigw.HttpApi(self, 'EmbeddingsProviderHttpApi',
            api_name=api_name,
            create_default_stage=True
        )

        authorizer = apigwa.HttpJwtAuthorizer(
            "EmbeddingsProviderAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id]
        )

        self.http_api.add_routes(
            path='/embeddings_provider',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.POST,
            ],
            authorizer=authorizer,
            integration=embeddings_provider_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=embeddings_provider_integration_fn
        )

        emb_provider_url_param = ssm.StringParameter(
            self, "EmbeddingsProviderApiUrlParam",
            parameter_name=f"/{parent_stack_name}/embeddings_provider_api_url",
            string_value=self.http_api.url
        )
        emb_provider_url_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        CfnOutput(self, "EmbeddingsProviderApiUrl",
            value=self.http_api.url,
        )



        
        


