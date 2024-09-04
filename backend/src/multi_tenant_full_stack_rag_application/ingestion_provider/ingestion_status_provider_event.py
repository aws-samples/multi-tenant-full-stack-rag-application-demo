#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class IngestionStatusProviderEvent:
    method: str=''
    user_id: str=''
    doc_id: str=''
    etag: str=''
    lines_processed: int=0
    progress_status: str=''

    def from_lambda_event(self, event):
        print(f"IngestionStatusProviderEvent.from_lambda_event: {event}")
        self.method = event['method']
        self.user_id = event['user_id']
        self.doc_id = event['doc_id']
        if 'etag' in event:
            self.etag = event['etag']
        if 'lines_processed' in event:
            self.lines_processed = event['lines_processed'] if 'lines_processed' in event else 0
        if 'progress_status' in event:
            self.progress_status = event['progress_status'] if 'progress_status' in event else ''
        return self

    def __str__(self):
        args = {
            "method": self.method,
            "user_id": self.user_id,
            "doc_id": self.doc_id,
            "etag": self.etag,
            "lines_processed": self.lines_processed,
            "progress_status": self.progress_status
        }
        return json.dumps(args)