#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class IngestionStatusProviderEvent:
    # account_id: str=''
    # method: str=''
    # path: str=''
    operation: str=''
    user_id: str=''
    doc_id: str=''
    etag: str=''
    lines_processed: int=0
    progress_status: str=''
    origin: str=''

    def from_lambda_event(self, event):
        print(f"IngestionStatusProviderEvent.from_lambda_event: {event}")
        self.operation = event['operation']
        self.origin = event['origin']

        self.user_id = event['args']['user_id']
        self.doc_id = event['args']['doc_id']

        if self.operation == 'create_ingestion_status':
            self.etag = event['args']['etag']
            self.lines_processed = event['args']['lines_processed']
            self.progress_status = event['args']['progress_status']
        if 'delete_from_s3' in event['args']:
            self.delete_from_s3 = event['args']['delete_from_s3']
        else:
            self.delete_from_s3 = False
        return self

    def __str__(self):
        args = {
            "operation": self.operation,
            "origin": self.origin,
            "user_id": self.user_id,
            "doc_id": self.doc_id,
            "etag": self.etag,
            "lines_processed": self.lines_processed,
            "progress_status": self.progress_status,
            "delete_from_s3": self.delete_from_s3
        }

        return json.dumps(args)