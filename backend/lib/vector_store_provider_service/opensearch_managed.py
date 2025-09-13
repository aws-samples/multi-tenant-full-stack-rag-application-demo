#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    Duration,
    RemovalPolicy,
    Size,
    NestedStack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_opensearchservice as aos,
    aws_ssm as ssm,
)
from aws_cdk.aws_cognito import UserPool, UserPoolDomain
from aws_cdk.aws_cognito_identitypool_alpha import IdentityPool
from constructs import Construct

from lib.shared.opensearch_access_policy import OpenSearchAccessPolicy


class OpenSearchManagedStack(NestedStack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
        cognito_identity_pool: IdentityPool,
        cognito_user_pool: UserPool,
        os_data_instance_ct: int,
        os_data_instance_type: str,
        os_data_instance_volume_size_gb: int,
        os_master_instance_ct: int,
        os_master_instance_type: str,
        os_multiaz_with_standby_enabled: bool,
        parent_stack_name: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # inference_role = iam.Role.from_role_arn(self, 'InferenceRoleRef', inference_role_arn)
        # ingestion_role = iam.Role.from_role_arn(self, 'IngestionRoleRef', ingestion_role_arn)

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
            ]
        ))

        self.domain = aos.Domain(self, 'OsDomain', 
            version=aos.EngineVersion.OPENSEARCH_2_7,
            capacity={
                "data_node_instance_type": os_data_instance_type,
                "data_nodes": os_data_instance_ct,
                "master_node_instance_type": os_master_instance_type,
                "master_nodes": os_master_instance_ct,
                "multi_az_with_standby_enabled": os_multiaz_with_standby_enabled
            },
            cognito_dashboards_auth={
                "identity_pool_id": cognito_identity_pool.identity_pool_id,
                "user_pool_id": cognito_user_pool.user_pool_id,
                "role": cognito_dashboards_role
            },
            ebs={
                "volume_size": os_data_instance_volume_size_gb,
                "volume_type": ec2.EbsDeviceVolumeType.GP3
            },
            enable_auto_software_update=True,
            enforce_https=True,
            node_to_node_encryption=True,
            encryption_at_rest={
                "enabled": True
            },
            removal_policy=RemovalPolicy(
                self.node.get_context('removal_policy')
            ),
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
        
        OpenSearchAccessPolicy(self, "OpenSearchCognitoDashboardsAccess",
            self.domain,
            cognito_dashboards_role.grant_principal,
            True, True, True, True
        )
        
        self.vector_store_endpoint = self.domain.domain_endpoint

        self.vector_store_provider = lambda_.Function(self, 'VectorStoreProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join([
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
                            "cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output",
                            "pip3 install -r /asset-input/vector_store_provider/opensearch_requirements.txt -t /asset-output"
                        ])
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,
            handler='multi_tenant_full_stack_rag_application.vector_store_provider.opensearch_vector_store_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                'STACK_NAME': parent_stack_name,
                'VECTOR_STORE_ENDPOINT': self.vector_store_endpoint,
                # 'AWS_ACCOUNT_ID': self.account,
                # 'IDENTITY_POOL_ID': identity_pool_id,
                # 'USER_POOL_ID': user_pool_id,
                # 'USER_SETTINGS_TABLE': user_settings_table.table_name
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[app_security_group],
        )

        self.vector_store_provider.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction",
                ],
                resources=[auth_fn.function_arn],
            )
        )
        
        OpenSearchAccessPolicy(self, "OpenSearchVectorServiceAccess",
            self.domain,
            self.vector_store_provider.grant_principal,
            True, True, True, True
        )

        self.vector_store_provider.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*",            
            ]
        ))

        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)

        self.vector_store_provider.grant_invoke(cognito_auth_role)

        OpenSearchAccessPolicy(self, 'OpenSearchAccessForCognitoRole',
            self.domain,
            cognito_auth_role.grant_principal,
            True, True, True, True
        )

        vs_fn_name = ssm.StringParameter(self, 'VectorStoreProviderFunctionName',
            parameter_name=f'/{parent_stack_name}/vector_store_provider_function_name',
            string_value=self.vector_store_provider.function_name
        )

        vs_fn_name.apply_removal_policy(RemovalPolicy.DESTROY)
        
        vs_origin_param = ssm.StringParameter(self, 'VectorStoreProviderOrigin',
            parameter_name=f'/{parent_stack_name}/origin_vector_store_provider',
            string_value=self.vector_store_provider.function_name
        )

        vs_origin_param.apply_removal_policy(RemovalPolicy.DESTROY)

