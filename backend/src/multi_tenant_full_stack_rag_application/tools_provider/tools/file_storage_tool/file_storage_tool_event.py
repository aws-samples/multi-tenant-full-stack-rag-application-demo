from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider_event import ToolProviderEvent


class FileStorageToolEvent(ToolProviderEvent):
    def __init__(self, 
        operation: str='',
        user_id: str='',
        body: str='',
        key: str='',
        max_keys: int=1000,
        start_after: str='',
    ):
        super().__init__(operation)
        self.user_id = user_id
        self.body = body
        self.key = key
        self.max_keys = max_keys
        self.start_after = start_after

    def from_lambda_event(self, evt):
        print(f"file storage tool event received evt {evt}")
        self.operation = evt['operation']
        self.args = evt['args']
        self.user_id = self.args['user_id']
        del self.args['user_id']

        if 'Body' in self.args:
            self.body = self.args['Body']
            if not isinstance(self.body, bytes):
                if isinstance(self.body, dict):
                    self.body = json.dumps(self.body)
                if isinstance(self.body, str):
                    self.body = self.body.encode('utf-8')
        else:
            self.body = None
            
        if 'Key' in self.args:
            # the replace should protect against directory traversal beyond
            # the user's root dir.
            self.key = self.args['Key'].replace('../', '')
        else:
            self.key = ''

        if self.operation == 'PUT' and\
        (self.key == '' or
        self.body == None):
            raise Exception("Must provide input data for body and S3 path as Key for PUT operations")
        
        elif self.operation == 'GET' and\
        self.key == '':
            raise Exception("Must provide S3 path as key for GET operations")

        self.max_keys = 1000 if not 'MaxKeys' in self.args else self.args['MaxKeys'] 
        self.start_after = '' if not 'StartAfter' in self.args else self.args['StartAfter'] 
        if not self.user_id:
            raise Exception("Must have user_id set for file storage tool usage.")

        return self