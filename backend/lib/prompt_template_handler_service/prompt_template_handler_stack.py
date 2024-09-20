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
    aws_dynamodb as ddb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)
from constructs import Construct
from lib.shared.dynamodb_table import DynamoDbTable
# from lib.shared.utils_permissions import UtilsPermissions


class PromptTemplateHandlerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_id: str,
        vpc: ec2.IVpc,
        # **kwargs,
    ) -> None:
        super().__init__(scope, construct_id) #  **kwargs)        
        
        cognito_auth_role = iam.Role.from_role_arn(self, 'PTCognitoAuthRole', auth_role_arn)

        self.prompt_templates_table = DynamoDbTable(self, 'PromptTemplatesTable',
            parent_stack_name=parent_stack_name,
            partition_key='user_id',
            partition_key_type=ddb.AttributeType.STRING,
            removal_policy=RemovalPolicy(self.node.get_context('removal_policy')),
            resource_name='PromptTemplatesTable',
            sort_key='sort_key',
            sort_key_type=ddb.AttributeType.STRING
        )
        
        self.prompt_templates_table.table.add_global_secondary_index(
            index_name='by_template_id',
            partition_key=ddb.Attribute(name='template_id', type=ddb.AttributeType.STRING),
        )

        build_cmds = [
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider',
            'cp /asset-input/bedrock_provider/bedrock_model_params.json /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates',
            "cp -r /asset-input/prompt_template_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler",
            "cp -r /asset-input/prompt_template_handler/prompt_templates/*.txt /asset-output/multi_tenant_full_stack_rag_application/prompt_template_handler/prompt_templates",
            'pip3 install -t /asset-output -r /asset-input/utils/utils_requirements.txt',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils/',
            "cp -r /asset-input/utils/* /asset-output/multi_tenant_full_stack_rag_application/utils/",
        ]

        self.prompt_template_handler_function = lambda_.Function(self, 'PromptTemplateHandlerFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.prompt_template_handler.prompt_template_handler.handler',
            timeout=Duration.seconds(60),
            environment={
                "PROMPT_TEMPLATES_TABLE": self.prompt_templates_table.table.table_name,
                "STACK_NAME": parent_stack_name
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )
        
        pt_fn_name_param = ssm.StringParameter(
            self, "PromptTemplateHandlerFunctionNameParam",
            parameter_name=f"/{parent_stack_name}/prompt_template_handler_function_name",
            string_value=self.prompt_template_handler_function.function_name
        )
        pt_fn_name_param.apply_removal_policy(RemovalPolicy.DESTROY)

        self.prompt_templates_table.table.grant_read_write_data(self.prompt_template_handler_function.grant_principal)
        
        self.prompt_template_handler_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'ssm:GetParameter',
                'ssm:GetParametersByPath'
            ],
            resources=[
                f'arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*'
            ]
        ))

        self.prompt_template_handler_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction",
                ],
                resources=[auth_fn.function_arn],
            )
        )
        
        self.prompt_template_handler_function.grant_invoke(cognito_auth_role)

        # UtilsPermissions(self, 'UtilsPermissions', self.prompt_template_handler_function.role)

        prompt_template_handler_integration_fn = apigwi.HttpLambdaIntegration(
            "PromptTemplateHandlerLambdaIntegration",
            self.prompt_template_handler_function
        )

        api_name = 'prompt_templates'

        self.http_api = apigw.HttpApi(self, 'PromptTemplateHandlerHttpApi',
            api_name=api_name,
            create_default_stage=True
        )

        authorizer = apigwa.HttpJwtAuthorizer(
            "PromptTemplateHandlerAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id]
        )

        self.http_api.add_routes(
            path='/prompt_templates',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.POST,
                apigw.HttpMethod.PUT,
                apigw.HttpMethod.DELETE
            ],
            authorizer=authorizer,
            integration=prompt_template_handler_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=prompt_template_handler_integration_fn
        )
        
        cognito_auth_role.add_to_principal_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['apigateway:DELETE', 'apigateway:GET', 'apigateway:POST'],
            resources=[
                f"arn:aws:apigateway:{self.region}::/apis/{self.http_api.http_api_id}/*"            ]
        ))
        pt_url_param = ssm.StringParameter(
            self, "PromptTemplateHandlerApiUrlParam",
            parameter_name=f"/{parent_stack_name}/prompt_template_handler_api_url",
            string_value=self.http_api.url.rstrip('/')
        )
        pt_url_param.apply_removal_policy(RemovalPolicy.DESTROY)

        CfnOutput(self, "PromptTemplateHandlerApiUrl",
            value=self.http_api.url.rstrip('/'),
        )