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
# from lib.shared.utils_permissions import UtilsPermissions

class EnrichmentPipelinesHandlerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_id: str,
        vpc=ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        enabled_pipelines = json.dumps({
            "entity_extraction": {
                "name": "Entity Extraction"
            }
        })

        eps_enabled_param = ssm.StringParameter(self, 'EnabledEnrichmentPipelinesParam',
            parameter_name=f'/{parent_stack_name}/enabled_enrichment_pipelines',
            string_value=enabled_pipelines
        )

        eps_enabled_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        CfnOutput(self, "EnabledEnrichmentPipelines", value=enabled_pipelines)

        self.entity_extraction_function = EntityExtractionProviderFunction(self, 'EntityExtractionProviderFunction',
            account=self.account,
            app_security_group=app_security_group,
            extraction_model_id=self.node.try_get_context("extraction_model_id"),
            parent_stack_name=self.stack_name,
            region=self.region,
            vpc=vpc
        )
