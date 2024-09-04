#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
from .user_setting import UserSetting
from .user_settings_provider_event import UserSettingsProviderEvent
"""
GET /user_setting/user_id/setting_name: fetch user setting
POST /user_setting: create or update user setting
    body = {
        'user_id': str,
        'setting_name': str,
        'data': str
    }
DELETE /user_setting/user_id/setting_name :  delete a user setting
"""

ddb_client = None
ssm_client = None
user_settings_provider = None
user_settings_table = None


class UserSettingsProvider:
    def __init__(self, 
        ddb_client: boto3.client,
        user_settings_table: str
    ):
        self.ddb = ddb_client
        self.table = user_settings_table

    @staticmethod
    def create_user_setting(user_id, setting_name, data):
        return UserSetting(user_id, setting_name, data)

    def delete_user_setting(self, user_id, setting_name):
        key = {
            'user_id': {"S": user_id},
            'setting_name': {"S": setting_name}
        }
        return self.ddb.delete_item(
            TableName=self.table,
            Key=key
        )

    """
    Get a user setting
    """
    def get_user_settings(self, user_id, setting_name, limit=20, last_eval_key='') -> [UserSetting]:
        print(f"get_user_settings received user_id {user_id}, setting_name {setting_name}, limit {limit}, last_eval_key {last_eval_key}") 
        projection_expression = "#data, #user_id, #setting_name"
        expression_attr_names = {
            "#data": "data",
            "#user_id": "user_id",
            "#setting_name": "setting_name"
        }
        key = {
            'user_id': {"S": user_id},
            'setting_name': {"S": setting_name}
        }
        args = {
            'TableName': self.table,
            'Key': key,
            'ProjectionExpression': projection_expression,
            'ExpressionAttributeNames': expression_attr_names,
        }
        if last_eval_key:
            args['ExclusiveStartKey'] = last_eval_key

        result = self.ddb.get_item(**args)
        # print(f"Got result {result}")
        items = []
        if "Item" in result.keys():
            items.append(UserSetting.from_ddb_record(result['Item']))
        elif "Items" in result.keys():
            for item in result['Items']:
                items.append(UserSetting.from_ddb_record(result['Item']))
        
        return {"response": items, "last_eval_key": result.get('LastEvaluatedKey', None)}

    def handler(self, event, context):
        print(f"Received event {event}")
        handler_evt = UserSettingsProviderEvent().from_lambda_event(event)

        if handler_evt.method == 'GET':
            response = self.get_user_settings(handler_evt.user_id, handler_evt.setting_name, handler_evt.limit, handler_evt.last_eval_key)
            print(f"get_user_settings response = {response}")
            result = {
                "operation": "GET /user_setting",
                "response": self.settings_to_list(response["items"]),
                "last_eval_key": response["last_eval_key"],
                "statusCode": 200
            }

        elif handler_evt.method == 'POST':
            response = self.set_user_setting(
                self.create_user_setting_(
                    handler_evt.user_id,
                    handler_evt.setting_name,
                    handler_evt.data
                )
            )
            print(f"set_user_setting response {response}")
            result = {
                "operation": "POST /user_setting",
                "statusCode": response["ResponseMetadata"]["HTTPStatusCode"]
            }
        
        elif handler_evt.method == 'DELETE':
            response = self.delete_user_setting_(
                handler_evt.user_id,
                handler_evt.setting_name
            )
            print(f"delete_user_setting response {response}")
            result = {
                "operation": "DELETE /user_setting",
                "statusCode": response["ResponseMetadata"]["HTTPStatusCode"],
            }
    
        else:
            raise Exception(f'Unexpected method {handler_evt.method}')
        return result

    def set_user_setting(self, user_setting: UserSetting) -> None:
        ddb_item = user_setting.to_ddb_record()

        return self.ddb.put_item(
            TableName=self.table,
            Item=ddb_item
        )

    def settings_to_list(self, settings: [UserSetting]):
        final_list = []
        print(f"settings_to_list received settings {settings}")
        for setting in settings:
            if not setting:
                continue
            else:
                print(f"Got setting {setting}")
            tmp_dict = setting.__dict__
            # del tmp_dict['user_id']
            # del tmp_dict['collection_name']
            final_list.append(tmp_dict)
        return final_list

def handler(event, context):
    global ddb_client, ssm_client, user_settings_provider, user_settings_table
    print(f"initialization handler received event {event}")
    if not user_settings_provider:
        ddb_client = boto3.client('dynamodb')
        ssm_client = boto3.client('ssm')
        print("About to get ssm parameter for user_settings_table")
        user_settings_table = ssm_client.get_parameter(
            Name=f'/{os.getenv("STACK_NAME")}/user_settings_table'
        )['Parameter']['Value']
        user_settings_provider = UserSettingsProvider(ddb_client, user_settings_table)
    result = user_settings_provider.handler(event, context)
    return result