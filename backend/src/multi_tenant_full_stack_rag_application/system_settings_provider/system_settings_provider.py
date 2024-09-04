#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os

from multi_tenant_full_stack_rag_application.system_settings_provider import SystemSetting, SystemSettingsProviderEvent

"""
GET /system_setting/id_key/sort_key: fetch system setting
POST /system_setting: create or update system setting
    body = {
        'id_key': str,
        'sort_key': str,
        'data': str
    }
DELETE /system_setting/id_key/sort_key :  delete a system setting
"""

ddb_client = None
ssm_client = None
system_settings_provider = None
system_settings_table = None


class SystemSettingsProvider:
    def __init__(self, 
        ddb_client: boto3.client,
        system_settings_table: str
    ):
        self.ddb = ddb_client
        self.table = system_settings_table

    def create_system_setting(self, id_key, sort_key, data):
        return SystemSetting(id_key, sort_key, data)

    def delete_system_setting(self, id_key, sort_key):
        return self.ddb.delete_item(
            TableName=self.table,
            Key={
                'id_key': {
                    'S': id_key
                },
                'sort_key': {
                    'S': sort_key
                }
            }
        )

    def get_system_settings(self, id_key, sort_key, limit=20, last_eval_key='') -> [SystemSetting]:
        print(f"get_system_settings received id_key {id_key}, sort_key {sort_key}")
        projection_expression = "#data, #id_key, #sort_key"
        expression_attr_names = {
            "#data": "data",
            "#id_key": "id_key",
            "#sort_key": "sort_key"
        }
        print(f"Getting item {sort_key} for id_key {id_key}")
        kwargs = {
            'TableName': self.table,
            'KeyConditions': {
                'id_key': {
                    'AttributeValueList': [
                        {"S": id_key},
                    ],
                    'ComparisonOperator': 'EQ' 
                }, 
                'sort_key': {
                    'AttributeValueList': [
                        {"S": sort_key},
                    ],
                    'ComparisonOperator': 'BEGINS_WITH' 
                }
            },
            'ProjectionExpression': projection_expression,
            'ExpressionAttributeNames': expression_attr_names,
            'Limit': int(limit)
        }
        if last_eval_key != '':
            kwargs['ExclusiveStartKey']: last_eval_key
        print(f"querying ddb with kwargs {kwargs}")
        result = self.ddb.query(
            **kwargs
        )
        items = []
        print(f"result from querying ddb: {result}")
        if "Items" in result.keys():
            for item in result["Items"]:        
                if len(list(item.keys())) > 0:
                    setting =  SystemSetting.from_ddb_record(item)
                    items.append(setting)
        print(f"Returning items {items}")
        return {
            "response": items,
            "last_eval_key": result.get("LastEvaluatedKey", None)
        }

    def handler(self, event, context):
        print(f"Received event {event}")
        handler_evt = SystemSettingsProviderEvent().from_lambda_event(event)

        if handler_evt.operation == 'get_system_settings':
            response = self.get_system_settings(handler_evt.id_key, handler_evt.sort_key, handler_evt.limit, handler_evt.last_eval_key)
            print(f"get_system_settings response {response}")
            items = self.settings_to_list(response['response'])
            print(f"get_system_settings response items = {items}")
            
            result = {
                "operation": handler_evt.operation,
                "response": items,
                "statusCode": 200,
                # "last_eval_key": response["last_eval_key"]
            }

        elif handler_evt.operation == 'set_system_setting':
            response = self.set_system_setting(
                self.create_system_setting(
                    handler_evt.id_key,
                    handler_evt.sort_key,
                    handler_evt.data
                )
            )
            print(f"set_system_setting response {response}")
            result = {
                "operation": handler_evt.operation,
                "response": response,
                "statusCode": response["ResponseMetadata"]["HTTPStatusCode"]
            }
        
        elif handler_evt.operation == 'delete_system_setting':
            response = self.delete_system_setting(
                handler_evt.id_key,
                handler_evt.sort_key
            )
            print(f"delete_system_setting response {response}")
            result = {
                "operation": "DELETE /system_setting",
                "response": response,
                "statusCode": response["ResponseMetadata"]["HTTPStatusCode"],
            }
    
        else:
            raise Exception(f'Unexpected operation {handler_evt.operation}')
        return result

    def set_system_setting(self, system_setting: SystemSetting):
        ddb_item = system_setting.to_ddb_record()
        response = self.ddb.put_item(
            TableName=self.table,
            Item=ddb_item
        )
        print(f"Response from set_system_setting {response}")
        return response

    @staticmethod
    def settings_to_list(settings: [SystemSetting]):
        final_list = []
        print(f"settings_to_dict received settings {settings}")
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
    global ddb_client, ssm_client, system_settings_provider, system_settings_table
    print(f"initialization handler received event {event}")
    if not system_settings_provider:
        ddb_client = boto3.client('dynamodb')
        ssm_client = boto3.client('ssm')
        print("About to get ssm parameter for system_settings_table")
        system_settings_table = ssm_client.get_parameter(
            Name=f'/{os.getenv("STACK_NAME")}/system_settings_table'
        )['Parameter']['Value']
        system_settings_provider = SystemSettingsProvider(ddb_client, system_settings_table)
    result = system_settings_provider.handler(event, context)
    return result