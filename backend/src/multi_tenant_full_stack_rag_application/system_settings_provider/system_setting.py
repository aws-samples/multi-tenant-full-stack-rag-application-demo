#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json

class SystemSetting:
    def __init__(self, id_key, sort_key, data={}):
        self.id_key = id_key
        self.sort_key = sort_key
        self.data = data
        if isinstance(data, dict):
            self.data_type = 'M'
        # right now the only system settings are maps
        else:
            # do this so if/when this breaks due to new types I will find 
            # this spot.
            raise Exception('Unexpected non-dict system setting type.')

    @staticmethod
    def from_ddb_record(rec):
        final_data = {}
        if 'data' in rec:
            data = rec['data']['M']
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

        setting = SystemSetting(rec['id_key']['S'], rec['sort_key']['S'], final_data)
        return setting


    def to_ddb_record(self): 
        typed_data = {}
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
           
        return {
            'id_key': {'S': self.id_key},
            'sort_key': {'S': self.sort_key},
            'data': {self.data_type: typed_data}
        }
    
    def __dict__(self):
        return {
            'id_key': self.id_key,
            'sort_key': self.sort_key,
            'data': self.data
        }

    def __str__(self):
        return json.dumps({
            'id_key': self.id_key,
            'sort_key': self.sort_key,
            'data': self.data
        })
