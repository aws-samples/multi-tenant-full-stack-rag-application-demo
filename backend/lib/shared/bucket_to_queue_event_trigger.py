#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk.aws_s3 import Bucket, EventType, IBucket, NotificationKeyFilter
from aws_cdk.aws_s3_notifications import SqsDestination
from aws_cdk.aws_sqs import ( IQueue  )

class BucketToQueueNotification(Construct):
    def __init__(self, scope: Construct, construct_id: str, 
        bucket_name: str,
        queue: IQueue,
        resource_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = Bucket.from_bucket_name(self, resource_name, bucket_name)
        notification = SqsDestination(queue)
        bucket.add_event_notification(
            EventType.OBJECT_CREATED,
            notification,
            NotificationKeyFilter(
                prefix='private'
            )
        )
        bucket.add_event_notification(
            EventType.OBJECT_REMOVED,
            notification,
            NotificationKeyFilter(
                prefix='private'
            )
        )
