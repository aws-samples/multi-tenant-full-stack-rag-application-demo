#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

# This processor manages changes to the system settings table for the sharing handler.
# Here are the possible changes in the SystemSettings table that are currently being 
# monitored, and the actions taken
# 
# id_key = 'user_by_email'
# sort_key = user's email
# data is a map consisting of:
#   user_id: the identity pool id for the user
#   document_collections_enabled: a map of collection id to collection name.
#
#   Change:                         Action:
#   create a user_by_email record   create a user_by_id record with user_email = user's email in the data field map.


import base64
import boto3
import json
import os

from aws_kinesis_agg.deaggregator import deaggregate_records

from multi_tenant_full_stack_rag_application.utils import BotoClientProvider
from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSetting, SystemSettingsProvider, SystemSettingsProviderFactory
from multi_tenant_full_stack_rag_application.utils import format_response


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
    results = []
    for record in records:
        print(f"Got record {record}")
        enc_payload = record["kinesis"]["data"]
        payload = decode_payload(enc_payload)
        rec = json.loads(payload)
        print(f"decoded payload: {rec.keys()}")
        print(f"{rec}")
        ddb_rec = rec["dynamodb"]
        if ddb_rec["Keys"]["id_key"]["S"] == "user_by_email" and \
            rec["eventName"] == 'MODIFY' and \
            'data' in ddb_rec["NewImage"] and \
            "user_id" in ddb_rec["NewImage"]["data"]["M"]:
                # now check for modifications we're interested in:
                # adding a new user_by_email record, create a user_by_id record.
                if 'user_id' not in ddb_rec["OldImage"]["data"]["M"]:
                    user_email = ddb_rec["Keys"]["sort_key"]["S"]
                    user_id = ddb_rec["NewImage"]["data"]["M"]["user_id"]["S"] 
                    new_setting = SystemSetting('user_by_id', user_id, data={"user_email": user_email})
                    print(f"Saving new setting {new_setting}")
                    result = system_settings_provider.set_system_setting(new_setting)
                    print(f"set_system_setting result {result}")
                    results.append(result)
                else: 
                    # add other conditions here later for this processor.
                    pass 
        else: 
            print(f"Skipping rec {ddb_rec}. Not relevant for creating user_by_id record")

    print("Processing complete.")
    return format_response(200, '', '')
