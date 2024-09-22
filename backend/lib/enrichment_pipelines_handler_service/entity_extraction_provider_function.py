#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_dynamodb as ddb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_evts,
    aws_ssm as ssm
)
from constructs import Construct
# from lib.shared.utils_permissions import UtilsPermissions


class EntityExtractionProviderFunction(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        account: str,
        app_security_group: ec2.ISecurityGroup,
        extraction_model_id: str,
        parent_stack_name: str,
        region: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # TODO_IN_PROGRESS replace this with a ddb stream
        # self.evt_source = lambda_evts.KinesisEventSource(ingestion_table_stream,
        #     starting_position=lambda_.StartingPosition.TRIM_HORIZON,
        #     batch_size=1
        # )

        build_cmds = []

        # for path in req_paths:
        #     build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        # for path in embeddings_provider_requirements_paths:
        #     build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
            
        # for path in vector_store_requirements_paths:
        #     build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        build_cmds += [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_handler/entity_extraction",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/enrichment_pipelines_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_handler",
            "cp /asset-input/enrichment_pipelines_handler/entity_extraction/*.py /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_handler/entity_extraction/",
            "cp /asset-input/enrichment_pipelines_handler/entity_extraction/*.txt /asset-output/multi_tenant_full_stack_rag_application/enrichment_pipelines_handler/entity_extraction/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output"
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
            handler='multi_tenant_full_stack_rag_application.enrichment_pipelines_handler.entity_extraction.handler',
            timeout=Duration.seconds(900),
            environment={
                "EXTRACTION_MODEL_ID": extraction_model_id,
                'SERVICE_REGION': region,
                "STACK_NAME": parent_stack_name,
            },
            # TODO_IN_PROGRESS replace this with a ddb stream
            # events=[self.evt_source],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            security_groups=[app_security_group]
        )

        # ent_extraction_origin_param = ssm.StringParameter(self, 'EntityExtractionProviderOrigin',
        #     parameter_name=f'/{parent_stack_name}/origin_entity_extraction',
        #     string_value=self.entity_extraction_function.function_name
        # )
        # ent_extraction_origin_param.apply_removal_policy(RemovalPolicy.DESTROY)

        self.entity_extraction_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{region}:{account}:parameter/{parent_stack_name}*"
            ]
        ))
        # UtilsPermissions(self, 'UtilsPermissions', self.entity_extraction_function.role)


        
