#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    CfnOutput,
    Stack,
    aws_s3 as s3
)
from constructs import Construct


class BucketStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        resource_name, 
        add_cors: bool=False, 
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.bucket = s3.Bucket(self, resource_name)
        
        if (add_cors): 
            self.bucket.add_cors_rule(
                allowed_headers=["*"],
                allowed_methods=[
                    s3.HttpMethods.PUT,
                    s3.HttpMethods.GET,
                    s3.HttpMethods.POST,
                    s3.HttpMethods.DELETE,
                ],
                allowed_origins=["*"]
            )

        CfnOutput(self, resource_name + 'BucketName',
            value=self.bucket.bucket_name
        )