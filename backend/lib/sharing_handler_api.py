#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_kinesis as kinesis,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_evts
)
from constructs import Construct


class SharingHandlerApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
        allowed_email_domains: [str],
        auth_role_arn: str,
        embeddings_provider_args: [str],
        embeddings_provider_extra_env: dict,
        embeddings_provider_py_path: str,
        embeddings_provider_req_paths: [str],
        ingestion_status_table: dynamodb.ITable,
        system_settings_table: dynamodb.ITable,
        system_settings_table_stream: kinesis.IStream,
        user_pool_client_id: str,
        user_pool_id: str,
        user_settings_table: dynamodb.ITable,
        user_settings_table_stream: kinesis.IStream,
        vector_store_endpoint: str,
        vector_store_provider_py_path: str,
        vector_store_req_paths: [str],
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'ULCognitoAuthRoleRef', auth_role_arn)

        # Set up user settings stream processor
        build_cmds = [
            "pip3 install -r /asset-input/sharing_handler/user_settings_stream_processor_requirements.txt -t /asset-output/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider',
            'cp /asset-input/bedrock_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/',
            "cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider/",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler',
            'cp /asset-input/document_collections_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider',
            'cp /asset-input/embeddings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider',
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider",
            "cp /asset-input/ingestion_status_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/sharing_handler",
            "cp /asset-input/sharing_handler/sharing_utils.py /asset-output/multi_tenant_full_stack_rag_application/sharing_handler/",
            "cp /asset-input/sharing_handler/user_settings_stream_processor.py /asset-output/multi_tenant_full_stack_rag_application/sharing_handler/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            "cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider/",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider',
            'cp /asset-input/user_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider',
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider',
            'cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider/',
        ]

        self.evt_source = lambda_evts.KinesisEventSource(user_settings_table_stream,
            starting_position=lambda_.StartingPosition.TRIM_HORIZON,
            batch_size=1
        )

        self.user_settings_stream_processor = lambda_.Function(self, 'UserSettingsStreamProcessorFn',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            handler='multi_tenant_full_stack_rag_application.sharing_handler.user_settings_stream_processor.handler',
            runtime=lambda_.Runtime.PYTHON_3_11,
            memory_size=128,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.seconds(60),
            vpc=vpc,
            environment={
                "ALLOWED_EMAIL_DOMAINS": ",".join(allowed_email_domains),
                "INGESTION_STATUS_TABLE": ingestion_status_table.table_name,
                "USER_SETTINGS_TABLE": user_settings_table.table_name,
                "SYSTEM_SETTINGS_TABLE": system_settings_table.table_name
            },
            events=[self.evt_source]
        )
        ingestion_status_table.grant_read_data(self.user_settings_stream_processor.grant_principal)
        system_settings_table.grant_read_write_data(self.user_settings_stream_processor.grant_principal)
        user_settings_table.grant_read_write_data(self.user_settings_stream_processor.grant_principal)

        # set up system settings stream processor
        build_cmds = [
            "pip3 install -r /asset-input/sharing_handler/system_settings_stream_processor_requirements.txt -t /asset-output/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider",
            "cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/sharing_handler",
            "cp /asset-input/sharing_handler/system_settings_stream_processor.py /asset-output/multi_tenant_full_stack_rag_application/sharing_handler/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider",
            "cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider/",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils",
        ]

        self.evt_source = lambda_evts.KinesisEventSource(system_settings_table_stream,
            starting_position=lambda_.StartingPosition.TRIM_HORIZON,
            batch_size=1
        )

        self.system_settings_stream_processor = lambda_.Function(self, 'SystemSettingsStreamProcessorFn',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            handler='multi_tenant_full_stack_rag_application.sharing_handler.system_settings_stream_processor.handler',
            runtime=lambda_.Runtime.PYTHON_3_11,
            memory_size=128,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.seconds(60),
            vpc=vpc,
            environment={
                "SYSTEM_SETTINGS_TABLE": system_settings_table.table_name
            },
            events=[self.evt_source]
        )
        system_settings_table.grant_read_write_data(self.system_settings_stream_processor.grant_principal)
        
        
        build_cmds = []
        for req_path in embeddings_provider_req_paths:
            build_cmds += [f'pip3 install -r /asset-input/{req_path} -t /asset-output/']
        
        for req_path in vector_store_req_paths:
            build_cmds += [f'pip3 install -r /asset-input/{req_path} -t /asset-output/']


        build_cmds += [
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/auth_provider',
            'cp /asset-input/auth_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/auth_provider/',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider',
            'cp /asset-input/bedrock_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/',
            'cp /asset-input/bedrock_provider/*.json /asset-output/multi_tenant_full_stack_rag_application/bedrock_provider/',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider',
            'cp /asset-input/boto_client_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/boto_client_provider',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler',
            'cp /asset-input/document_collections_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider',
            'cp /asset-input/embeddings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/embeddings_provider',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider',
            'cp /asset-input/ingestion_status_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/ingestion_status_provider',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider',
            'cp /asset-input/system_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/system_settings_provider',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/sharing_handler',
            'cp /asset-input/sharing_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/sharing_handler/',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider',
            'cp /asset-input/user_settings_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/user_settings_provider/',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider',
            'cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider/',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils',
            'cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/'
        ]

        self.sharing_function = lambda_.Function(self, 'SharingHandlerFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            handler='multi_tenant_full_stack_rag_application.sharing_handler.sharing_handler.handler',
            runtime=lambda_.Runtime.PYTHON_3_11,
            memory_size=512,
            architecture=lambda_.Architecture.X86_64,
            timeout=Duration.seconds(60),
            vpc=vpc,
            environment={
                **embeddings_provider_extra_env,
                'ALLOWED_EMAIL_DOMAINS': ','.join(allowed_email_domains),
                'EMBEDDINGS_PROVIDER_PY_PATH': embeddings_provider_py_path,
                'EMBEDDINGS_PROVIDER_ARGS': json.dumps(embeddings_provider_args),
                'VECTOR_STORE_ENDPOINT': vector_store_endpoint,
                'INGESTION_STATUS_TABLE': ingestion_status_table.table_name,
                'SYSTEM_SETTINGS_TABLE': system_settings_table.table_name,
                'USER_SETTINGS_TABLE': user_settings_table.table_name,
                'VECTOR_STORE_ENDPOINT': vector_store_endpoint,
                'VECTOR_STORE_PROVIDER_PY_PATH': vector_store_provider_py_path
            }
        )

        self.sharing_function.grant_invoke(cognito_auth_role)

        ingestion_status_table.grant_read_data(self.sharing_function.grant_principal)
        system_settings_table.grant_read_data(self.sharing_function.grant_principal)
        user_settings_table.grant_read_write_data(self.sharing_function.grant_principal)
        
        self.sharing_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/frontendOrigin",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderPyPath",
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/multitenantrag/authProviderArgs"
            ]
        ))

        integration_fn = apigwi.HttpLambdaIntegration(
            'SharingHandlerApiIntegration', 
            self.sharing_function
        )

        api_name = 'sharing'

        self.http_api = apigw.HttpApi(self, 'SharingHandlerApi',
            api_name=api_name,
            create_default_stage=True
        )

        authorizer = apigwa.HttpJwtAuthorizer(
            "SharingHandlerAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/sharing/{collection_id}/{email}',
            methods=[
                apigw.HttpMethod.DELETE
            ],
            authorizer=authorizer,
            integration=integration_fn
        )

        self.http_api.add_routes(
            path='/sharing/{collection_id}/{user_prefix}/{limit}/{last_eval_key}',
            methods=[
                apigw.HttpMethod.GET
            ],
            authorizer=authorizer,
            integration=integration_fn
        )

        self.http_api.add_routes(
            path='/sharing',
            methods=[
                apigw.HttpMethod.POST
            ],
            authorizer=authorizer,
            integration=integration_fn
        )
        
        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=integration_fn
        )

        CfnOutput(self, "SharingHandlerHttpApiUrl", value=self.http_api.url)