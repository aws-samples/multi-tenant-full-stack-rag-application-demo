#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
from botocore.config import Config

region = os.getenv('AWS_REGION')
config = Config(retries={"max_attempts": 10, "mode": "adaptive"})

class BotoClientProvider:
    @staticmethod
    def get_client(
        service_name: str, 
        region: str=region,
        config: Config=config
    ) -> boto3.client: 
        print(f"Getting client for service {service_name}")
        return boto3.client(service_name, region_name=region, config=config)

