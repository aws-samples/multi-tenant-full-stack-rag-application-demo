#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
from datetime import datetime


class DocumentCollectionShare:
    def __init__(self,
        collection_id: str,
        share_with_user_email: str,
        created_date: str = None
    ):
        self.collection_id = collection_id
        self.share_with_user_email = share_with_user_email
        self.sort_key = f"collection_share::{collection_id}"
        self.created_date = created_date if \
            created_date else \
            datetime.now().isoformat() + 'Z'

    @staticmethod
    def from_ddb_record(rec):
        return DocumentCollectionShare(
            rec['collection_id']['S'],
            rec['share_with_user_email']['S'],
            rec['created_date']['S'] 
        )

    @staticmethod
    def to_ddb_record():
        record = {
            'collection_id': {'S': self.collection_id},
            'partition_key': {'S': self.share_with_user_email},
            'sort_key': {'S': self.sort_key},
            'created_date': {'S': self.created_date}
        }

    