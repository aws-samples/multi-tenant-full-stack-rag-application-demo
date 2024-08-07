#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
from datetime import datetime

from multi_tenant_full_stack_rag_application.memory_provider import ChatFeedback
class ChatMessage:
    def __init__(self, 
        user_id: str,
        conversation_id: str,
        human_message: str, 
        bot_message: str, 
        model_id: str, 
        prompt_template_id: str, 
        message_num: int=0,
        feedback: ChatFeedback = None
    ):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.human_message = human_message
        self.ai_message = ai_message
        self.feedback = feedback
        self.created = datetime.now().isoformat()
        self.model_id = model_id
        self.prompt_template_id = prompt_template_id
        self.message_num = message_num
        self.message_id = f"{conversation_id}:{message_num}"


    @staticmethod
    def from_ddb_record(rec):
        return {
            'user_id': rec['user_id']['S'],
            'conversation_id': rec['conversation_id']['S'],
            'message_id': rec['message_id']['S'],
            'created': rec['created']['S'],
            'feedback_id': rec['feedback_id']['S'],
            'feedback_neg_message': rec['feedback_neg_message']['S'],
            'feedback_pos_msg': rec['feedback_pos_msg']['S'],
            'prompt': rec['prompt']['S']
        }

    def to_ddb_record(self): 
        return {
            self.user_id: { 'S': self.user_id },
            self.created: { 'S': self.created },
            self.feedback_id: { 'S': self.feedback_id },
            self.feedback_neg_msg: { 'S': self.feedback_neg_msg },
            self.feedback_pos_msg: { 'S': self.feedback_pos_msg },
            self.prompt: { 'S': self.prompt }
        }

    def __dict__(self):
        return {
            'user_id': self.user_id,
            'created': self.created,
            'feedback_id': self.feedback_id,
            'feedback_neg_message': self.feedback_neg_msg,
            'feedback_pos_msg': self.feedback_pos_msg,
            'prompt': self.prompt,
        }

    def __str__(self):
        return json.dumps({
            'user_id': self.user_id,
            'created': self.created,
            'feedback_id': self.feedback_id,
            'feedback_neg_message': self.feedback_neg_msg,
            'feedback_pos_msg': self.feedback_pos_msg,
            'prompt': self.prompt,
        })
            
    
    def __eq__(self, obj):
        return self.user_id == obj.user_id and \
            self.created == obj.created and \
            self.feedback_id == obj.feedback_id and \
            self.feedback_neg_msg == obj.feedback_neg_msg and \
            self.feedback_pos_msg == obj.feedback_pos_msg and \
            self.prompt == obj.prompt
        
