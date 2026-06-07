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
    aws_dynamodb as ddb,
    aws_ec2 as ec2,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_sqs as sqs,
    aws_ssm as ssm,
)
from constructs import Construct
from .entity_extraction_provider_function import EntityExtractionProviderFunction
from lib.shared.queue import Queue
from lib.shared.queue_to_function_event_trigger import QueueToFunctionTrigger

class EnrichmentPipelinesHandlerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        parent_stack_name: str,
        vpc=ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SQS queue for entity extraction
        self.entity_extraction_queue = Queue(self, 'EntityExtractionQueue',
            resource_name='EntityExtractionQueue',
            visibility_timeout=Duration.minutes(15)
        )

        # Create enrichment pipelines stream processor function
        build_cmds_stream_processor = [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output",
            "cp /asset-input/enrichment_pipelines_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_provider/",
            "cp /asset-input/service_provider*.py /asset-output/multi_tenant_full_stack_rag_application/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
        ]

        self.stream_processor_function = lambda_.Function(self, 'EnrichmentPipelinesStreamProcessor',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds_stream_processor)
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,
            handler='multi_tenant_full_stack_rag_application.enrichment_pipelines_provider.enrichment_pipelines_stream_processor.handler',
            timeout=Duration.seconds(300),
            environment={
                "AWS_ACCOUNT_ID": self.account,
                "SERVICE_REGION": self.region,
                "STACK_NAME": parent_stack_name,
                "ENTITY_EXTRACTION_QUEUE_URL": self.entity_extraction_queue.queue.queue_url,
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            security_groups=[app_security_group]
        )

        # Grant permissions to stream processor
        self.stream_processor_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"
            ]
        ))
        # Grant SQS permissions to stream processor
        self.entity_extraction_queue.queue.grant_send_messages(self.stream_processor_function.grant_principal)

        # Create SSM parameter for stream processor origin
        stream_processor_origin_param = ssm.StringParameter(self, 'EnrichmentPipelinesStreamProcessorOrigin',
            parameter_name=f'/{parent_stack_name}/origin_enrichment_pipelines_stream_processor',
            string_value=self.stream_processor_function.function_name
        )
        stream_processor_origin_param.apply_removal_policy(RemovalPolicy.DESTROY)

        CfnOutput(self, 'EnabledEnrichmentPipelines',
            value=json.dumps({"entity_extraction": {"name": "Entity Extraction"}})
        )

        # Create entity extraction function with queue integration
        self.entity_extraction_function = EntityExtractionProviderFunction(self, 'EntityExtractionProviderFunction',
            account=self.account,
            app_security_group=app_security_group,
            entity_extraction_queue=self.entity_extraction_queue,
            extraction_model_id=self.node.try_get_context("extraction_model_id"),
            parent_stack_name=parent_stack_name,
            region=self.region,
            vpc=vpc
        )
