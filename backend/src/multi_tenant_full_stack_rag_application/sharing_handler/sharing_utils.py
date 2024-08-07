#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from multi_tenant_full_stack_rag_application.document_collections_handler import DocumentCollection
from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSetting

def user_add_collection(collection: DocumentCollection, shared_with_user: SystemSetting, shared_by_user: SystemSetting):
    print(f"user_add_collection got {collection}, {shared_with_user}, {shared_by_user}")
    collections_enabled = {}
    if not hasattr(shared_with_user, 'data'):
        shared_with_user.data = {}
    if 'document_collections_enabled' in shared_with_user.data:
        collections_enabled = shared_with_user.data['document_collections_enabled']
    # if 'document_collections_enabled' not in user.data:
    #     user.data['document_collections_enabled'] = {}
    print(f"shared_with_user.data is now {shared_with_user.data}")
    print(f"shared_by_user is now {shared_by_user}")
    print(f"collections_enabled = {collections_enabled}")
    if collection.collection_id not in list(collections_enabled.keys()):
        collections_enabled[collection.collection_id] = {
            "collection_name": {"S": collection.collection_name},
            "description": {"S": collection.description},
            "shared_by_userid": {"S": shared_by_user.sort_key},
            "shared_by_email": {"S": shared_by_user.data['user_email']},
        }
        print(f"collections_enabled = {collections_enabled}")
    shared_with_user.data['document_collections_enabled'] = collections_enabled
    return shared_with_user

def user_remove_collection(collection_id, user):
    if isinstance(user, dict):
        print("User passed in is dict. Converting to SystemSetting")
        user = SystemSetting(**user)
    if not hasattr(user, 'data'):
        print("User system setting doesn't have a data attribute. Returning.")
        return user
    if 'document_collections_enabled' not in user.data:
        print("No document_collections_enabled in user.data. Returning.")
        return user
    if collection_id in list(user.data['document_collections_enabled'].keys()):
        print(f"Deleting {collection_id} from user.data['document_collections_enabled]")
        del user.data['document_collections_enabled'][collection_id]
    else:
        print(f"Couldn't find {collection_id} in {user.data['document_collections_enabled']}")
    return user