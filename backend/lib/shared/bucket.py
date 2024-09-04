#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    CfnOutput,
    NestedStack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_ssm as ssm,
)
from constructs import Construct


class Bucket(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        resource_name, 
        add_cors: bool=False, 
        *,
        parent_stack_name: str,
        removal_policy: str,
        ssm_parameter_name: str=None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.bucket = s3.Bucket(self, resource_name,
            removal_policy=RemovalPolicy(
                removal_policy
            )
        )

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
        self.ssm_param_bucket_name = ssm.StringParameter(
            self, 'SSMBucketName',
            parameter_name=f"/{parent_stack_name}/{ssm_parameter_name}",
            string_value=self.bucket.bucket_name
        )
        self.ssm_param_bucket_name.apply_removal_policy(RemovalPolicy.DESTROY)
        
        CfnOutput(self, resource_name + 'BucketName',
            value=self.bucket.bucket_name
        )