#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
import os
from .user_setting import UserSetting

class UserSettingsProvider:
    def __init__(self, 
        ddb_client: boto3.client,
        user_settings_table: str
    ):
        self.ddb = ddb_client
        self.table = user_settings_table

    def get_user_setting(self, user_id, setting_name) -> UserSetting:
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
        # print(f"Getting item {setting_name} for user_id {user_id}")
        # print(f"region is {os.getenv('AWS_REGION')}")
        # print(f"Key is {key}")
        # print(f"Table name is {self.table}")
        # print(f"projection_expression {projection_expression}")
        # print(f"expression_attr_names {expression_attr_names}")
        result = self.ddb.get_item(
            TableName=self.table,
            Key=key,
            ProjectionExpression=projection_expression,
            ExpressionAttributeNames=expression_attr_names
        )
        # print(f"Got result {result}")
        item = {}
        if "Item" in result.keys():
            item = result['Item']
        #TODO strip the ddb types before returning the item
        if len(list(item.keys())) > 0:
            
            us =  UserSetting.from_ddb_record(item)
            return us
        else: 
            return None

    def set_user_setting(self, user_setting: UserSetting) -> None:
        ddb_item = user_setting.to_ddb_record()

        self.ddb.put_item(
            TableName=self.table,
            Item=ddb_item
        )