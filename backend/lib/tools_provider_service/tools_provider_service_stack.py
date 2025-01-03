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
    # aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)

from constructs import Construct
# from lib.shared.utils_permissions import UtilsPermissions

class ToolsProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        # auth_role_arn: str,
        parent_stack_name: str,
        # user_pool_client_id: str,
        # user_pool_id: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.tools_provider_function = lambda_.Function(self, 'ToolsProviderFunction',
            code=lambda_.Code.from_asset_image(
                'src/multi_tenant_full_stack_rag_application/',
                file="tools_provider/Dockerfile.tools_provider"
            ),
            memory_size=256,
            runtime=lambda_.Runtime.FROM_IMAGE,
            # runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler=lambda_.Handler.FROM_IMAGE,
            # handler='multi_tenant_full_stack_rag_application.tools_provider.tools_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                'STACK_NAME': parent_stack_name,
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            security_groups=[app_security_group]
        )

        self.tools_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"
            ]
        ))

        self.tools_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'lambda:InvokeFunction',
            ],
            resources=[auth_fn.function_arn]
        ))

        stack_prefix = parent_stack_name.replace('-', '')
        self.tools_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'lambda:CreateFunction',
                'lambda:DeleteFunction',
                'lambda:InvokeFunction',
            ],
            resources=[
                f"arn:aws:lambda:{self.region}:{self.account}:function:{stack_prefix}ToolSandbox*"
            ]
        ))

        self.tools_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'iam:PassRole'
            ],
            resources=[
                self.tools_provider_function.role.role_arn
            ]
        ))

        tools_provider_function_name_param = ssm.StringParameter(self, 'ToolsProviderFunctionNameParam',
            parameter_name=f'/{parent_stack_name}/tools_provider_function_name',
            string_value=self.tools_provider_function.function_name
        )
        tools_provider_function_name_param.apply_removal_policy(RemovalPolicy.DESTROY)

        tools_provider_origin_param = ssm.StringParameter(self, 'ToolsProviderOriginParam',
            parameter_name=f'/{parent_stack_name}/origin_tools_provider',
            string_value=self.tools_provider_function.function_name
        )
        tools_provider_origin_param.apply_removal_policy(RemovalPolicy.DESTROY)
