#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    CfnOutput,
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
                # Comment out the entire next block if you don't want
                # public subnets, and then search the code under
                # backend/lib for CHANGE_PUBLIC_SUBNET_TO_ISOLATED,
                # and change the other ones to ec2.SubnetType.PRIVATE_ISOLATED
                {
                    "cidrMask": 21,
                    "name": 'ingress',
                    "subnetType": ec2.SubnetType.PUBLIC,
                },
                # comment out above here but not below.
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

        self.ssm_endpoint = self.vpc.add_interface_endpoint(
            "SsmEndpoint",
            private_dns_enabled=True,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.ssm",
                443
            ),
            subnets=ec2.SubnetSelection(
                # availability_zones=[f"{self.region}a", f"{self.region}b"],
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )
        CfnOutput(self, 'SsmVpcEndpoint', value=self.ssm_endpoint.vpc_endpoint_id)

        self.dynamodb_endpoint = self.vpc.add_gateway_endpoint('DynamoDbEndpoint',
            service = ec2.GatewayVpcEndpointAwsService.DYNAMODB
        )

        CfnOutput(self, 'DynamoDbVpcEndpoint', value=self.dynamodb_endpoint.vpc_endpoint_id)

        self.kms_endpoint = self.vpc.add_interface_endpoint(
            "KmsEndpoint",
            private_dns_enabled=True,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.kms",
                443
            ),
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )

        self.bedrock_endpoint = self.vpc.add_interface_endpoint(
            "BedrockEndpoint",
            private_dns_enabled=True,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.bedrock",
                443
            ),
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )

        self.bedrock_agent_endpoint = self.vpc.add_interface_endpoint(
            "BedrockAgentEndpoint",
            private_dns_enabled=True,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.bedrock-agent",
                443
            ),
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )

        self.bedrock_agent_runtime_endpoint = self.vpc.add_interface_endpoint(
            "BedrockAgentRuntimeEndpoint",
            private_dns_enabled=True,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.bedrock-agent-runtime",
                443
            ),
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )

        self.bedrock_runtime_endpoint = self.vpc.add_interface_endpoint(
            "BedrockRuntimeEndpoint",
            private_dns_enabled=True,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.bedrock-runtime",
                443
            ),
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )
        