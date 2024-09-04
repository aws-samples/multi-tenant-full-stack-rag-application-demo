#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_neptune_alpha as neptune,
    aws_ssm as ssm,
)
from constructs import Construct

class NeptuneStack(Construct):
    def __init__(self, scope, id, 
        allowed_role: iam.IRole,
        app_security_group: ec2.ISecurityGroup,
        instance_type: str,
        parent_stack_name: str,
        removal_policy: RemovalPolicy,
        vpc: ec2.IVpc,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        self.cluster = neptune.DatabaseCluster(self, "GraphDatabase",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            instance_type=neptune.InstanceType.of(instance_type),
            iam_authentication=True,
            security_groups=[app_security_group]
        )

        self.cluster.apply_removal_policy(
            removal_policy
        )

        # self.graph_provider_function = lambda_.Function(self, 'GraphStoreProviderFunction',
        #     code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
        #         bundling=BundlingOptions(
        #             image=lambda_.Runtime.PYTHON_3_11.bundling_image,
        #             bundling_file_access=BundlingFileAccess.VOLUME_COPY,
        #             command=[
        #                 "bash", "-c", " && ".join([
        #                     "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
        #                     "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils"
        #                 ])
        #             ]
        #         )
        #     ),
        #     memory_size=256,
        #     runtime=lambda_.Runtime.PYTHON_3_11,
        #     architecture=lambda_.Architecture.X86_64,
        #     handler='multi_tenant_full_stack_rag_application.graph_store_provider.graph_store_provider.handler',
        #     timeout=Duration.seconds(60),
        #     environment={
        #         'AWS_ACCOUNT': self.account,
        #         'GRAPH_STORE_ENDPOINT': self.cluster.cluster_endpoint.socket_address,
        #         # 'GRAPH_STORE_PORT': self.cluster.cluster_endpoint.port
        #     }
        # )
        
        self.cluster.grant_connect(allowed_role.grant_principal) # Grant the role neptune-db:* access to the DB
        self.cluster.grant(allowed_role.grant_principal, "neptune-db:ReadDataViaQuery", "neptune-db:WriteDataViaQuery")

        ssm.StringParameter(self, 'NeptuneEndpointAddressParameter',
            string_value=self.cluster.cluster_endpoint.socket_address,
            parameter_name=f'/{parent_stack_name}/neptune_endpoint'
        )

        CfnOutput(self, 'NeptuneEndpointAddress', value=self.cluster.cluster_endpoint.socket_address)
