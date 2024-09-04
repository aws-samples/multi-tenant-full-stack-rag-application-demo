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
    aws_dynamodb as ddb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)
from constructs import Construct
from lib.shared.dynamodb_table import DynamoDbTable


class DocumentCollectionsHandlerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        auth_role_arn: str,
        cognito_identity_pool_id: str,
        cognito_user_pool_client_id,
        cognito_user_pool_id: str,
        parent_stack_name: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)
        
        build_cmds = []

        # for path in embeddings_provider_req_paths:
        #     build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")
        
        # for path in vector_store_req_paths:
        #     build_cmds.append(f"pip3 install -r /asset-input/{path} -t /asset-output/")

        build_cmds += [
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler",
            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
            "cp /asset-input/document_collections_handler/*.py /asset-output/multi_tenant_full_stack_rag_application/document_collections_handler/",
            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils/",
        ]
        # must be one of "DESTROY", "RETAIN", "RETAIN_ON_UPDATE_OR_DELETE", or "SNAPSHOT"
        removal_policy = self.node.get_context('removal_policy')

        self.doc_collections_table_stack = DynamoDbTable(self, 'DocCollectionsTable',
            parent_stack_name=parent_stack_name,
            partition_key='user_id',
            partition_key_type=ddb.AttributeType.STRING,
            removal_policy=RemovalPolicy(removal_policy),
            resource_name='DocCollectionsTable',
            ssm_parameter_name='document_collections_table',
            sort_key='sort_key',
            sort_key_type=ddb.AttributeType.STRING
        )

        self.doc_collections_function = lambda_.Function(self, 'DocCollectionsHandlerFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.document_collections_handler.document_collections_handler.handler',
            timeout=Duration.seconds(60),
            environment={}
        )
       
        self.doc_collections_function.grant_invoke(cognito_auth_role)
        self.doc_collections_table_stack.table.grant_read_write_data(self.doc_collections_function.grant_principal)

        self.doc_collections_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}/*",
            ]
        ))

        doc_collections_api_name = 'document_collections'
        doc_collections_integration_fn = apigwi.HttpLambdaIntegration(
            "DocCollectionsLambdaIntegration",
            self.doc_collections_function
        )

        self.http_api = apigw.HttpApi(self, 'DocCollectionsHttpApi',
            api_name=doc_collections_api_name,
            create_default_stage=True
        )

        ssm.StringParameter(self, 'DocCollectionsHttpApiUrl',
            parameter_name=f'/{parent_stack_name}/document_collections_http_url',
            string_value=self.http_api.api_id
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "DocCollectionsHttpAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{cognito_user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[cognito_user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/document_collections',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.POST,
                apigw.HttpMethod.PUT,
                apigw.HttpMethod.DELETE
            ],
            authorizer=authorizer,
            integration=doc_collections_integration_fn
        )
        self.http_api.add_routes(
            path='/document_collections/{collection_id}/{limit}/{last_eval_key}',
            methods=[
                apigw.HttpMethod.GET
            ],
            authorizer=authorizer,
            integration=doc_collections_integration_fn
        )

        self.http_api.add_routes(
            path='/document_collections/{collection_id}/{file_name}',
            methods=[
                apigw.HttpMethod.DELETE
            ],
            authorizer=authorizer,
            integration=doc_collections_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=doc_collections_integration_fn
        )

        CfnOutput(self, "HttpApiUrl", value=self.http_api.url)