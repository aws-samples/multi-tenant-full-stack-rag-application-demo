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

class GraphStoreProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
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
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/"
        ]

        self.graph_store_provider = lambda_.Function(self, 'GraphStoreProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(bundling_cmds)
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.graph_store_provider.graph_store_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                "STACK_NAME": parent_stack_name,
            }
        )
        self.graph_store_provider.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}/*"
            ]
        ))

        self.graph_store_provider.grant_invoke(cognito_auth_role)

        self.neptune_stack = NeptuneStack(self, "NeptuneStack",
            allowed_role=self.graph_store_provider.role,
            app_security_group=app_security_group,
            instance_type=instance_type,
            parent_stack_name=parent_stack_name,
            removal_policy=RemovalPolicy(self.node.get_context('removal_policy')),
            vpc=vpc
        )
        enrichment_pipelines_integration_fn = apigwi.HttpLambdaIntegration(
            "GraphStoreLambdaIntegration", 
            self.graph_store_provider,
        )

        api_name = 'graph_store'

        self.http_api = apigw.HttpApi(self, "GraphStoreProviderApi",
            api_name=api_name,
            create_default_stage=True
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "GraphStoreAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/enrichment_pipelines',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.DELETE,
                apigw.HttpMethod.POST,
            ],
            authorizer=authorizer,
            integration=enrichment_pipelines_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=enrichment_pipelines_integration_fn
        )
        
        gs_url_param = ssm.StringParameter(self, 'GraphStoreHttpApiUrlParam',
            parameter_name=f'/{parent_stack_name}/graph_store_api_url',
            string_value=self.http_api.url
        )
        gs_url_param.apply_removal_policy(RemovalPolicy.DESTROY)

        CfnOutput(self, "GraphStoreHttpApiUrl", value=self.http_api.url)

        gs_ep_param = ssm.StringParameter(self, 'GraphStoreProviderEndpointUrl',
            parameter_name=f'/{parent_stack_name}/graph_provider_endpoint_url',
            string_value=self.neptune_stack.cluster.cluster_endpoint.socket_address
        )
        gs_ep_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        