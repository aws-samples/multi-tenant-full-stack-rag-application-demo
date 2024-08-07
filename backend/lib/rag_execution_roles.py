#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_iam as iam
)
from constructs import Construct

class RagExecutionRolesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.ingestion_role = iam.Role(self, 'IngestionFunctionRole', 
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )
        # self.ingestion_role.add_to_policy(iam.PolicyStatement(
        #     actions=['es:*', 'aoss:*', 'bedrock:*', 'kendra:*'],
        #     resources=['*'],
        #     effect=iam.Effect.ALLOW
        # ))
        self.ingestion_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, 
                'IngestionFunctionVpcPolicy',
                'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole'
            )
        )
        self.ingestion_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['cognito-identity:GetId'],
            resources=['*']
        ))

        self.inference_role = iam.Role(self, 'InferenceFunctionRole', 
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )
        # self.inference_role.add_to_policy(iam.PolicyStatement(
        #     actions=['es:*', 'aoss:*', 'bedrock:*', 'kendra:*'],
        #     resources=['*'],
        #     effect=iam.Effect.ALLOW
        # ))
        self.inference_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, 
                'InferenceFunctionVpcPolicy',
                'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole'
            )
        )