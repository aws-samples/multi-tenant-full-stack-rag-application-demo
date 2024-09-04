#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import (
    AttributeType, 
    BillingMode,
    StreamViewType, 
    Table, 
    TableProps
)
from aws_cdk.aws_ec2 import GatewayVpcEndpointAwsService, IVpc
from aws_cdk.aws_iam import AnyPrincipal, PolicyStatement
from aws_cdk.aws_kinesis import Stream, StreamMode
from aws_cdk.aws_ssm import StringParameter

import sys

# TODO VPC endpoint could be moved to a trigger function at the end
# to remove the dependency for the vpc here.
class DynamoDbTable(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        parent_stack_name: str,
        partition_key: str,
        partition_key_type: AttributeType,
        removal_policy: RemovalPolicy,
        resource_name: str,
        sort_key: str='',
        sort_key_type: AttributeType or '' = '',
        ssm_parameter_name: str='',
        **kwargs
    ) :
        super().__init__(scope, construct_id, **kwargs)
        kwargs = {
            "partition_key": {"name": partition_key, "type": partition_key_type},
            "billing_mode": BillingMode.PAY_PER_REQUEST,
            "removal_policy": removal_policy
        }

        if sort_key != '':
            kwargs["sort_key"] = {"name": sort_key, "type": sort_key_type}
        # if self.stream:
        #     kwargs["kinesis_stream"] = self.stream
        
        kwargs["stream"] = StreamViewType.NEW_IMAGE

        self.table = Table(self, resource_name, **kwargs)

        if ssm_parameter_name != '':
            table_param = StringParameter(self, f"{resource_name}-{ssm_parameter_name}",
                parameter_name=f"/{parent_stack_name}/{ssm_parameter_name}",
                string_value=self.table.table_name
            )
            table_param.apply_removal_policy(RemovalPolicy.DESTROY)

        
        # try: 
        #     dynamodb_endpoint = vpc.add_gateway_endpoint('DynamoDbEndpoint',
        #         service = GatewayVpcEndpointAwsService.DYNAMODB
        #     )
        # except Exception as e:
        #     # if we have more than one ddb table it will try to create this again,
        #     # but we only need one for the account & region, so catch it and 
        #     # keep going. If it's something else, exit.
        #     if e.args[0] != "Error: There is already a Construct with name 'DynamoDbEndpoint' in Vpc [Vpc]":
        #         print("Endpoint already exists or some other error occurred:")
        #         print(e.args[0])
        #         # sys.exit(1)

        