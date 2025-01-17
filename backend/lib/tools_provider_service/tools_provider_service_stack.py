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
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    # aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_ssm as ssm,
)

from constructs import Construct
from .code_sandbox_host import CodeSandboxHost

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


        self.code_sandbox_host = CodeSandboxHost(self, 'CodeSandboxHost',
            app_security_group=app_security_group,
            parent_stack_name=parent_stack_name,
            vpc=vpc
        )

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

        # Create Task Execution Role
        # task_execution_role = iam.Role(self, "CodeSandboxTaskExecutionRole",
        #     assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        #     managed_policies=[
        #         iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
        #     ]
        # )

        # # Create Task Definition
        # task_definition = ecs.FargateTaskDefinition(self, "CodeSandboxTaskDefinition",
        #     memory_limit_mib=512,
        #     cpu=256,
        #     task_role=task_execution_role,
        #     execution_role=task_execution_role
        # )

        # # Add Container to Task Definition
        # task_definition.add_container("SandboxContainer",
        #     image=ecs.ContainerImage.from_asset(
        #         'src/multi_tenant_full_stack_rag_application/',
        #         file="tools_provider/Dockerfile.code_sandbox_tool_v2"
        #     ),  # Path to local Dockerfile directory
        #     port_mappings=[ecs.PortMapping(container_port=80)],
        #     logging=ecs.LogDriver.aws_logs(
        #         stream_prefix="code-sandbox-logs",
        #         log_group=logs.LogGroup(self, "CodeSandboxContainerLogGroup",
        #             log_group_name="/ecs/code-sandbox-logs",
        #             removal_policy=RemovalPolicy.DESTROY
        #         )
        #     )
        # )

        # # Create Fargate Service
        # ecs.FargateService(self, "CodeSandboxFargateService",
        #     cluster=code_sandbox_cluster,
        #     task_definition=task_definition,
        #     desired_count=2,
        #     assign_public_ip=False,
        #     service_name="code-sandbox-service",
        #     platform_version=ecs.FargatePlatformVersion.LATEST
        # )