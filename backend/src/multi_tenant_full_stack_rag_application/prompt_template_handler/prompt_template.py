#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
from datetime import datetime
from uuid import uuid4


class PromptTemplate:
    def __init__(self,
        user_id: str, 
        user_email: str,
        template_name: str,
        template_text: str,
        model_ids: [str],
        stop_sequences: [str] = [],
        template_id: str=None,
        created_date: str=None, 
        updated_date: str=None
    ):
        self.user_id = user_id
        self.sort_key = f"template::{template_name}"
        self.user_email = user_email
        self.template_name = template_name
        self.template_text = template_text
        self.model_ids = model_ids
        self.stop_sequences = stop_sequences
        self.template_id = template_id if template_id else uuid4().hex       
        now = datetime.now().isoformat() + 'Z'
        self.created_date = created_date if created_date else now
        self.updated_date = updated_date if updated_date else now

    @staticmethod
    def from_ddb_record(rec):
        stop_seqs = []
        if 'stop_sequences' in rec:
            stop_seqs = rec['stop_sequences']['SS']

        template = PromptTemplate(
            rec['user_id']['S'], 
            rec['user_email']['S'],
            rec['template_name']['S'], 
            rec['template_text']['S'],
            rec['model_ids']['SS'], 
            stop_seqs,
            rec['template_id']['S'], 
            rec['created_date']['S'],
            rec['updated_date']['S']
        )
        return template

    def to_ddb_record(self): 
        rec = {
            'user_id': {'S': self.user_id},
            'sort_key': {'S': self.sort_key},
            'user_email': {'S': self.user_email},
            'template_id': {'S': self.template_id},
            'template_name': {'S': self.template_name},
            'template_text': {'S': self.template_text},
            'model_ids': {'SS': self.model_ids},
            'created_date': {'S': self.created_date},
            'updated_date': {'S': self.updated_date}
        }
        
        if hasattr(self, 'stop_sequences') and \
            len(self.stop_sequences) > 0:
            rec['stop_sequences']: {'SS': self.stop_sequences}
        return rec

    def __dict__(self):
        stop_seqs = []
        if hasattr(self, 'stop_sequences') and \
            isinstance(self.stop_sequences, list) and \
            len(self.stop_sequences) > 0:
            stop_seqs = self.stop_sequences
        # print(f"stop_seqs = {stop_seqs}")
        return {
            'user_id': self.user_id,
            'user_email': self.user_email,
            'sort_key': self.sort_key,
            'template_id': self.template_id,
            'template_name': self.template_name,
            'template_text': self.template_text,
            'model_ids': self.model_ids,
            'stop_sequences': stop_seqs,
            'created_date': self.created_date,
            'updated_date': self.updated_date
        }

    def __str__(self):
        template_id = ''
        if hasattr(self, 'template_id'):
            template_id = self.template_id

        return json.dumps({
            'user_id': self.user_id,
            'sort_key': self.sort_key,
            'user_email': self.user_email,
            'template_id': template_id,
            'template_name': self.template_name,
            'template_text': self.template_text,
            'model_ids': self.model_ids,
            'stop_sequences': self.stop_sequences,
            'created_date': self.created_date,
            'updated_date': self.updated_date
        })
    
    def __eq__(self, obj):
        return self.user_id == obj.user_id and \
            self.user_email == obj.user_email and \
            self.template_id == obj.template_id and \
            self.template_name == obj.template_name and \
            self.template_text == obj.template_text and \
            self.model_ids == obj.model_ids and \
            self.stop_sequences == obj.stop_sequences and \
            self.created_date == obj.created_date and \
            self.updated_date == obj.updated_date