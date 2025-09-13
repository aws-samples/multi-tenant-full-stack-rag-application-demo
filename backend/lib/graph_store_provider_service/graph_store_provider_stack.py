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
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_neptune_alpha as neptune,
    aws_ssm as ssm,
)

from constructs import Construct
from lib.graph_store_provider_service.neptune import NeptuneStack
# from lib.shared.utils_permissions import UtilsPermissions

class GraphStoreProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
        instance_type: str,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_id: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)

        bundling_cmds = []

        bundling_cmds += [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/graph_store_provider",
            "cp /asset-input/graph_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/graph_store_provider/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output"
        ]

        self.graph_store_provider = lambda_.Function(self, 'GraphStoreProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(bundling_cmds)
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,
            handler='multi_tenant_full_stack_rag_application.graph_store_provider.neptune_graph_store_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                "STACK_NAME": parent_stack_name,
                "SERVICE_REGION": self.region,
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            security_groups=[app_security_group]
        )

        gs_fn_name = ssm.StringParameter(self, 'GraphStoreProviderFunctionName',
            parameter_name=f'/{parent_stack_name}/graph_store_provider_function_name',
            string_value=self.graph_store_provider.function_name
        )
        gs_fn_name.apply_removal_policy(RemovalPolicy.DESTROY)

        self.graph_store_provider.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*"
            ]
        ))

        self.graph_store_provider.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction",
                ],
                resources=[auth_fn.function_arn],
            )
        )

        # UtilsPermissions(self, 'UtilsPermissions', self.graph_store_provider.role)
        self.graph_store_provider.grant_invoke(cognito_auth_role)

        self.neptune_stack = NeptuneStack(self, "NeptuneStack",
            allowed_role=self.graph_store_provider.role,
            app_security_group=app_security_group,
            instance_type=instance_type,
            parent_stack_name=parent_stack_name,
            removal_policy=RemovalPolicy(self.node.get_context('removal_policy')),
            vpc=vpc
        )        
        self.neptune_stack.cluster.grant_connect(self.graph_store_provider.grant_principal) # Grant the role neptune-db:* access to the DB
        self.neptune_stack.cluster.grant(self.graph_store_provider.grant_principal, "neptune-db:ReadDataViaQuery", "neptune-db:WriteDataViaQuery")
