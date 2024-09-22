#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
from datetime import datetime
from json import JSONEncoder

def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)

_default.default = JSONEncoder.default  # Save unmodified default.
JSONEncoder.default = _default # Replace it.


class IngestionStatus:
    def __init__(self, user_id: str, doc_id: str, etag: str, 
        lines_processed: int=0, progress_status: str='', last_modified=None):
        self.user_id = user_id
        self.doc_id = doc_id
        self.etag = etag
        self.lines_processed = lines_processed
        self.progress_status = progress_status
        if not last_modified:
            self.last_modified = datetime.now().isoformat() + 'Z'
        else:
            self.last_modified = last_modified

    @staticmethod
    def from_ddb_record(rec):
        lines_processed = rec['lines_processed']['N']
        if '.' in lines_processed:
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
        # print("Called ingestion_status.to_json()")
        return {
            'user_id': self.user_id,
            'doc_id': self.doc_id,
            'etag': self.etag,
            'lines_processed': self.lines_processed,
            'progress_status': self.progress_status,
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


