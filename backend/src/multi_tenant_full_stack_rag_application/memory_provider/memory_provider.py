#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from multi_tenant_full_stack_rag_application.user_settings_provider import UserSetting, UserSettingsProvider, UserSettingsProviderFactory
from .chat_message import ChatMessage
from .chat_conversation import ChatConversation
from .chat_feedback import ChatFeedback


class MemoryProvider:
    def __init__(self,
        user_settings_provider: UserSettingsProvider,
    ):
        self.user_settings_provider = user_settings_provider
    
    def save_conversation(self, conversation: ChatConversation):
        sort_key = f"conversation:{conversation.conversation_id}"
        user_setting = UserSetting(
            user_id,
            sort_key,
            data={

            }
        )
        self.user_settings_provider.set_user_setting()
        pass

    def get_conversation(self, user_id: str, conversation_id: str) -> ChatConversation:

        return ChatConversation(
            user_id,
            conversation_id,
            messages=[],
            feedback=None,
        )

    