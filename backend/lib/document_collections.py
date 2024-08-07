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
    aws_opensearchservice as aos,
    aws_s3 as s3,
    aws_s3_notifications as s3_notif,
    aws_sqs as sqs
)
from constructs import Construct

class DocumentCollectionsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        allowed_email_domains: [str],
        auth_role_arn: str,
        auth_provider_args: [str],
        auth_provider_py_path: str,
        cognito_identity_pool_id: str,
        cognito_user_pool_id: str,
        doc_collections_bucket: s3.IBucket,
        embeddings_provider_args: [str],
        embeddings_provider_extra_env: dict,
        embeddings_provider_py_path: str,
        embeddings_provider_req_paths: [str],
        ingestion_queue: sqs.IQueue,
        ingestion_status_table: ddb.ITable,
        system_settings_table: ddb.ITable,
        user_settings_table: ddb.Table,
        vector_store_domain: aos.Domain,
        vector_store_endpoint: str,
        vector_store_provider_py_path: str,
        vector_store_req_paths: [str],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)
        
        build_cmds = []

        for path in embeddings_provider_req_paths:
            build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
        
        for path in vector_store_req_paths:
            build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        build_cmds += [
            f"pip3 install -r /asset-input/bedrock_provider/bedrock_provider_requirements.txt -t /asset-output/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider/",
            "cp /asset-input/bedrock_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/bedrock_provider/bedrock_model_params.json /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider/",
            "cp /asset-input/document_collections_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler/",
            "cp /asset-input/embeddings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider/",
            "cp /asset-input/ingestion_status_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider/",
            "cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider/",
            "cp /asset-input/user_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            "cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider/",
        ]

        self.doc_collections_function = lambda_.Function(self, 'DocCollectionsApiFunction',
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
            handler='multi_tenant_full_stack_rag_application.document_collections_handler.document_collections_handler.handler',
            timeout=Duration.seconds(60),
            environment={
                **embeddings_provider_extra_env,
                'ALLOWED_EMAIL_DOMAINS': ','.join(allowed_email_domains),
                'IDENTITY_POOL_ID': cognito_identity_pool_id,
                'USER_POOL_ID': cognito_user_pool_id,
                'DOC_COLLECTIONS_BUCKET': doc_collections_bucket.bucket_name,
                'EMBEDDINGS_PROVIDER_ARGS': json.dumps(embeddings_provider_args),
                'EMBEDDINGS_PROVIDER_PY_PATH': embeddings_provider_py_path,
                'INGESTION_STATUS_TABLE': ingestion_status_table.table_name,
                'SQS_QUEUE_ARN': ingestion_queue.queue_arn,
                'SYSTEM_SETTINGS_TABLE': system_settings_table.table_name,
                'USER_SETTINGS_TABLE': user_settings_table.table_name,
                'VECTOR_STORE_ENDPOINT': vector_store_endpoint,
                'VECTOR_STORE_PROVIDER_PY_PATH': vector_store_provider_py_path
            }
        )
        # doc collections function permissions
        system_settings_table.grant_read_data(self.doc_collections_function.grant_principal)
        user_settings_table.grant_read_write_data(self.doc_collections_function.grant_principal)
        self.doc_collections_function.grant_invoke(cognito_auth_role)
        self.doc_collections_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                's3:GetBucketNotification',
                's3:PutBucketNotification',
                's3:DeleteObject'
            ],
            resources=[
                doc_collections_bucket.bucket_arn,
                f"{doc_collections_bucket.bucket_arn}/*"
            ]
        ))
        ingestion_status_table.grant_read_write_data(self.doc_collections_function.grant_principal)
        self.doc_collections_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['cognito-identity:GetId'],
            resources=['*']
        ))

        self.doc_collections_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/frontendOrigin",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs"
            ]
        ))
        vector_store_domain.grant_index_read_write("*", self.doc_collections_function.grant_principal)
        vector_store_domain.grant_read_write(self.doc_collections_function.grant_principal)

        cognito_auth_role.attach_inline_policy(iam.Policy(self, 'CognitoAuthDocBucketPolicy',
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:DeleteObject"
                    ],
                    resources=[
                        f"{doc_collections_bucket.bucket_arn}/private/{'${cognito-identity.amazonaws.com:sub}'}/*",
                    ]
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        's3:ListBucket'
                    ],
                    resources=[
                        f"{doc_collections_bucket.bucket_arn}"
                    ],
                    conditions={
                        "StringLike": {
                            "s3:prefix": [
                                "private/${cognito-identity.amazonaws.com:sub}/",
                                "private/${cognito-identity.amazonaws.com:sub}/*"
                            ]
                        }
                    }
                )
            ]
        ))