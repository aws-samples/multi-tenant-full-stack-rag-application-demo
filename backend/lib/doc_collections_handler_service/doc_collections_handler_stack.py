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
# from lib.shared.utils_permissions import UtilsPermissions


class DocumentCollectionsHandlerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
        cognito_identity_pool_id: str,
        cognito_user_pool_client_id,
        cognito_user_pool_id: str,
        parent_stack_name: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
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
            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output"
        ]
        # must be one of "DESTROY", "RETAIN", "RETAIN_ON_UPDATE_OR_DELETE", or "SNAPSHOT"
        removal_policy = self.node.get_context('removal_policy')

        self.doc_collections_table_stack = DynamoDbTable(self, 'DocCollectionsTable',
            parent_stack_name=parent_stack_name,
            partition_key='user_id',
            partition_key_type=ddb.AttributeType.STRING,
            removal_policy=RemovalPolicy(removal_policy),
            resource_name='DocCollectionsTable',
            sort_key='sort_key',
            sort_key_type=ddb.AttributeType.STRING,
        )
        
        self.doc_collections_table_stack.table.add_global_secondary_index(
            index_name='by_collection_id',
            partition_key=ddb.Attribute(name='collection_id', type=ddb.AttributeType.STRING),
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
            environment={
                "DOCUMENT_COLLECTIONS_TABLE": self.doc_collections_table_stack.table.table_name,
                "STACK_NAME": parent_stack_name,
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[app_security_group]
        )
       
        doc_collection_fn_name_param = ssm.StringParameter(self, 'DocCollectionsFunctionName',
            parameter_name=f'/{parent_stack_name}/document_collections_handler_function_name',
            string_value=self.doc_collections_function.function_name
        )
        
        doc_collection_fn_name_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        doc_collection_origin_param = ssm.StringParameter(self, 'DocCollectionsOrigin',
            parameter_name=f'/{parent_stack_name}/origin_document_collections_handler',
            string_value=self.doc_collections_function.function_name
        )
        doc_collection_origin_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        self.doc_collections_table_stack.table.grant_read_write_data(self.doc_collections_function.grant_principal)

        self.doc_collections_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*",
            ]
        ))

        self.doc_collections_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction",
                    "execute-api:Invoke"
                ],
                resources=['*']
                # security TODO fix this to be more restrictive later
                #resources=[auth_fn.function_arn],
            )
        )

        doc_collections_api_name = 'document_collections'
        doc_collections_integration_fn = apigwi.HttpLambdaIntegration(
            "DocCollectionsLambdaIntegration",
            self.doc_collections_function
        )

        self.http_api = apigw.HttpApi(self, 'DocCollectionsHttpApi',
            api_name=doc_collections_api_name,
            create_default_stage=True
        )

        doc_collections_api_url_param = ssm.StringParameter(self, 'DocCollectionsHttpApiUrl',
            parameter_name=f'/{parent_stack_name}/doc_collections_handler_api_url',
            string_value=self.http_api.url.rstrip('/')
        )
        doc_collections_api_url_param.apply_removal_policy(RemovalPolicy.DESTROY)

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
            path='/document_collections/{collection_id}',
            methods=[
                apigw.HttpMethod.DELETE
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

        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)
        cognito_auth_role.grant_assume_role(self.doc_collections_function.grant_principal
        )
        self.doc_collections_function.grant_invoke(cognito_auth_role)

        cognito_auth_role.add_to_principal_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['apigateway:DELETE', 'apigateway:GET', 'apigateway:POST'],
            resources=[
                f"arn:aws:apigateway:{self.region}::/apis/{self.http_api.http_api_id}/*"            ]
        ))
        
        CfnOutput(self, "HttpApiUrl", value=self.http_api.url.rstrip('/').rstrip('/'))