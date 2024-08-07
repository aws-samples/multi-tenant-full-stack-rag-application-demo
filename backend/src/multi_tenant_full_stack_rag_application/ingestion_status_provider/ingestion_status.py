#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
from datetime import datetime


class IngestionStatus:
    def __init__(self, user_id: str, s3_key: str, etag: str, 
        lines_processed: int=0, progress_status: str=''):
        self.user_id = user_id
        self.s3_key = s3_key
        self.etag = etag
        self.lines_processed = lines_processed
        self.progress_status = progress_status
        self.last_modified = datetime.now().isoformat() + 'Z'

    @staticmethod
    def from_ddb_record(rec):
        lines_processed = rec['lines_processed']['N']
        if '.' in lines_processed:
            lines_processed = float(lines_processed)
        else:
            lines_processed = int(lines_processed)

        return IngestionStatus(
            rec['user_id']['S'],
            rec['s3_key']['S'],
            rec['etag']['S'],
            lines_processed,
            rec['progress_status']['S']
        )

    def to_ddb_record(self):     
        return {
            'user_id': {'S': self.user_id},
            's3_key': {'S': self.s3_key},
            'etag': {'S': self.etag},
            'lines_processed': {'N': str(self.lines_processed)},
            'progress_status': {'S': self.progress_status},
            'last_modified': {'S': self.last_modified}
        }

    def __dict__(self):
        return {
            'user_id': self.user_id,
            's3_key': self.s3_key,
            'etag': self.etag,
            'lines_processed': self.lines_processed,
            'progress_status': self.progress_status,
            'last_modified': self.last_modified,
        }

    def __str__(self):
        return json.dumps(self.__dict__())

    def __eq__(self, other):
        print(f"__eq__ received {self}, {other}")
        return self.user_id == other.user_id and \
            self.s3_key == other.s3_key and \
            self.etag == other.etag and \
            self.lines_processed == other.lines_processed and \
            self.progress_status == other.progress_status and \
            self.last_modified == other.last_modified


