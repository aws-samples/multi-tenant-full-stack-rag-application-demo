#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
from datetime import datetime
from uuid import uuid4


class ChatConversation:
    def __init__(self,
        user_id: str, 
        conversation_name: str, 
        messages: [dict], 
        conversation_id: str=None, 
        created_date: str=None, 
    ):
        self.user_id = user_id
        self.conversation_name = conversation_name
        self.messages = messages
        self.conversation_id = conversation_id if conversation_id else uuid4().hex
        now = datetime.now().isoformat() + 'Z'
        self.created_date = created_date if created_date else now

    @staticmethod
    def from_ddb_record(user_id, rec):
        return ChatConversation(
            rec['user_id']['S'],
            rec['conversation_name']['S'],
            rec['messages']['L']
        )
        
        for conversation_name in rec:
            conversation_rec = rec[conversation_name]['M']
            msgs = []
            rec_msgs = conversation_rec['messages']['L']
            for rec_msg in rec_msgs:
                for key in rec_msgs:
                    rec_msg = rec_msgs[key]
                    msgs.append({
                        ""
                    })
            conversations.append(Conversation(
                user_id, conversation_name, 
                conversation['messages']['L'],
                conversation['conversation_id']['S'], 
                conversation['created_date']['S'],
                conversation['updated_date']['S']
            ))
        return conversations

    @staticmethod
    def messages_to_list(messages):
        print(f"messages_to_dict got messages {messages}")
        final_messages= {}
        for message_id in messages:
            message = messages[message_id]
            if isinstance(message, ChatMessage):
                message = message.__dict__()
            print(f"message is now {message}, type {type(message)}")
            final_messages[message_id] = message
        return final_messages

    def to_ddb_record(self): 
        # self.user_id = user_id
        # self.conversation_name = conversation_name
        # self.messages = messages
        # self.conversation_id = conversation_id if conversation_id else uuid4().hex
        # now = datetime.now().isoformat() + 'Z'
        # self.created_date = created_date if created_date else now
        messages = self.messages_to_list(self.messages)
        for i in range(len(messages)):
            messages[i] = messages[i].to_ddb_record()

        return {
            'user_id': {'S': self.user_id},
            'conversation_name': {'S': self.conversation_name},
            'conversation_id': {'S': self.conversation_id},
            'messages': {'L': messages},
            'created_date': {'S': self.created_date},
        }

    # def toJson(self):
    #     return json.dumps(self, default=lambda o: o.__dict__)
    def __dict__(self):
        return {
            'user_id': self.user_id,
            'collection_id': self.collection_id,
            'collection_name': self.collection_name,
            'description': self.description,
            'vector_db_type': self.vector_db_type,
            'created_date': self.created_date,
            'updated_date': self.updated_date
        }

    def __str__(self):
        return json.dumps({
            'user_id': self.user_id,
            'collection_id': self.collection_id,
            'collection_name': self.collection_name,
            'description': self.description,
            'vector_db_type': self.vector_db_type,
            'created_date': self.created_date,
            'updated_date': self.updated_date
        })
    
    def __eq__(self, obj):
        return self.user_id == obj.user_id and \
            self.collection_id == obj.collection_id and \
            self.collection_name == obj.collection_name and \
            self.description == obj.description and \
            self.vector_db_type == obj.vector_db_type and \
            self.created_date == obj.created_date and \
            self.updated_date == obj.updated_date