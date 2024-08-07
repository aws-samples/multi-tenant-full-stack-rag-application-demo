#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
from constructs import Construct


class VpcStack(Stack):
    vpc: ec2.Vpc

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
    
        # create a vpc with 2 AZs
        self.vpc = ec2.Vpc(self, "Vpc", 
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                {
                    "cidrMask": 21,
                    "name": 'ingress',
                    "subnetType": ec2.SubnetType.PUBLIC,
                },
                {
                    "cidrMask": 21,
                    "name": 'application_egress',
                    "subnetType": ec2.SubnetType.PRIVATE_WITH_EGRESS,
                },
                {
                    "cidrMask": 21,
                    "name": 'data_isolated',
                    "subnetType": ec2.SubnetType.PRIVATE_ISOLATED,
                },
            ]
        )

        self.app_security_group = ec2.SecurityGroup(self, 'AppSecurityGroup', 
            vpc=self.vpc,
            allow_all_outbound=True
        )
        self.app_security_group.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.all_traffic()
        )

        # self.secretsmanager_vpce = self.vpc.add_interface_endpoint('SecretsManagerEndpoint',
        #     service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
        #     open=True,
        #     security_groups=[self.app_security_group],
        #     subnets=ec2.SubnetSelection(
        #         subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
        #     )
        # )
