#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_sqs as sqs,
)
from constructs import Construct


class QueueStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        resource_name: str, 
        visibility_timeout: Duration.minutes, 
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.dlq = sqs.Queue(self, f'{resource_name}DLQ')
        self.queue = sqs.Queue(self, resource_name,
            visibility_timeout=visibility_timeout,
            dead_letter_queue=sqs.DeadLetterQueue(
                queue=self.dlq,
                max_receive_count=2
            )
        )
        self.queue.grant_send_messages(iam.ServicePrincipal('s3.amazonaws.com'))
