#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    Stack,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)
from constructs import Construct

from lib.auth_provider_service.cognito import CognitoStack


class EmbeddingsProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        embeddings_model_id: str,
        parent_stack_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        build_cmds = []
        embeddings_provider_req_paths =  [
            "embeddings_provider/bedrock_embeddings_provider_requirements.txt",
            "bedrock_provider/bedrock_provider_requirements.txt"
        ]
        
        for path in embeddings_provider_req_paths:
            build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
        
        # for path in vector_store_req_paths:
        #     build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        build_cmds += [
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            # "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
            # "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider/",
            # "cp /asset-input/bedrock_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/bedrock_provider/bedrock_model_params.json /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider/",
            # "cp /asset-input/document_collections_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler/",
            "cp /asset-input/embeddings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider/",
            # "cp /asset-input/ingestion_status_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider/",
            # "cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider/",
            # "cp /asset-input/user_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            # "cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider/",
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
                # 'DOC_COLLECTIONS_BUCKET': doc_collections_bucket.bucket_name,
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
                resources=[f"arn:aws:bedrock:{self.region}::foundation-model/{embeddings_model_id}"]
            )
        )

        ssm.StringParameter(
            self, "EmbeddingsProviderFunctionArnSsmParameter",
            parameter_name=f"/{parent_stack_name}/embeddings_provider_lambda_arn",
            string_value=self.embeddings_provider_function.function_arn
        )
        


