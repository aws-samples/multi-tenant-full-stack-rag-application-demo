import os

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
    aws_cognito as cognito, 
    aws_cognito_identitypool_alpha as idp,
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)

from constructs import Construct

from lib.vector_store_provider_service.opensearch_managed import OpenSearchManagedStack

class VectorStoreProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        cognito_identity_pool: idp.IdentityPool,
        cognito_user_pool: cognito.UserPool,
        parent_stack_name: str,
        user_pool_client_id: str,
        user_pool_domain: cognito.UserPoolDomain,
        user_pool_id: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vector_store_stack = OpenSearchManagedStack(self, "OpenSearchManagedStack",
            app_security_group=app_security_group,
            cognito_identity_pool=cognito_identity_pool,
            cognito_user_pool=cognito_user_pool,
            os_data_instance_ct=self.node.try_get_context('os_data_instance_ct'),
            os_data_instance_type=self.node.try_get_context('os_data_instance_type'),
            os_data_instance_volume_size_gb=self.node.try_get_context('os_data_instance_volume_size_gb'),
            os_master_instance_ct=self.node.try_get_context('os_master_instance_ct'),
            os_master_instance_type=self.node.try_get_context('os_master_instance_type'),
            os_multiaz_with_standby_enabled=self.node.try_get_context('os_multiaz_with_standby_enabled'),
            os_dashboards_ec2_cert_country=self.node.try_get_context('os_dashboards_ec2_cert_country'),
            os_dashboards_ec2_cert_state=self.node.try_get_context('os_dashboards_ec2_cert_state'),
            os_dashboards_ec2_cert_city=self.node.try_get_context('os_dashboards_ec2_cert_city'),
            os_dashboards_ec2_cert_email_address=self.node.try_get_context('os_dashboards_ec2_cert_email_address'),
            os_dashboards_ec2_cert_hostname=self.node.try_get_context('os_dashboards_ec2_cert_hostname'),
            os_dashboards_ec2_enable_traffic_from_ip=self.node.try_get_context('os_dashboards_ec2_enable_traffic_from_ip'),
            parent_stack_name=parent_stack_name,
            user_pool_domain=user_pool_domain,
            vpc=vpc
        )

        self.vector_store_provider = lambda_.Function(self, 'VectorStoreProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join([
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
                            "cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils"
                        ])
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.vector_store_provider.vector_store_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                # 'AWS_ACCOUNT': self.account,
                # 'IDENTITY_POOL_ID': identity_pool_id,
                # 'USER_POOL_ID': user_pool_id,
                # 'USER_SETTINGS_TABLE': user_settings_table.table_name
            }
        )

        vector_store_provider_integration_fn = apigwi.HttpLambdaIntegration(
            "VectorStoreProviderLambdaIntegration", 
            self.vector_store_provider,
        )

        api_name = 'vector_store'

        self.http_api = apigw.HttpApi(self, "VectorStoreProviderHandlerApi",
            api_name=api_name,
            create_default_stage=True
        )
        
        authorizer = apigwa.HttpJwtAuthorizer(
            "VectorStoreProviderAuthorizer",
            f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}",
            identity_source=["$request.header.Authorization"],
            jwt_audience=[user_pool_client_id],
        )

        self.http_api.add_routes(
            path='/vector_store',
            methods=[
                apigw.HttpMethod.GET,
                apigw.HttpMethod.DELETE,
                apigw.HttpMethod.POST,
            ],
            authorizer=authorizer,
            integration=vector_store_provider_integration_fn
        )

        self.http_api.add_routes(
            path='/{proxy+}',
            methods=[
                apigw.HttpMethod.OPTIONS
            ],
            integration=vector_store_provider_integration_fn
        )
        
        CfnOutput(self, "VectorStoreHttpApiUrl", value=self.http_api.url)

        vs_url_param = ssm.StringParameter(self, 'VectorStoreHttpApiUrlParam',
            parameter_name=f'/{parent_stack_name}/vector_store_provider_api_url',
            string_value=self.http_api.url
        )
        vs_url_param.apply_removal_policy(RemovalPolicy.DESTROY)
        