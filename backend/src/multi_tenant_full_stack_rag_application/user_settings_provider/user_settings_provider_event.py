#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class UserSettingsProviderEvent:
    method: str=''
    user_id: str=''
    setting_name: str=''
    # data is usually going to be a 
    # json.dumps string of a dict.
    data: dict={}
    limit: int=20
    last_eval_key: str=''


    def from_lambda_event(self, event):
        self.method = event['method']
        self.user_id = event['user_id']
        self.setting_name = event['setting_name']
        self.data = event['data'] if 'data' in event else {}
        
        if 'limit' in event:
            self.limit = int(event['limit'])

        if 'last_eval_key' in event:
            self.last_eval_key = event['last_eval_key']
        
        return self

    def __str__(self):
        args = {
            "method": self.method,
            "user_id": self.user_id,
            "setting_name": self.setting_name,
            "data": self.data
        }
        return json.dumps(args)