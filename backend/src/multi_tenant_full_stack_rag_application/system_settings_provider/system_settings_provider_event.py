#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json


class SystemSettingsProviderEvent:
    operation: str=''
    id_key: str=''
    sort_key: str=''
    # data is usually going to be a 
    # json.dumps string of a dict.
    data: dict={}
    limit: int=20
    last_eval_key: str=None


    def from_lambda_event(self, event):
        self.operation = event['operation']
        self.id_key = event['id_key']
        self.sort_key = event['sort_key']
        self.data = event['data'] if 'data' in event else {}
        
        if 'limit' in event:
            self.limit = int(event['limit'])
        
        if 'last_eval_key' in event:
            self.last_eval_key = event['last_eval_key']
        return self

    def __str__(self):
        args = {
            "operation": self.operation,
            "id_key": self.id_key,
            "sort_key": self.sort_key,
            "data": self.data
        }
        return json.dumps(args)