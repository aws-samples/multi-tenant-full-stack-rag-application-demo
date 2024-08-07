#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_authorizers as apigwa,
    aws_apigatewayv2_integrations as apigwi,
    aws_dynamodb as ddb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_notifications as s3_notif,
    aws_sqs as sqs
)
from constructs import Construct

class DocumentCollectionsApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        doc_collections_function: lambda_.IFunction,
        user_pool_client_id: str,
        user_pool_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        doc_collections_api_name = 'document_collections'

        doc_collections_integration_fn = apigwi.HttpLambdaIntegration(
            "DocCollectionsLambdaIntegration", 
            doc_collections_function
        )

        self.http_api = apigw.HttpApi(self, "DocCollectionsHttpApi",
            api_name=doc_collections_api_name,
            create_default_stage=True,
            # cors_preflight=apigw.CorsPreflightOptions(
            #     allow_origins=["*"],
            #     allow_methods=[apigw.CorsHttpMethod.ANY]
            # )
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "DocCollectionsHttpAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
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