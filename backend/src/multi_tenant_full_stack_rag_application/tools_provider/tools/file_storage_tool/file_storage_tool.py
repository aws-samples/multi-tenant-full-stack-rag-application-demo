import boto3

from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider import ToolProvider
from multi_tenant_full_stack_rag_application import utils
from .file_storage_tool_event import FileStorageToolEvent


class FileStorageTool(ToolProvider):
    def __init__(self,
        s3_client=None
    ):
        super().__init__()
        self.utils = utils
        self.bucket = self.utils.get_ssm_params('ingestion_bucket_name')
        if not s3_client:
            self.s3 = boto3.client('s3')
        else:
            self.s3 = s3_client
        self.my_origin = self.utils.get_ssm_params('origin_tools_provider')

    @staticmethod
    def get_inputs():
        return {
            "operation": {
                "required": True,
                "type": "string",
                "description": "The operation to execute on the tool. Currently GET, LIST, or PUT"
            },
            "FileContents": {
                "required": "True when using PUT operations.",
                "type": "bytes",
                "description": "The contents of the file to save."
            },
            "Key": {
                "comment": "does not include the s3://bucket_name/ prefix, just the key.",
                "required": "depends",
                "type": "string",
                "description": "The key format is collection_id/filename. Required full s3_key for GET or PUT operations. Optional as a prefix for LIST operation. If you know the collection ID to LIST (the one that has file storage enabled), use it as the key value."
            },
            "StartAfter": {
                "required": False,
                "type": "string",
                "description": "used by LIST operation to start somewhere other than the first result",
            },
            "MaxKeys": {
                "required": False,
                "type": "int",
                "description": "used by LIST operation to page through results. Defaults to 1000."
            },
            "ContinuationToken": {
                "required": False,
                "type": "string",
                "description": "Used in LIST operations when paging through results. Must be obtained from the results of a previous LIST operation."
            }
        }

    @staticmethod
    def get_outputs():
        return {
            "comment": "return results are different by operation type",
            "results": [
                {
                    "s3_key_of_result": {
                        "contents": "file contents in bytes if it was a get, or none if it's a list or a put.",
                    }
                }
            ]
        }

    def handler(self, evt):
        print(f"FileStorageTool.handler received evt {evt}")
        handler_evt = FileStorageToolEvent().from_lambda_event(evt)
        doc_collections = self.utils.get_document_collections(
            handler_evt.user_id,
            origin=self.my_origin
        )
        print(f"Got document collections {doc_collections}")
        enabled_storage_collections = []
        for collection_name in doc_collections.keys():
            collection = doc_collections[collection_name]
            print(f"Got document collection {collection}")
            if collection['file_storage_tool_enabled']:
                enabled_storage_collections.append(collection)
        print(f"document collections enabled for storage: {enabled_storage_collections}")
        if len(enabled_storage_collections) == 0:
            result = "No collections enabled for storage"
        else:
            print(f"FileStorageToolEvent is now {handler_evt.__dict__}")
            result = self.run_tool(handler_evt, enabled_storage_collections)
            print(f"Result from file_storage_tool: {result}")
            return result

    def get_object(self, args):
        response = self.s3.get_object(**args)
        key = self.sanitize_key(args['Key'])
        results = {
            key: {
                "contents": response['Body'].read()
            }
        }
        return results

    def list_objects(self, args):
        response = self.s3.list_objects_v2(**args)
        results = {
            "Files": []
        }
        print(f"list_objects got response {response}")
        for file in response['Contents']:
            results['Files'].append(
                self.sanitize_key(file['Key'])
            )
        if response['IsTruncated']:
            results['NextContinuationToken'] = response['NextContinuationToken']
        return results
    
    def put_object(self, args):
        response = self.s3.put_object(**args)
        if 'ETag' in response:
            # succeeded
            result = {
                "Key": self.sanitize_key(args["Key"]),
            }
        else:
            raise Exception(f"Failed to upload object with args {args}")
        return result

    def run_tool(self, handler_evt, enabled_storage_collections):
        op = handler_evt.operation
        s3_root_path = f"private/{handler_evt.user_id}"
        path = f"{s3_root_path}/{handler_evt.key}"
        
        args = {
            "Bucket": self.bucket,
        }

        if op == 'LIST':
            args["Prefix"] = path
            args["MaxKeys"] = handler_evt.max_keys
            if handler_evt.start_after != '':
                args['StartAfter'] = handler_evt.start_after
            results = self.list_objects(args)  

        elif op == 'GET':
            args['Key'] = path
            results = self.get_object(args)

        elif op == 'PUT':
            args['FileContents'] = handler_evt.body
            args['Key'] = path
            results = self.put_object(args)

        print(f"Got results {results}")
        return {
            "statusCode": '200',
            "body": results
        }

    def sanitize_key(self, key):
        if key.startswith('private/'):
            key = key.split('/', 2)[-1]
        return key

