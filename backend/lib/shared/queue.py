#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Duration,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_ssm as ssm,
    aws_sqs as sqs,
)
from constructs import Construct
from .bucket_to_queue_event_trigger import BucketToQueueNotificationStack

class QueueStack(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        resource_name: str, 
        visibility_timeout: Duration.minutes, 
        bucket_name: str=None,
        ssm_parameter_name: str=None,
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
        if bucket_name:
            self.ingestion_event_trigger = BucketToQueueNotificationStack(self, 'IngestionBucketToQueueTriggerStack', 
                bucket_name=bucket_name,
                queue=self.queue,
                resource_name='IngestionEventTrigger'
            )
        
        if ssm_parameter_name:
            queue_param = ssm.StringParameter(self, f'{resource_name}QueueUrlSsmParameter',
                parameter_name=f'/{parent_stack_name}/ssm_parameter_name',
                string_value=self.queue.queue_url
            )
            queue_param.apply_removal_policy(RemovalPolicy.DESTROY)