#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class UserSetting:
    def __init__(self, user_id, setting_name, data={}):
        self.user_id = user_id
        self.setting_name = setting_name
        self.data = data
        if isinstance(data, dict):
            self.data_type = 'M'
        # right now the only user settings are maps
        else:
            # do this so if/when this breaks due to new types I will find 
            # this spot.
            raise Exception('Unexpected non-dict user setting type.')

    @staticmethod
    def from_ddb_record(rec):
        # print(f"from_ddb_record got rec {rec}")
        data = rec['data']['M']
        final_data = {}
        for key in data:
            final_data[key] = {}
            data_type = list(data[key].keys())[0]
            if data_type == 'M':
                subdict = data[key]['M']
                for subkey in subdict:
                    final_data[key][subkey] = {}
                    data_type = list(subdict[subkey].keys())[0]
                    val = subdict[subkey][data_type]
                    if data_type == 'N':
                        if '.' in val: 
                            val = float(val)
                        else:
                            val = int(val)
                    final_data[key][subkey] = val
            elif data_type == 'N':
                if '.' in data[key]['N']:
                    final_data[key] = float(data[key]['N'])
                else:
                    final_data[key] = int(data[key]['N'])
            elif data_type == 'S': 
                final_data[key] = data[key]['S']
            elif data_type == 'SS':
                final_data[key] = data[key]['SS']
            elif data_type == 'L':
                final_data[key] = data[key]['L']
                

        us = UserSetting(rec['user_id']['S'], rec['setting_name']['S'], final_data)
        return us


    def to_ddb_record(self): 
        typed_data = {}
        print(f"to_ddb_record converting self.data {self.data}")
        for key in self.data:
            if isinstance(self.data[key], str):
                typed_data[key] = {'S': self.data[key]}
            elif isinstance(self.data[key], float) or \
                isinstance(self.data[key], int):
                typed_data[key] = {'N': str(self.data[key])}
            elif isinstance(self.data[key], dict):
                subdict = self.data[key]
                typed_subdict = {}
                for subkey in subdict:
                    if isinstance(subdict[subkey], str):
                        typed_subdict[subkey] = {'S': subdict[subkey]}
                    elif isinstance(subdict[subkey], float) or \
                        isinstance(subdict[subkey], int):
                        typed_subdict[subkey] = {'N': subdict[subkey]}
                    elif isinstance(subdict[subkey], list):
                        print(f"key {key} has subkey[subdict] list {subdict[subkey]}")
                        if len(subdict[subkey]) == 0:
                            continue
                        type_val = 'L'
                        all_strs = True
                        for item in subdict[subkey]:
                            if not isinstance(item, str):
                                all_strs = False
                                break
                        if all_strs:
                            type_val = 'SS'
                        typed_subdict[subkey] = {type_val: subdict[subkey]} 
                    elif isinstance(subdict[subkey], dict):
                        typed_subdict[subkey] = {'M': subdict[subkey]} 
                    else:
                        pass
                typed_data[key] = {'M': typed_subdict}
        result = {
            'user_id': {'S': self.user_id},
            'setting_name': {'S': self.setting_name},
            'data': {self.data_type: typed_data}
        }
        print(f"to_ddb_record returning {result}")
        return result
    
    def __dict__(self):
        return {
            'user_id': self.user_id,
            'setting_name': self.setting_name,
            'data': self.data
        }

    def __str__(self):
        return json.dumps({
            'user_id': self.user_id,
            'setting_name': self.setting_name,
            'data': self.data
        })
