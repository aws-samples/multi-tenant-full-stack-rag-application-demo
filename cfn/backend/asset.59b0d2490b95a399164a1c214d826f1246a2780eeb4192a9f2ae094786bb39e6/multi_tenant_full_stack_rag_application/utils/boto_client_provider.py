#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os

region = os.getenv('AWS_REGION')

boto_config=None

 
class BotoClientProvider:
    @staticmethod
    def get_client(
        service_name: str, 
        region: str=region,
    ) -> boto3.client: 
        global boto_config
        if not boto_config:
            from botocore.config import Config
            boto_config = Config(retries={"max_attempts": 10, "mode": "adaptive"})
        # print(f"Getting client for service {service_name}")
        return boto3.client(service_name, region_name=region, config=boto_config)

