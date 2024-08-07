#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    CfnOutput,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_neptune_alpha as neptune
)


class NeptuneStack(Stack):
    def __init__(self, scope, id, 
        app_security_group: ec2.ISecurityGroup,
        inference_role_arn: str,
        ingestion_role_arn: str,
        instance_type: neptune.InstanceType.T4_G_MEDIUM,
        vpc: ec2.IVpc,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)
    
        ingestion_role_ptr = iam.Role.from_role_arn(self, "IngestionRole", ingestion_role_arn)
        inference_role_ptr = iam.Role.from_role_arn(self, "InferenceRole", inference_role_arn)

        self.cluster = neptune.DatabaseCluster(self, "GraphDatabase",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            instance_type=instance_type,
            iam_authentication=True,
            security_groups=[app_security_group]
        )
        self.cluster.grant_connect(ingestion_role_ptr) # Grant the role neptune-db:* access to the DB
        self.cluster.grant(ingestion_role_ptr, "neptune-db:ReadDataViaQuery", "neptune-db:WriteDataViaQuery")
        self.cluster.grant_connect(inference_role_ptr) # Grant the role neptune-db:* access to the DB
        self.cluster.grant(inference_role_ptr, "neptune-db:ReadDataViaQuery")
        role = iam.Role(self, "NeptuneUserRole", assumed_by=iam.AccountPrincipal(self.account))
        self.cluster.grant_connect(role) # Grant the role neptune-db:* access to the DB
        self.cluster.grant(role, "neptune-db:ReadDataViaQuery", "neptune-db:WriteDataViaQuery")

        CfnOutput(self, 'NeptuneEndpointAddress', value=self.cluster.cluster_endpoint.socket_address)