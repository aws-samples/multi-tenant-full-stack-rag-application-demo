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
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_neptune_alpha as neptune,
    aws_s3 as s3,
    aws_ssm as ssm,
)
from constructs import Construct
# from lib.shared.utils_permissions import UtilsPermissions

class GenerationHandlerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
        graph_handler_fn_arn: str,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_id: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'GhCognitoAuthRoleRef', auth_role_arn)

        bundling_cmds = [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/generation_handler",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/generation_handler/*.{py,txt} /asset-output/multi_tenant_full_stack_rag_application/generation_handler/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            "pip3 install -r /asset-input/generation_handler/generation_handler_requirements.txt -t /asset-output",
            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output"
        ]

        self.generation_handler_function = lambda_.Function(self, 'GenerationHandlerFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(bundling_cmds)
                    ]
                )
            ),
            memory_size=768,
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,
            handler='multi_tenant_full_stack_rag_application.generation_handler.generation_handler.handler',
            timeout=Duration.seconds(120),
            environment={
                'STACK_NAME': parent_stack_name,
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            security_groups=[app_security_group]
        )

        self.generation_handler_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"
            ]
        ))

        self.generation_handler_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['lambda:InvokeFunction'],
            resources=[
                auth_fn.function_arn,
                graph_handler_fn_arn,
            ]
        ))

        self.generation_handler_function.grant_invoke(cognito_auth_role)

        generation_handler_integration_fn = apigwi.HttpLambdaIntegration(
            "GenerationHandlerLambdaIntegration", 
            self.generation_handler_function,
        )

        api_name = 'generation'

        self.http_api = apigw.HttpApi(self, "GenerationHandlerApi",
            api_name=api_name,
            create_default_stage=True
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "GenerationHandlerAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/generation',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.POST
            ],
            authorizer=authorizer,
            integration=generation_handler_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=generation_handler_integration_fn
        )

        CfnOutput(self, "GenerationHandlerHttpApiUrl", value=self.http_api.url.rstrip('/'))
        
        gen_handler_api_url_param = ssm.StringParameter(self, 'GenerationHandlerHttpApiUrlParam',
            parameter_name=f'/{parent_stack_name}/generation_handler_api_url',
            string_value=self.http_api.url.rstrip('/')
        )
        gen_handler_api_url_param.apply_removal_policy(RemovalPolicy.DESTROY)

        gen_handler_origin_param = ssm.StringParameter(self, 'GenerationHandlerOriginParam',
            parameter_name=f'/{parent_stack_name}/origin_generation_handler',
            string_value=self.generation_handler_function.function_name
        )
        gen_handler_origin_param.apply_removal_policy(RemovalPolicy.DESTROY)
