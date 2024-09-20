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
import os

from constructs import Construct
# from lib.shared.utils_permissions import UtilsPermissions

class BedrockProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
        user_pool_client_id: str,
        user_pool_id:str,
        parent_stack_name: str,
        vpc: ec2.IVpc,
        # **kwargs,
    ) -> None:
        super().__init__(scope, construct_id) #  **kwargs)        
        
        build_cmds = [
            "pip3 install -t /asset-output/ -r /asset-input/bedrock_provider/bedrock_provider_requirements.txt",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider',
            "cp -r /asset-input/bedrock_provider/* /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider",
            'pip3 install -t /asset-output -r /asset-input/utils/utils_requirements.txt',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils/',
            "cp -r /asset-input/utils/* /asset-output/multi_tenant_full_stack_rag_application/utils/",
        ]

        self.bedrock_provider_function = lambda_.Function(self, 'BedrockProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=256,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.bedrock_provider.bedrock_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                "STACK_NAME": parent_stack_name,
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )
        
        self.bedrock_provider_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:*",
                ],
                resources=["*"],
            )
        )

        self.bedrock_provider_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction",
                ],
                resources=[auth_fn.function_arn],
            )
        )
        
        # self.bedrock_provider_function.add_to_role_policy(iam.PolicyStatement(
        #       effect=iam.Effect.ALLOW,
        #       actions=['lambda:Invoke'],
        #       resources=[auth_fn.function_arn]
        # ))

        self.bedrock_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*",            
            ]
        ))

        bedrock_provider_fn_name_param = ssm.StringParameter(
            self, "BedrockProviderFunctionName",
            parameter_name=f"/{parent_stack_name}/bedrock_provider_function_name",
            string_value=self.bedrock_provider_function.function_name
        )
        
        bedrock_provider_fn_name_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)
        self.bedrock_provider_function.grant_invoke(cognito_auth_role)

