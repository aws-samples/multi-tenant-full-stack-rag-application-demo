from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Size,
    Stack,
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
# from lib.shared.bucket_to_queue_event_trigger import BucketToQueueNotification
from lib.shared.dynamodb_table import DynamoDbTable
from lib.shared.queue import Queue
from lib.shared.queue_to_function_event_trigger import QueueToFunctionTrigger
# from lib.shared.utils_permissions import UtilsPermissions

class IngestionProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_id: str,
        vpc: ec2.IVpc,
        # vpc_endpoint_apigw: ec2.InterfaceVpcEndpointAwsService,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id) #  **kwargs)        
        
        # ssm_param_name = 'self.ingestion_status_table'
        removal_policy = self.node.get_context('removal_policy')
        
        self.ingestion_bucket = Bucket(self, 'IngestionBucket',
            'IngestionBucket',
            True, # add_cors
            parent_stack_name=parent_stack_name,
            removal_policy=RemovalPolicy(removal_policy),
        )
        
        self.ingestion_status_table = DynamoDbTable(self, 'DdbTable',
            parent_stack_name=parent_stack_name,
            partition_key='user_id',
            partition_key_type=ddb.AttributeType.STRING,
            removal_policy=RemovalPolicy(removal_policy),
            resource_name='IngestionStatusTable',
            sort_key='doc_id',
            sort_key_type=ddb.AttributeType.STRING,
        )

        build_cmds = [
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_provider/',
            "cp -r /asset-input/ingestion_provider/ingestion*.py /asset-output/multi_tenant_full_stack_rag_application/ingestion_provider",
            'pip3 install -t /asset-output -r /asset-input/utils/utils_requirements.txt',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils/',
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/"
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
                "AWS_ACCOUNT_ID": self.account,
                "EMBEDDING_MODEL_ID": self.node.get_context('embeddings_model_id'),
                "INGESTION_BUCKET": self.ingestion_bucket.bucket.bucket_name,
                "INGESTION_STATUS_TABLE": self.ingestion_status_table.table.table_name,
                "STACK_NAME": parent_stack_name,
                "UPDATED": "2024-09-20T23:02:00Z"
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )

        self.ingestion_status_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'ssm:GetParameter','ssm:GetParametersByPath'
            ],
            resources=[
                f'arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*'
            ]
        ))

        self.ingestion_status_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction",
                ],
                resources=[auth_fn.function_arn],
            )
        )
        # self.ingestion_status_function.add_to_role_policy(iam.PolicyStatement(
        #     effect=iam.Effect.ALLOW,
        #     actions=['lambda:Invoke'],
        #     resources=[auth_fn.function_arn]
        # ))

        # UtilsPermissions(self, 'IngestionStatusUtilsPermissions', self.ingestion_status_function.role)

        self.ingestion_status_table.table.grant_read_write_data(self.ingestion_status_function.grant_principal)

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
                "AWS_ACCOUNT_ID": self.account,
                "EMBEDDING_MODEL_ID": self.node.get_context("embeddings_model_id"),
                "STACK_NAME": parent_stack_name,
                "INGESTION_STATUS_TABLE": self.ingestion_status_table.table.table_name,
                "OCR_MODEL_ID": self.node.get_context('ocr_model_id'),
                "UPDATED": "2024-09-20T23:02:00Z",
            }
        )
        self.ingestion_status_function.grant_invoke(self.ingestion_function.grant_principal)
        
        self.ingestion_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'ssm:GetParameter','ssm:GetParametersByPath'
            ],
            resources=[
                f'arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*'
            ]
        ))
        
        self.ingestion_status_table.table.grant_read_write_data(self.ingestion_function.grant_principal)
        
        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)

        cognito_auth_role.attach_inline_policy(iam.Policy(self, 'CognitoAuthDocBucketPolicy',
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:DeleteObject"
                    ],
                    resources=[
                        f"{self.ingestion_bucket.bucket.bucket_arn}/private/{'${cognito-identity.amazonaws.com:sub}'}/*",
                    ]
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        's3:ListBucket'
                    ],
                    resources=[
                        f"{self.ingestion_bucket.bucket.bucket_arn}"
                    ],
                    conditions={
                        "StringLike": {
                            "s3:prefix": [
                                "private/${cognito-identity.amazonaws.com:sub}/",
                                "private/${cognito-identity.amazonaws.com:sub}/*"
                            ]
                        }
                    }
                )
            ]
        ))
        
        self.ingestion_bucket.bucket.grant_read(self.ingestion_function.role)
        self.ingestion_bucket.bucket.grant_delete(self.ingestion_status_function.grant_principal)

        self.ingestion_queue = Queue(self, 'IngestionQueue',
            resource_name='IngestionQueue',
            visibility_timeout=Duration.minutes(15),
            bucket_name=self.ingestion_bucket.bucket.bucket_name
        )

        self.queue_to_function_trigger_stack = QueueToFunctionTrigger(self, 'QueueToFunctionTrigger',
            function=self.ingestion_function,
            queue_arn=self.ingestion_queue.queue.queue_arn,
            resource_name='IngestionQueueToFunctionTrigger'
        )
        
        self.ingestion_queue.queue.grant_consume_messages(self.ingestion_function.grant_principal)

        CfnOutput(self, 'IngestionBucketName',
            value=self.ingestion_bucket.bucket.bucket_name,
        )

        isp_fn_name_param = ssm.StringParameter(self, 'IngestionStatusFunctionName',
            parameter_name=f"/{parent_stack_name}/ingestion_status_provider_function_name",
            string_value=self.ingestion_status_function.function_name,
        )
        
        isp_fn_name_param.apply_removal_policy(RemovalPolicy.DESTROY)

        isp_origin_param = ssm.StringParameter(self, 'IngestionStatusProviderOriginParam',
            parameter_name=f"/{parent_stack_name}/origin_ingestion_status_provider",
            string_value=self.ingestion_status_function.function_name
        )
        isp_origin_param.apply_removal_policy(RemovalPolicy('DESTROY'))
        
        ip_fn_name_param = ssm.StringParameter(self, 'IngestionProviderFunctionName',
            parameter_name=f"/{parent_stack_name}/ingestion_provider_function_name",
            string_value=self.ingestion_function.function_name,
        )
    
        ip_fn_name_param.apply_removal_policy(RemovalPolicy.DESTROY)

        ip_origin_param = ssm.StringParameter(self, 'IngestionProviderOriginParam',
            parameter_name=f"/{parent_stack_name}/origin_ingestion_provider",
            string_value=self.ingestion_function.function_name
        )
        ip_origin_param.apply_removal_policy(RemovalPolicy('DESTROY'))
        