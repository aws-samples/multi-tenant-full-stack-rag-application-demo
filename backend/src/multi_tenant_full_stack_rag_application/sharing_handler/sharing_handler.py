#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import json
import os

from multi_tenant_full_stack_rag_application.auth_provider.auth_provider import AuthProvider
from multi_tenant_full_stack_rag_application.auth_provider.auth_provider_factory import AuthProviderFactory
from multi_tenant_full_stack_rag_application.document_collections_handler import DocumentCollectionsHandler, DocumentCollectionsHandlerFactory
from multi_tenant_full_stack_rag_application.system_settings_provider.system_setting import SystemSetting
from multi_tenant_full_stack_rag_application.system_settings_provider.system_settings_provider import SystemSettingsProvider
from multi_tenant_full_stack_rag_application.system_settings_provider.system_settings_provider_factory import SystemSettingsProviderFactory
from multi_tenant_full_stack_rag_application.utils.utils import format_response
from .sharing_handler_event import SharingHandlerEvent
from .sharing_utils import user_add_collection, user_remove_collection
# initialize globals for the class and inputs so they 
# don't need to reinitialize on every call of handler
auth_provider = None
system_settings_provider = None
sharing_handler = None

""" 
API calls served by this function (via API Gateway):
DELETE /sharing/{collection_id}/{email}
GET /sharing/{collection_id}/{user_prefix}/{limit}/{last_eval_key}
POST /sharing 
    body = {
        "collection_id": str,
        "email": str
    }
"""

class SharingHandler:
    def __init__(self, 
        auth_provider: AuthProvider,
        document_collections_handler: DocumentCollectionsHandler,
        system_settings_provider: SystemSettingsProvider,
        ssm_client: boto3.client=None
    ): 
        self.auth_provider = auth_provider
        self.document_collections_handler = document_collections_handler
        self.ssm = boto3.client('ssm') if not ssm_client else ssm_client
        self.system_settings_provider = system_settings_provider
        origin_domain_name = self.ssm.get_parameter(
            Name='/multitenantrag/frontendOrigin'
        )['Parameter']['Value']
        self.frontend_origins = [
            f'https://{origin_domain_name}',
            'http://localhost:5173'
        ]

    def handler(self, event):   
        print(f"SharingHandler.lookup received event {event.__dict__()}")     
        if event.origin not in self.frontend_origins:
            print(f"Origin not allowed. Returning 403.")
            return format_response(403, {}, None)
        
        user_id = None
        status = 200
        if hasattr(event, 'auth_token') and event.auth_token is not None:
            user_id = self.auth_provider.get_userid_from_token(event.auth_token)
            event.user_id = user_id

        if event.method != 'OPTIONS' and user_id == None:
            status = 403
            result = {"error": "forbidden"}

        elif event.method == 'OPTIONS':
            result = {}

        elif event.method == 'GET' and event.path.startswith('/sharing/'):
            user_prefix = event.user_prefix
            if not len(user_prefix) >= 4:
                raise Exception('user_prefix must be at least 4 characters')
            collection = self.document_collections_handler.get_doc_collection(user_id, collection_id)
            settings = self.system_settings_provider.get_system_settings('user_by_email', user_prefix, event.limit, event.last_eval_key)
            settings = self.system_settings_provider.settings_to_list(settings)
            print(f"SharingHandler.lookup retrieved settings {settings}")
            final_settings = []
            for i in range(len(settings)):
                setting = settings[i]
                if not (setting['sort_key'] == event.user_email or \
                    setting['sort_key'] in collection.shared_with):
                    final_settings.append(setting)
            result = final_settings
        
        elif event.method == 'POST' and event.path == '/sharing':
            doc_collection = self.document_collections_handler.get_doc_collection(user_id, event.collection_id)
            doc_collection.shared_with.append(event.shared_with_email)
            print(f"SharingHandler.lookup updating doc_collection {doc_collection}")
            collection = self.document_collections_handler.upsert_doc_collection(doc_collection, event)
            print(f"got updated doc collections {collection}")
            users_result = self.system_settings_provider.get_system_settings('user_by_email', event.shared_with_email)
            if isinstance(users_result, list) and len(users_result) > 0:
                shared_with_user = users_result[0]
                shared_by_user = self.system_settings_provider.get_system_settings('user_by_id', event.user_id)[0]
                user_add_collection(doc_collection, shared_with_user, shared_by_user)
            
            result = self.document_collections_handler.collections_to_dict(collections)

        elif event.method == 'DELETE' and event.path.startswith('/sharing/'):
            doc_collection = self.document_collections_handler.get_doc_collection(user_id, event.collection_id)
            doc_collection.shared_with.remove(event.shared_with_email)
            print(f"SharingHandler.lookup updating doc_collection {doc_collection}")
            collection = self.document_collections_handler.upsert_doc_collection(doc_collection, event)
            users_result = self.system_settings_provider.get_system_settings('user_by_email', event.shared_with_email)
            if isinstance(users_result, list) and len(users_result) > 0:
                removed_from_user  = users_result[0]
                user_remove_collection(doc_collection.collection_id, removed_from_user)
            result = collections[0].shared_with

        print(f"SharingHandler.lookup returning {result}")
        return format_response(status, result, event.origin)


def handler(event, context):
    global auth_provider, document_collections_handler, sharing_handler, system_settings_provider
    print(f"handler received event {event}")
    event = SharingHandlerEvent().from_lambda_event(event)
    print(f"Converted event {event.__dict__()}")
    if not sharing_handler:
        initialize()
    return sharing_handler.handler(event)


# this is the handler for the ingestion event that is called
# by the cognito post-confirmation hook when a new user is created.
# def handler_post_confirmation_add_user(event, context):
#     global sharing_handler, system_settings_provider
#     print(f"user lookup handler post_confirmation_add_user got event {event}")
#     email = event['request']['userAttributes']['email']
#     if not sharing_handler:
#         initialize()
#     response = system_settings_provider.set_system_setting(
#         SystemSetting(
#             'user_by_email',
#             email
#         )
#     )
#     print(f"Got response {response}")
#     return event


# def handler_post_delete_remove_user(event, context):
#     return 'Temp result'


def initialize():
    global auth_provider, document_collections_handler, sharing_handler, system_settings_provider
    if not sharing_handler:
        system_settings_provider = SystemSettingsProviderFactory.get_system_settings_provider()
        document_collections_handler = DocumentCollectionsHandlerFactory.get_document_collections_handler()
        auth_provider = AuthProviderFactory.get_auth_provider()
        sharing_handler = SharingHandler(
            auth_provider,
            document_collections_handler,
            system_settings_provider
        )

if __name__=='__main__':
    with open('test_event.json', 'r') as f:
        event = json.load(f)
    result = handler(event, {})
    print(f"Got result {result}")