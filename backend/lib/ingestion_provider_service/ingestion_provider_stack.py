from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Size,
    Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_dynamodb as ddb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_sqs as sqs,
    aws_ssm as ssm,
)
import os

from constructs import Construct

from lib.shared.bucket import Bucket
from lib.shared.bucket_to_queue_event_trigger import BucketToQueueNotificationStack
from lib.shared.dynamodb_table import DynamoDbTable
from lib.shared.queue_to_function_event_trigger import QueueToFunctionTrigger

class IngestionProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        app_security_group: ec2.ISecurityGroup,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_id: str,
        vpc: ec2.IVpc,
        # **kwargs,
    ) -> None:
        super().__init__(scope, construct_id) #  **kwargs)        
        
        ssm_param_name = 'ingestion_status_table'
        removal_policy = self.node.get_context('removal_policy')

        ingestion_status_table = DynamoDbTable(self, 'DdbTable',
            parent_stack_name=parent_stack_name,
            partition_key='user_id',
            partition_key_type=ddb.AttributeType.STRING,
            removal_policy=RemovalPolicy(removal_policy),
            resource_name='IngestionStatusTable',
            ssm_parameter_name=ssm_param_name,
            sort_key='doc_id',
            sort_key_type=ddb.AttributeType.STRING,
        )

        build_cmds = [
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_provider',
            "cp -r /asset-input/ingestion_provider/*.{txt,py} /asset-output/multi_tenant_full_stack_rag_application/ingestion_provider",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils/',
            "cp -r /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/"
        ]

        self.ingestion_status_function = lambda_.Function(self, 'IngestionStatusProviderFunction',
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
            handler='multi_tenant_full_stack_rag_application.ingestion_provider.ingestion_status_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                "STACK_NAME": parent_stack_name,
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )
        
        self.ingestion_status_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'ssm:GetParameter'
            ],
            resources=[
                f'arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}/*'
            ]
        ))

        ingestion_status_table.table.grant_read_write_data(self.ingestion_status_function.grant_principal)

        # self.ingestion_status_provider_role = self.ingestion_status_function.role.grant_principal

        self.ingestion_function = lambda_.Function(self, 'VectorIngestionFunction',
            code=lambda_.Code.from_asset_image(
                'src/multi_tenant_full_stack_rag_application', 
                file="ingestion_provider/Dockerfile.vector_ingestion_provider",
                # build_args={
                #     "emb_provider_reqs": ' '.join(embeddings_provider_requirements_paths),
                #     "vector_store_reqs": ' '.join(vector_store_requirements_paths)
                # }
            ),
            dead_letter_queue=sqs.Queue(self, 'IngestionDLQ',
                visibility_timeout=Duration.minutes(60),
                retention_period=Duration.days(14)
            ),
            memory_size=4096,
            ephemeral_storage_size=Size.gibibytes(10),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            runtime=lambda_.Runtime.FROM_IMAGE,
            handler=lambda_.Handler.FROM_IMAGE,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.minutes(15),
            security_groups=[app_security_group],
            environment={ 
                # **embeddings_provider_extra_env,
                # "ALLOWED_EMAIL_DOMAINS": ",".join(allowed_email_domains),
                # "IDENTITY_POOL_ID": cognito_identity_pool_id,
                # "USER_POOL_ID": cognito_user_pool_id,
                # "EMBEDDINGS_PROVIDER_ARGS": json.dumps(embeddings_provider_args),
                # "EMBEDDINGS_PROVIDER_PY_PATH": embeddings_provider_py_path,
                # "INGESTION_STATUS_TABLE": ingestion_status_table.table_name,
                # "OCR_MODEL_ID": ocr_model_id,
                # "PATH": "$PATH:/var/task/bin",
                # "SYSTEM_SETTINGS_TABLE": system_settings_table.table_name,
                # "USER_SETTINGS_TABLE": user_settings_table.table_name,
                # "VECTOR_STORE_ENDPOINT": vector_store_endpoint,
                # "VECTOR_STORE_PROVIDER_PY_PATH": vector_store_provider_py_path,
            }
        )

        ingestion_status_table.table.grant_read_write_data(self.ingestion_function.grant_principal)

        self.ingestion_bucket = Bucket(self, 'IngestionBucket',
            'IngestionBucket',
            parent_stack_name=parent_stack_name,
            removal_policy=RemovalPolicy(removal_policy),
            ssm_parameter_name='ingestion_bucket'
        )
        
        self.ingestion_bucket.bucket.grant_read(self.ingestion_function.role)

        self.ingestion_queue = sqs.Queue(self, 'IngestionQueue',
            visibility_timeout=Duration.minutes(15),
            retention_period=Duration.days(1)
        )

        self.ingestion_queue.grant_consume_messages(self.ingestion_function.grant_principal)

        self.queue_to_function_trigger_stack = QueueToFunctionTrigger(self, 'QueueToFunctionTrigger',
            function=self.ingestion_function,
            queue_arn=self.ingestion_queue.queue_arn,
            resource_name='IngestionQueueToFunctionTrigger'
        )

        CfnOutput(self, 'IngestionBucketName',
            value=self.ingestion_bucket.bucket.bucket_name,
        )
    

        ingestion_provider_integration_fn = apigwi.HttpLambdaIntegration(
            "IngestionProviderLambdaIntegration", 
            self.ingestion_status_function,
        )

        api_name = 'ingestion_status'

        self.http_api = apigw.HttpApi(self, "IngestionProviderHandlerApi",
            api_name=api_name,
            create_default_stage=True
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "IngestionProviderAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/ingestion_status',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.DELETE,
                apigw.HttpMethod.POST
            ],
            authorizer=authorizer,
            integration=ingestion_provider_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=ingestion_provider_integration_fn
        )
        
        CfnOutput(self, "IngestionStatusHttpApiUrl", value=self.http_api.url)

        isp_url_param = ssm.StringParameter(self, 'IngestionStatusHttpApiUrlParam',
            parameter_name=f"/{parent_stack_name}/ingestion_status_provider_api_url",
            string_value=self.http_api.url
        )
        isp_url_param.apply_removal_policy(RemovalPolicy.DESTROY)