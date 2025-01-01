#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

class ToolsProviderEvent:
    def __init__(self, 
        args: dict={},
        operation: str='',
        origin: str=''
    ):
        self.operation = operation
        self.args = args
        self.origin = origin

    def from_lambda_event(self, evt):
        self.operation = evt['operation']
        if self.operation not in ['invoke_tool', 'list_tools']:
            raise Exception(f"ERROR: Invalid operation \"{operation}\" provided")
        self.origin = evt['origin']
        if 'args' in evt:
            self.args = evt['args']
        else:
            self.args = {}
        
        return self