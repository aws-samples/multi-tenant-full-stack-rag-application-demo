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
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)

from constructs import Construct
from lib.shared.utils_permissions import UtilsPermissions
from lib.vector_store_provider_service.opensearch_managed import OpenSearchManagedStack
from lib.vector_store_provider_service.opensearch_dashboards_proxy import OpenSearchDashboardsProxyStack
class VectorStoreProviderStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
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
            auth_fn=auth_fn,
            auth_role_arn=auth_role_arn,
            cognito_identity_pool=cognito_identity_pool,
            cognito_user_pool=cognito_user_pool,
            os_data_instance_ct=self.node.try_get_context('os_data_instance_ct'),
            os_data_instance_type=self.node.try_get_context('os_data_instance_type'),
            os_data_instance_volume_size_gb=self.node.try_get_context('os_data_instance_volume_size_gb'),
            os_master_instance_ct=self.node.try_get_context('os_master_instance_ct'),
            os_master_instance_type=self.node.try_get_context('os_master_instance_type'),
            os_multiaz_with_standby_enabled=self.node.try_get_context('os_multiaz_with_standby_enabled'),
            parent_stack_name=parent_stack_name,
            vpc=vpc
        )

        self.opensearch_dashboards_stack = OpenSearchDashboardsProxyStack(self, 'OpenSearchDashboardsProxy',
            app_security_group=app_security_group,
            os_dashboards_ec2_cert_country=self.node.try_get_context('os_dashboards_ec2_cert_country'),
            os_dashboards_ec2_cert_state=self.node.try_get_context('os_dashboards_ec2_cert_state'),
            os_dashboards_ec2_cert_city=self.node.try_get_context('os_dashboards_ec2_cert_city'),
            os_dashboards_ec2_cert_email_address=self.node.try_get_context('os_dashboards_ec2_cert_email_address'),
            os_dashboards_ec2_cert_hostname=self.node.try_get_context('os_dashboards_ec2_cert_hostname'),
            os_dashboards_ec2_enable_traffic_from_ip=self.node.try_get_context('os_dashboards_ec2_enable_traffic_from_ip'),
            os_domain=self.vector_store_stack.domain,
            user_pool_domain=user_pool_domain,
            vpc=vpc                                                                     
        )

        