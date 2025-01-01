#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0


import boto3
import json
import os

from datetime import datetime
from json import JSONEncoder

def _default(self, obj):
    if obj:
        return getattr(obj.__class__, "to_json", _default.default)(obj)
    else:
        return '{}'

_default.default = JSONEncoder.default  # Save unmodified default.
JSONEncoder.default = _default # Replace it.
s3 = boto3.client('s3')
ingestion_bucket = os.getenv('INGESTION_BUCKET')


class IngestionStatus:
    def __init__(self, 
        user_id: str, 
        doc_id: str, 
        etag: str, 
        lines_processed: int=0, 
        progress_status: str='', 
        # presigned_url: str='',
        last_modified=None
    ):
        self.user_id = user_id
        self.doc_id = doc_id
        self.etag = etag
        self.lines_processed = lines_processed
        self.progress_status = progress_status
        # if presigned_url:
        #     self.presigned_url = presigned_url
        # else:
        #     self.presigned_url = self.create_presigned_url({
        #         'user_id': {'S': user_id},
        #         'doc_id': {'S': doc_id}
        #     })

        if not last_modified:
            self.last_modified = datetime.now().isoformat() + 'Z'
        else:
            self.last_modified = last_modified

    def create_presigned_url(self, rec):
        return s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': ingestion_bucket,
                'Key': f"/private/{rec['user_id']['S']}/{rec['doc_id']['S']}"
            },
            # links time out in 20 minutes
            ExpiresIn=20 * 60
        )
    
    @staticmethod
    def from_ddb_record(rec):
        print(f"from_ddb_record got rec {rec}")
        lines_processed = rec['lines_processed']['N']
        if isinstance(lines_processed, str):
            if '.' in str(lines_processed):
                lines_processed = float(lines_processed)
            else:
                lines_processed = int(lines_processed)
        
        return IngestionStatus(
            rec['user_id']['S'],
            rec['doc_id']['S'],
            rec['etag']['S'],
            lines_processed,
            rec['progress_status']['S']
        )

    def to_ddb_record(self):     
        return {
            'user_id': {'S': self.user_id},
            'doc_id': {'S': self.doc_id},
            'etag': {'S': self.etag},
            'lines_processed': {'N': str(self.lines_processed)},
            'progress_status': {'S': self.progress_status},
            'last_modified': {'S': self.last_modified}
        }

    def to_json(self):
        print("Called ingestion_status.to_json()")
        return {
            'user_id': self.user_id,
            'doc_id': self.doc_id,
            'etag': self.etag,
            'lines_processed': self.lines_processed,
            'progress_status': self.progress_status,
            # 'presigned_url': self.presigned_url,
            'last_modified': self.last_modified,
        }

    def __str__(self):
        return json.dumps(self.to_json())

    def __eq__(self, other):
        # print(f"__eq__ received {self}, {other}")
        return self.user_id == other.user_id and \
            self.doc_id == other.doc_id and \
            self.etag == other.etag and \
            self.lines_processed == other.lines_processed and \
            self.progress_status == other.progress_status # and \
            # self.last_modified == other.last_modified


