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
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_kinesis as kinesis,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_evts,
    aws_s3 as s3,
    aws_s3_notifications as s3_notif,
    aws_sqs as sqs,
    aws_ssm as ssm
)
from constructs import Construct


class EntityExtractionPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        embeddings_provider_args: [str],
        embeddings_provider_extra_env: dict,
        embeddings_provider_iam_permissions: [dict],
        embeddings_provider_py_path: str,
        embeddings_provider_requirements_paths: [str],     
        extraction_model_id: str,
        ingestion_role: iam.IRole,
        ingestion_table: ddb.ITable,
        ingestion_table_stream: kinesis.IStream,
        neptune_endpoint: str,
        req_paths: [str],
        system_settings_table: ddb.ITable,
        user_settings_table: ddb.ITable,
        vector_store_endpoint: str,
        vector_store_provider_py_path: str,
        vector_store_requirements_paths: [str],
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.evt_source = lambda_evts.KinesisEventSource(ingestion_table_stream,
            starting_position=lambda_.StartingPosition.TRIM_HORIZON,
            batch_size=1
        )

        build_cmds = []

        for path in req_paths:
            build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        for path in embeddings_provider_requirements_paths:
            build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
            
        for path in vector_store_requirements_paths:
            build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        build_cmds += [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "cp /asset-input/bedrock_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/bedrock_provider/bedrock_model_params.json /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/",
            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider/",
            "cp /asset-input/document_collections_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler",
            "cp /asset-input/embeddings_provider/*.py  /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider", 
            "cp /asset-input/embeddings_provider/*.txt  /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider", 
            "cp /asset-input/enrichment_pipelines/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines",
            "cp /asset-input/enrichment_pipelines/entity_extraction/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction/",
            "cp /asset-input/enrichment_pipelines/entity_extraction/*.txt /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines/entity_extraction/",
            "cp /asset-input/ingestion_status_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider",
            "cp /asset-input/prompt_template_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/",
            "cp /asset-input/prompt_template_handler/prompt_templates/*.txt /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates/",
            "cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            "cp /asset-input/user_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            "cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider"
        ]

        self.entity_extraction_function = lambda_.Function(self, 'EntityExtractionFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=1024,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.enrichment_pipelines.entity_extraction.handler',
            timeout=Duration.seconds(900),
            environment={
                **embeddings_provider_extra_env,
                "EMBEDDINGS_PROVIDER_ARGS": json.dumps(embeddings_provider_args),
                "EMBEDDINGS_PROVIDER_PY_PATH": embeddings_provider_py_path,
                "EXTRACTION_MODEL_ID": extraction_model_id,
                "HUGGINGFACE_HUB_CACHE": "/tmp",
                "TRANSFORMERS_CACHE": '/tmp',
                'NEPTUNE_ENDPOINT': neptune_endpoint,
                'INGESTION_STATUS_TABLE': ingestion_table.table_name,
                'SERVICE_REGION': self.region,
                'SYSTEM_SETTINGS_TABLE': system_settings_table.table_name,
                'USER_SETTINGS_TABLE': user_settings_table.table_name,
                "VECTOR_STORE_ENDPOINT": vector_store_endpoint,
                "VECTOR_STORE_PROVIDER_PY_PATH": vector_store_provider_py_path
            },
            events=[self.evt_source],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            role=ingestion_role,
            security_groups=[app_security_group]
        )

        ingestion_table.grant_read_write_data(self.entity_extraction_function.grant_principal)
        ingestion_table_stream.grant_read(self.entity_extraction_function.grant_principal)
        system_settings_table.grant_read_data(self.entity_extraction_function.grant_principal)
        user_settings_table.grant_read_data(self.entity_extraction_function.grant_principal)

        self.entity_extraction_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/frontendOrigin",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs"
            ]
        ))

        # self.entity_extraction_function.add_managed_policy(
        #     iam.ManagedPolicy.from_managed_policy_arn(
        #         self, 
        #         'EntityExtractionFunctionVpcPolicy',
        #         'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole'
        #     )
        # )

        for perm in embeddings_provider_iam_permissions:
            self.entity_extraction_function.add_to_role_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=perm['actions'],
                resources=perm['resources']
            ))
