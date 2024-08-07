#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    Duration,
    Size,
    Stack,
    aws_dynamodb as ddb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,  
)

from constructs import Construct

class VectorIngestionStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        allowed_email_domains: [str],
        app_security_group: ec2.ISecurityGroup,
        auth_provider_args: [str],
        cognito_identity_pool_id: str,
        cognito_user_pool_id: str,
        document_collections_bucket: s3.IBucket,
        embeddings_provider_args: [str],
        embeddings_provider_extra_env: dict,
        embeddings_provider_iam_permissions: [dict],
        embeddings_provider_py_path: str,
        embeddings_provider_requirements_paths: [str],
        # ingestion_handler_build_paths: [str],
        # ingestion_handler_extra_env: dict,
        # ingestion_handler_py_path: str,
        # ingestion_handler_requirements_paths: [str],
        ingestion_role: iam.IRole,
        ingestion_status_table: ddb.ITable,
        ocr_model_id: str,
        system_settings_table: ddb.ITable,
        user_settings_table: ddb.ITable,
        vector_store_endpoint: str,
        vector_store_provider_py_path: str,
        vector_store_requirements_paths: str,
        vpc: ec2.IVpc,
        **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.ingestion_function = lambda_.Function(self, 'VectorIngestionFunction',
            code=lambda_.Code.from_asset_image(
                'src/multi_tenant_full_stack_rag_application', 
                file="vector_store_provider/Dockerfile.vector_ingestion_handler",
                build_args={
                    "emb_provider_reqs": ' '.join(embeddings_provider_requirements_paths),
                    "vector_store_reqs": ' '.join(vector_store_requirements_paths)
                }
            ),
            memory_size=4096,
            ephemeral_storage_size=Size.gibibytes(10),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            runtime=lambda_.Runtime.FROM_IMAGE,
            handler=lambda_.Handler.FROM_IMAGE,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(15),
            role=ingestion_role,
            security_groups=[app_security_group],
            environment={ 
                **embeddings_provider_extra_env,
                "ALLOWED_EMAIL_DOMAINS": ",".join(allowed_email_domains),
                "HUGGINGFACE_HUB_CACHE": "/tmp",
                "TRANSFORMERS_CACHE": '/tmp',
                "IDENTITY_POOL_ID": cognito_identity_pool_id,
                "USER_POOL_ID": cognito_user_pool_id,
                "EMBEDDINGS_PROVIDER_ARGS": json.dumps(embeddings_provider_args),
                "EMBEDDINGS_PROVIDER_PY_PATH": embeddings_provider_py_path,
                "INGESTION_STATUS_TABLE": ingestion_status_table.table_name,
                "OCR_MODEL_ID": ocr_model_id,
                "PATH": "$PATH:/var/task/bin",
                "SYSTEM_SETTINGS_TABLE": system_settings_table.table_name,
                "USER_SETTINGS_TABLE": user_settings_table.table_name,
                "VECTOR_STORE_ENDPOINT": vector_store_endpoint,
                "VECTOR_STORE_PROVIDER_PY_PATH": vector_store_provider_py_path,
            }
        )
        system_settings_table.grant_read_data(self.ingestion_function.grant_principal)
        document_collections_bucket.grant_read(self.ingestion_function.grant_principal)
        ingestion_status_table.grant_read_write_data(self.ingestion_function.grant_principal)
        user_settings_table.grant_read_write_data(self.ingestion_function.grant_principal)

        self.ingestion_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/frontendOrigin",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs"
            ]
        ))
        
        self.ingestion_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['bedrock:InvokeModel'],
            resources=["arn:aws:bedrock:*::foundation-model/*"]
        ))

        for perm in embeddings_provider_iam_permissions:
            self.ingestion_function.add_to_role_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=perm['actions'],
                resources=perm['resources']
            ))