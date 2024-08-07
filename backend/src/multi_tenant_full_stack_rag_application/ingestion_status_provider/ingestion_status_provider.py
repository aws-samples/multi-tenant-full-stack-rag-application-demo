#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import boto3
from .ingestion_status import IngestionStatus


class IngestionStatusProvider:
    def __init__(self, ddb_client: boto3.client, ingestion_status_table):
        self.ddb = ddb_client
        self.table = ingestion_status_table
    
    @staticmethod
    def __strip_userid_prefix__(s3_key) -> str: 
        print(f"__strip_userid_prefix__ received {s3_key}")
        if s3_key.startswith('private/'):
            s3_key = s3_key[8:]
        parts = s3_key.split('/')
        print(f"__strip_userid_prefix__ got parts {parts}")
        return_val = ''
        if len(parts) == 2:
            return_val = '/'.join(parts)
        elif len(parts) > 2:
            return_val = '/'.join(parts[1:])
        else:
            return_val = ''
        return return_val

    def delete_ingestion_status(self, user_id, s3_key):
        s3_key = self.__strip_userid_prefix__(s3_key)
        return self.ddb.delete_item(
            TableName=self.table,
            Key={
                'user_id': {'S': user_id},
                's3_key': {'S': s3_key}
            }
        )

    def get_ingestion_status(self, user_id, s3_key, to_dict=False, limit=20, last_eval_key='')-> IngestionStatus:
        projection_expression = "#user_id, #s3_key, #etag, #lines_processed, #progress_status"
        expression_attr_names = {
            "#user_id": "user_id",
            "#s3_key": "s3_key",
            "#etag": "etag",
            "#lines_processed": "lines_processed",
            "#progress_status": "progress_status"
        }
        # s3_key = self.__strip_userid_prefix__(s3_key)
        kwargs = {      
            'TableName': self.table,
            'KeyConditions': {
                'user_id': {
                    'AttributeValueList': [
                        {"S": user_id}
                    ],
                    'ComparisonOperator': 'EQ'
                },
                's3_key': {
                    'AttributeValueList': [
                        {"S": s3_key}
                    ],
                    'ComparisonOperator': 'BEGINS_WITH'
                }
            },
            'ProjectionExpression': projection_expression,
            'ExpressionAttributeNames': expression_attr_names,
            'Limit': limit,
        }
        if last_eval_key not in [None, '']:  
            kwargs['ExclusiveStartKey'] = {
                "user_id":  {"S": user_id},
                "s3_key": {"S": last_eval_key}
            }

        result = self.ddb.query(
            **kwargs
        )
        
        items = []
        if "Items" in result.keys():
            items = result['Items']
        final_items = []
        for item in items:
            print(f"get_ingestion_status item = {item}")
            status = {"progress_status": "IN_PROGRESS"}
            if len(list(item.keys())) > 0:
                status =  IngestionStatus.from_ddb_record(item)
                if to_dict:
                    status = status.__dict__()
            final_items.append(status)
        print(f"get_ingestion_status returning {final_items}")
        return final_items

    def set_ingestion_status(self, ingestion_status: IngestionStatus): 
        ingestion_status.s3_key = self.__strip_userid_prefix__(ingestion_status.s3_key)
        result = self.ddb.put_item(
            TableName=self.table,
            Item=ingestion_status.to_ddb_record()
        )
        print(f"set_ingestion_status result = {result}")
        return result