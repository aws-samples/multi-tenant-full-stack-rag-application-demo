#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk.aws_lambda import EventSourceMapping, Function
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk.aws_sqs import Queue

class QueueToFunctionTrigger(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        function: Function,
        queue_arn: str,
        resource_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        queue = Queue.from_queue_arn(self, resource_name, queue_arn)
        ingestion_queue_notification = SqsEventSource(queue)
        lambda_sqs_evt_source = EventSourceMapping(self, f'{resource_name}EventSource',
            target=function,
            batch_size=1,
            enabled=True,
            event_source_arn=queue_arn
        )

        queue.grant_consume_messages(function.grant_principal)