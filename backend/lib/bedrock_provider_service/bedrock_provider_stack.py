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
    aws_ssm as ssm,
)
import os

from constructs import Construct


class BedrockProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
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

        self.bedrock_provider_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}/*",            
            ]
        ))
        
        bedrock_provider_integration_fn = apigwi.HttpLambdaIntegration(
            "BedrockProviderLambdaIntegration",
            self.bedrock_provider_function
        )

        api_name = 'bedrock_provider'

        self.http_api = apigw.HttpApi(self, 'BedrockProviderHttpApi',
            api_name=api_name,
            create_default_stage=True
        )

        authorizer = apigwa.HttpJwtAuthorizer(
            "BedrockProviderAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id]
        )

        self.http_api.add_routes(
            path='/bedrock_provider/list_models',
            methods=[
                apigw.HttpMethod.GET,
            ],
            authorizer=authorizer,
            integration=bedrock_provider_integration_fn
        )
        
        self.http_api.add_routes(
            path='/bedrock_provider/{operation}/{model_id}',
            methods=[
                apigw.HttpMethod.GET,
            ],
            authorizer=authorizer,
            integration=bedrock_provider_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=bedrock_provider_integration_fn
        )

        bedrock_provider_api_url_param = ssm.StringParameter(
            self, "BedrockProviderApiUrlParam",
            parameter_name=f"/{parent_stack_name}/bedrock_provider_api_url",
            string_value=self.http_api.url
        )
        
        bedrock_provider_api_url_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        CfnOutput(self, "BedrockProviderApiUrl",
            value=self.http_api.url,
        )

