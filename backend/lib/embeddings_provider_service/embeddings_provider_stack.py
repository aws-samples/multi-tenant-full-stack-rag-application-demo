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
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)

from constructs import Construct
# from lib.shared.utils_permissions import UtilsPermissions


class EmbeddingsProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
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
            "cp /asset-input/service_provider* /asset-output/multi_tenant_full_stack_rag_application/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output",
            "pip3 install -r /asset-input/embeddings_provider/bedrock_embeddings_provider_requirements.txt -t /asset-output"
        ]

        embeddings_model_id = self.node.get_context('embeddings_model_id')
        embeddings_provider_args = self.node.get_context('embeddings_provider_args')
        embeddings_provider_py_path = self.node.get_context('embeddings_provider_py_path')
        handler_path = '.'.join(embeddings_provider_py_path.split('.')[:-1]) + '.handler'

        self.embeddings_provider_function = lambda_.Function(self, 'EmbeddingsProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=256,
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,
            handler=handler_path,
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

        if 'sagemaker' in self.node.get_context('embeddings_provider_py_path'):
            endpoint_name = self.node.get_context('embeddings_provider_args')['endpoint_name']
            self.embeddings_provider_function.add_to_role_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
				    "sagemaker:InvokeEndpointAsync",
				    "sagemaker:InvokeEndpointWithResponseStream",
    				"sagemaker:InvokeEndpoint"
                ],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{endpoint_name}"
                ]
            ))
        
        emb_provider_fn_name_param =ssm.StringParameter(self, 'EmbeddingsProviderFunctionName',
            parameter_name=f'/{parent_stack_name}/embeddings_provider_function_name',
            string_value=self.embeddings_provider_function.function_name
        )
        emb_provider_fn_name_param.apply_removal_policy(RemovalPolicy.DESTROY)

        emb_provider_origin_param = ssm.StringParameter(self, 'EmbeddingsProviderOrigin',
            parameter_name=f'/{parent_stack_name}/origin_embeddings_provider',
            string_value=self.embeddings_provider_function.function_name
        )
        emb_provider_origin_param.apply_removal_policy(RemovalPolicy.DESTROY)

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
        
        self.embeddings_provider_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction",
                ],
                resources=[auth_fn.function_arn],
            )
        )
        
        self.embeddings_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*",            
            ]
        ))

        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)
        self.embeddings_provider_function.grant_invoke(cognito_auth_role)
        



        
        


