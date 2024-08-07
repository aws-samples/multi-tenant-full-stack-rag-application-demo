#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
from multi_tenant_full_stack_rag_application.system_settings_provider.system_setting import SystemSetting

class SystemSettingsProvider:
    def __init__(self, 
        ddb_client: boto3.client,
        system_settings_table: str
    ):
        self.ddb = ddb_client
        self.table = system_settings_table

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
        return items

    def set_system_setting(self, system_setting: SystemSetting):
        ddb_item = system_setting.to_ddb_record()
        return self.ddb.put_item(
            TableName=self.table,
            Item=ddb_item
        )

    @staticmethod
    def settings_to_list(settings: [SystemSetting]):
        final_list = []
        print(f"settings_to_dict received settings {settings}")
        for setting in settings:
            if not setting:
                continue
            else:
                print(f"Got setting {setting}")
            tmp_dict = setting.__dict__()
            # del tmp_dict['user_id']
            # del tmp_dict['collection_name']
            final_list.append(tmp_dict)
        return final_list