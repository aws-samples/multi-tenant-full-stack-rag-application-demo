#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    Duration,
    Size,
    Stack,
    aws_dynamodb as ddb,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_evts,
    aws_opensearchservice as aos,
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
    aws_sqs as sqs,
)
from constructs import Construct


class OpenSearchManagedStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: str,
        cognito_auth_role: iam.IRole,
        cognito_identity_pool_id: str,
        cognito_user_pool_id: str,
        inference_role_arn: str,
        ingestion_role_arn: str,
        ingestion_status_table_name: str,
        os_data_instance_ct: int,
        os_data_instance_type: str,
        os_master_instance_ct: int,
        os_master_instance_type: str,
        os_multiaz_with_standby_enabled: bool,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        inference_role = iam.Role.from_role_arn(self, 'InferenceRoleRef', inference_role_arn)
        ingestion_role = iam.Role.from_role_arn(self, 'IngestionRoleRef', ingestion_role_arn)

        cognito_dashboards_role = iam.Role(
            self, 
            'OpenSearchDashboardsCognitoRole',
            assumed_by=iam.ServicePrincipal('opensearchservice.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, 
                    'OsCognitoAccessPolicy',
                    'arn:aws:iam::aws:policy/AmazonOpenSearchServiceCognitoAccess'
                )
            ],
        )
        cognito_dashboards_role.assume_role_policy.add_statements(iam.PolicyStatement(
            actions=['sts:AssumeRole'],
            principals=[
                iam.ServicePrincipal('es.amazonaws.com'),
            ],
        ))
        #cognito_dashboards_role.grant_assume_role(iam.ServicePrincipal('es.amazonaws.com'))
        # slr = iam.CfnServiceLinkedRole(self, "OpenSearchLinkedRole",
        #     aws_service_name="opensearchservice.amazonaws.com"
        # )

        self.domain = aos.Domain(self, 'Domain', 
            # domain_name=os_domain_name,
            version=aos.EngineVersion.OPENSEARCH_2_7,
            capacity={
                "data_node_instance_type": os_data_instance_type,
                "data_nodes": os_data_instance_ct,
                "master_node_instance_type": os_master_instance_type,
                "master_nodes": os_master_instance_ct,
                "multi_az_with_standby_enabled": os_multiaz_with_standby_enabled
            },
            cognito_dashboards_auth={
                "identity_pool_id": cognito_identity_pool_id,
                "user_pool_id": cognito_user_pool_id,
                "role": cognito_dashboards_role
            },
            ebs={
                "volume_size": 100,
                "volume_type": ec2.EbsDeviceVolumeType.GP3
            },
            enable_auto_software_update=True,
            enforce_https=True,
            node_to_node_encryption=True,
            encryption_at_rest={
                "enabled": True
            },
            security_groups=[app_security_group],
            vpc=vpc,
            vpc_subnets=[{
                "subnetType": ec2.SubnetType.PRIVATE_ISOLATED
            }],
            zone_awareness={
                "enabled": True,
                "availability_zone_count": 2,
            }
        )
        self.domain.add_access_policies(iam.PolicyStatement(
            actions=['es:*'],
            principals=[
                ingestion_role.grant_principal,
                inference_role.grant_principal,
                cognito_auth_role.grant_principal
            ],
            resources=[
                f"arn:aws:es:{self.region}:{self.account}:domain/{self.domain.domain_name}",
                f"arn:aws:es:{self.region}:{self.account}:domain/{self.domain.domain_name}/*",
                f"arn:aws:es:{self.region}:{self.account}:domain/{self.domain.domain_name}/*/*"
            ]
        ))
        self.domain.grant_index_read_write("*", ingestion_role)
        self.domain.grant_read_write(ingestion_role)
        self.domain.grant_index_read("*", inference_role)

        self.vector_store_endpoint = self.domain.domain_endpoint
        