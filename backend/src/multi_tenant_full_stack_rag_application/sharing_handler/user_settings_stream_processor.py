#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

# This processor manages changes to the user settings table for the sharing handler.
# Here are the possible changes in the UserSettings table that are currently being 
# monitored, and the actions taken
# 
# setting_name = 'document_collections'
# data is a map of all of a user's document collections, with the keys to the map
# being the collection name, and the values being the metadata about the collection
# including collection id, collection name, creation and updated date, description, 
# and the list of users it's shared with.abs
#   Change:                         Action:
#   ddb record deleted entirely     record delete only happens when a user's last
#                                   document collection is deleted. Do the ssame thing
#                                   as a single doc collection deletion.
#   delete single doc collection.   loop through shared_with users and delete doc
#                                   collection from all of their system settings.
#   add user to doc collection      loop through old shared_with users. remove them 
#                                   from list of new shared_with users. Any left in 
#                                   new list were just added. Add to their system setting.
#   remove user from collection.    while looping through old users, if they're not
#                                   in new shared_with users, remove the collection
#                                   from their user record in system settings. If there 
#                                   is no shared_with in the system setting anymore,
#.                                  Then any users in the old share_with should be 
#                                   removed from the system setting.


import base64
import boto3
import json
import os

from aws_kinesis_agg.deaggregator import deaggregate_records

from multi_tenant_full_stack_rag_application.boto_client_provider import BotoClientProvider
from multi_tenant_full_stack_rag_application.document_collections_handler import DocumentCollection, DocumentCollectionsHandler, DocumentCollectionsHandlerFactory
from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSetting, SystemSettingsProvider, SystemSettingsProviderFactory
from multi_tenant_full_stack_rag_application.utils import format_response
from .sharing_utils import user_add_collection, user_remove_collection

ddb = None
kinesis = None
system_settings_provider: SystemSettingsProvider = None


def decode_payload(enc_payload):
    return base64.b64decode(enc_payload).strip()


def handler(event, context):
    global ddb, kinesis, system_settings_provider

    print(f"Handler received event {event}")
    if ddb is None:
        ddb = BotoClientProvider.get_client('dynamodb')
        kinesis = BotoClientProvider.get_client('kinesis')
        system_settings_provider = SystemSettingsProviderFactory.get_system_settings_provider()
    records = deaggregate_records(event["Records"])
    status = 200
    results = []
    for record in records:
        print(f"Got record {record}")
        enc_payload = record["kinesis"]["data"]
        payload = decode_payload(enc_payload)
        rec = json.loads(payload)
        print(f"decoded payload: {rec.keys()}")
        print(f"{rec}")
        if rec["dynamodb"]["Keys"]["setting_name"]["S"] == "document_collections":
            # on create, a user's document collections record setting will never have a sharing list yet.
            # we only need to modifications to the doc collection's sharing list or deletion of the
            # document collection entirely. 
            shared_by_userid = rec["dynamodb"]["Keys"]["user_id"]["S"]
            shared_by_user = system_settings_provider.get_system_settings('user_by_id', shared_by_userid)[0]
            
            if rec["eventName"] == 'MODIFY':
                updated_rec = rec["dynamodb"]["NewImage"]["data"]["M"]
                updated_collections = DocumentCollection.from_ddb_record(shared_by_user, updated_rec)
                old_rec = rec["dynamodb"]["OldImage"]["data"]["M"]
                old_collections = DocumentCollection.from_ddb_record(shared_by_user, old_rec)
                print(f"Before removing dupes\nold_collections = {old_collections}\nupdated_collections = {updated_collections}")

                updated_collection_names = list(updated_collections.keys())
                old_collection_names = list(old_collections.keys())

                for collection_name in updated_collection_names:
                    # each key in new_rec and old_rec is a document collection dict
                    if collection_name not in old_collection_names:
                        # This is a new document collection. There's nothing to do yet
                        # because you can't share until after doc collection creation.
                        del updated_collections[collection_name]
                    else:
                        updated_collection = updated_collections[collection_name]
                        old_collection = old_collections[collection_name]
                        print(f"Comparing old collection {old_collection} to updated collection {updated_collection}")
                        if updated_collection == old_collection:
                            # no changes to the collection. remove it
                            # from updated_collections, and in the end, any left
                            # in either new or old will be updated.
                            print(f"removing {collection_name} from both old and new because they're identical.")
                            del updated_collections[collection_name]
                            del old_collections[collection_name]
                        else:
                            print(f"Leaving {collection_name} because it's changed and old and new are not identical.")

                print(f"After removing dupes\nold_collections = {old_collections}\nupdated_collections = {updated_collections}")

                # any left in old_collections but not in updated collections are deleted 
                # any left in both are changed.
                # remove references of those doc collections 
                # from all users in the system settings table
                for collection_name in old_collections:
                    if collection_name not in updated_collections:
                        old_collection = old_collections[collection_name]
                        print(f"Deleting collection {old_collection.collection_id} from all users who had it shared")
                        
                        for shared_with_email in old_collection.shared_with:
                            settings: [SystemSetting] = system_settings_provider.get_system_settings('user_by_email', shared_with_email)
                            if isinstance(settings, list) and len(settings) > 0:
                                shared_with_user = settings[0]
                                print(f"shared_with_user before updates: {shared_with_user}")
                                shared_with_user = user_remove_collection(old_collection.collection_id, shared_with_user)
                                print(f"Updating shared_with_user to {shared_with_user}")
                                result = system_settings_provider.set_system_setting(shared_with_user)
                                print(f"Updating shared_with_user result {result}")
                                results.append({"action": "removed_user", "user": shared_with_email, "collection_id": old_collection.collection_id})
                
                # any left have changed and are in both.
                for collection_name in updated_collections:
                    updated_collection = updated_collections[collection_name]
                    old_collection = old_collections[collection_name]
                    updated_shared_with = [] if not hasattr(updated_collection, 'shared_with') else updated_collection.shared_with
                    old_shared_with = [] if not hasattr(old_collection, 'shared_with') else old_collection.shared_with

                    for shared_with_email in updated_shared_with:
                        if shared_with_email not in old_shared_with:
                            # this is a new user in the sharing list.
                            # we need to add this user to the user's document collection record.
                            print(f"Adding collection {updated_collection.collection_id} to user {shared_with_email}")
                            shared_with_user = system_settings_provider.get_system_settings('user_by_email', shared_with_email)[0]
                            shared_with_user = user_add_collection(updated_collection, shared_with_user, shared_by_user)
                            print(f"Updating shared_with_user to {shared_with_user}")
                            result = system_settings_provider.set_system_setting(shared_with_user)
                            print(f"Updating shared_with_user result {result}")
                            results.append({"action": "added_user", "user": shared_with_email, "collection_id": updated_collection.collection_id})
                    
                    for shared_with_email in old_shared_with:
                        if shared_with_email not in updated_shared_with:
                            # this user has been removed from the sharing list.
                            # we need to remove this user from the user's document collection record.
                            print(f"Removing collection {updated_collection.collection_id} from user {shared_with_email}")
                            shared_with_user = system_settings_provider.get_system_settings('user_by_email', shared_with_email)[0]
                            shared_with_user = user_remove_collection(updated_collection.collection_id, shared_with_user)
                            print(f"Updating shared_with_user to {shared_with_user}")
                            result = system_settings_provider.set_system_setting(shared_with_user)
                            print(f"Updating shared_with_user result {result}")
                            results.append({"action": "removed_user", "user": shared_with_email, "collection_id": old_collection.collection_id})

                        # # this is an update to an existing document collection.
                        # if hasattr(updated_collection, 'shared_with'):
                        #     updated_shared_with = updated_collection.shared_with
        
                        # if hasattr(old_collection, 'shared_with'):
                        #     old_shared_with = old_collection.shared_with
                        # print(f"updated_shared_with is now {updated_shared_with}, old_shared_with {old_shared_with}")
                        # for shared_with_email in old_shared_with:
                        #     settings: [SystemSetting] = system_settings_provider.get_system_settings('user_by_email', shared_with_email)
                        #     print(f"Looking up shared_with_user by email {shared_with_email} from old_shared_with, got settings {settings})")
                        #     if isinstance(settings, list) and len(settings) > 0:
                        #         shared_with_user = settings[0]
                        #         print(f"shared_with_user before updates: {shared_with_user}")
                        #         if len(updated_shared_with) > 0 and \
                        #             shared_with_email in updated_shared_with:
                        #             # remove the ones that haven't changed from updated_shared_with,
                        #             # and then any remaining will be added. This is only removing
                        #             # it from the list here, not removing from the db yet.
                        #             print(f"{shared_with_email} didn't change.")
                        #             updated_shared_with.remove(shared_with_email)
                        #         else:  
                        #             # this user has been removed from the sharing list.
                        #             # we need to remove this user from the user's document collection record.
                        #             print(f"Removing collection {updated_collection.collection_id} from user {shared_with_user} of type {type(shared_with_user)}")
                        #             shared_with_user = user_remove_collection(updated_collection.collection_id, shared_with_user)
                        #             print(f"Updating shared_with_user to {shared_with_user}")
                        #             result = system_settings_provider.set_system_setting(shared_with_user)
                        #             print(f"Result from updating shared_with: {result}")
                        
                        # if len(updated_shared_with) > 0:
                        #     print(f"Adding users {updated_shared_with}")
                        #     # any remaining after removing unchanged should be added
                        #     for shared_with_email in updated_shared_with:
                        #         shared_with_user: [SystemSetting] = system_settings_provider.get_system_settings('user_by_email', shared_with_email)
                        #         if isinstance(shared_with_user, list) and len(shared_with_user) > 0:
                        #             shared_with_user = shared_with_user[0]
                        #             print(f"Got shared_with_user: {shared_with_user}\nshared_by_user: {shared_by_user}\nupdated_collection: {updated_collection}")
                        #             shared_with_user = user_add_collection(updated_collection, shared_with_user, shared_by_user)
                        #             system_settings_provider.set_system_setting(shared_with_user)
                        # else:
                        #     # any in the old_shared_with should be removed.
                        #     print(f"Removing users {old_shared_with}")
                        #     for shared_with_email in old_shared_with:
                        #         shared_with_user: [SystemSetting] = system_settings_provider.get_system_settings('user_by_email', shared_with_email)
                        #         if isinstance(shared_with_user, list) and len(shared_with_user) > 0:
                        #             shared_with_user = shared_with_user[0]
                        #             print(f"Got shared_with_user: {shared_with_user}\nshared_by_user: {shared_by_user}\nold_collection: {old_collection}")
                        #             shared_with_user = user_remove_collection(old_collection.collection_id, shared_with_user)
                        #             system_settings_provider.set_system_setting(shared_with_user)

            elif rec['eventName'] == 'DELETE':
                # the final doc collection was deleted and the user's setting record was removed. We need to
                # remove the last doc collection from all the users it was shared with
                old_rec = rec["dynamodb"]["OldImage"]["data"]["M"]
                for collection_name in old_rec:
                    collection = old_rec['collection_name']["M"]
                    for email in collection['shared_with']:
                        user: SystemSetting = system_settings_provider.get_system_settings('user_by_email', email)[0]
                        user = user_remove_collection(collection, user)
                        system_settings_provider.set_system_setting(user)

    return format_response(status, '', '')

                
