#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
from datetime import datetime
from uuid import uuid4

class ChatFeedback:
    def __init__(self, 
        user_id: str,
        chat_message_id: str,
        feedback_pos_msg='',
        feedback_neg_msg='',
        prompt='',
        feedback_id=uuid4().hex,
    ):
        self.user_id = user_id
        self.chat_message_id = chat_message_id
        self.feedback_id = feedback_id
        self.feedback_pos_msg = feedback_pos_msg
        self.feedback_neg_msg = feedback_neg_msg
        self.prompt = prompt
        self.created = datetime.now().isoformat()
    
    @staticmethod
    def from_ddb_record(rec):
        return {
            'user_id': rec['user_id']['S'],
            'chat_message_id': rec['chat_message_id']['S'],
            'created': rec['created']['S'],
            'feedback_id': rec['feedback_id']['S'],
            'feedback_neg_message': rec['feedback_neg_message']['S'],
            'feedback_pos_msg': rec['feedback_pos_msg']['S'],
            'prompt': rec['prompt']['S']
        }

    def to_ddb_record(self): 
        return {
            self.user_id: { 'S': self.user_id },
            self.chat_message_id:  { 'S': self.chat_message_id },
            self.created: { 'S': self.created },
            self.feedback_id: { 'S': self.feedback_id },
            self.feedback_neg_msg: { 'S': self.feedback_neg_msg },
            self.feedback_pos_msg: { 'S': self.feedback_pos_msg },
            self.prompt: { 'S': self.prompt }
        }

    def __dict__(self):
        return {
            'user_id': self.user_id,
            'chat_message_id': self.chat_message_id,
            'created': self.created,
            'feedback_id': self.feedback_id,
            'feedback_neg_message': self.feedback_neg_msg,
            'feedback_pos_msg': self.feedback_pos_msg,
            'prompt': self.prompt,
        }

    def __str__(self):
        return json.dumps({
            'user_id': self.user_id,
            'chat_message_id': self.chat_message_id,
            'created': self.created,
            'feedback_id': self.feedback_id,
            'feedback_neg_message': self.feedback_neg_msg,
            'feedback_pos_msg': self.feedback_pos_msg,
            'prompt': self.prompt,
        })
            
    
    def __eq__(self, obj):
        return self.user_id == obj.user_id and \
            self.chat_message_id == obj.chat_message_id and \
            self.created == obj.created and \
            self.feedback_id == obj.feedback_id and \
            self.feedback_neg_msg == obj.feedback_neg_msg and \
            self.feedback_pos_msg == obj.feedback_pos_msg and \
            self.prompt == obj.prompt
        
