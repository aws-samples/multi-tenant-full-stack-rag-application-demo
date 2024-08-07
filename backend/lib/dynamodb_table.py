#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import Stack
from aws_cdk.aws_dynamodb import (
    AttributeType, 
    BillingMode, 
    Table, 
    TableProps
)
from aws_cdk.aws_ec2 import GatewayVpcEndpointAwsService, IVpc
from aws_cdk.aws_iam import AnyPrincipal, PolicyStatement
from aws_cdk.aws_kinesis import Stream, StreamMode

import sys


class DynamoDbTableStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        partition_key: str,
        partition_key_type: AttributeType,
        resource_name: str,
        vpc: IVpc,
        sort_key: str,
        sort_key_type: AttributeType or '' = '',
        create_stream: bool = False,
        **kwargs
    ) :
        super().__init__(scope, construct_id, **kwargs)
        
        self.stream = None
        if create_stream:
            self.stream = Stream(self, 'Stream',
                stream_mode=StreamMode.ON_DEMAND
            )

        kwargs = {
            "partition_key": {"name": partition_key, "type": partition_key_type},
            "billing_mode": BillingMode.PAY_PER_REQUEST
        }

        if sort_key != '':
            kwargs["sort_key"] = {"name": sort_key, "type": sort_key_type}
        if self.stream:
            kwargs["kinesis_stream"] = self.stream
            
        self.table = Table(self, resource_name, **kwargs)

        try: 
            dynamodb_endpoint = vpc.add_gateway_endpoint('DynamoDbEndpoint',
                service = GatewayVpcEndpointAwsService.DYNAMODB
            )
        except Exception as e:
            # if we have more than one ddb table it will try to create this again,
            # but we only need one for the account & region, so catch it and 
            # keep going. If it's something else, exit.
            if e.args[0] != "Error: There is already a Construct with name 'DynamoDbEndpoint' in Vpc [Vpc]":
                print("Endpoint already exists or some other error occurred:")
                print(e.args[0])
                sys.exit(1)

        