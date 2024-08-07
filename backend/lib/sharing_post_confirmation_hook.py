#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    aws_lambda as lambda_,
)
from constructs import Construct


class SharingPostConfirmationHookStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        lambda_fn_arn: str,
        user_pool: cognito.UserPool,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lambda_fn = lambda_.Function.from_function_arn(
            self,
            'PostConfirmationLambda',
            lambda_fn_arn,
        )
        user_pool.add_trigger(
            cognito.UserPoolOperation.POST_CONFIRMATION,
            lambda_fn,
        )