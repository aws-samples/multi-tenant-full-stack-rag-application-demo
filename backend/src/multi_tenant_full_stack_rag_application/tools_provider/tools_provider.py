import json
import os
from importlib import import_module

from .tools_provider_event import ToolsProviderEvent
from .tools.tool_provider import ToolProvider
from multi_tenant_full_stack_rag_application import utils
"""
API 
event {
    "operation": [ "list_tools" | "invoke_tool" ],
    "origin": the function name of the calling function, or the frontend_origin.,
    "args": 
        for list_tools:
            none

        for invoke_tool:
            **kwargs (depends on tool)

Initialization of tools

To init the tools the ToolsProvider will scan the tools directory for 
directory names, and import the files in those directories of the same name

"""

tp = None

class ToolsProvider:
    def __init__(self,
        tools_dir: str=None
    ):
        print(f"Initiaized ToolsProvider")
        tools_subdir = "/multi_tenant_full_stack_rag_application/tools_provider/tools"
        tools_pypath = tools_subdir.replace("/", ".").strip('.')

        if not tools_dir:
            tools_dir = f"{os.getcwd()}/{tools_subdir}"
        print(f"Scanning tools_dir {tools_dir}")
        self.tool_descriptions = {}
        self.tool_classes = {}
        self.fn_name_prefix = os.getenv('STACK_NAME').replace('-','') + 'ToolSandbox'

        for entry in os.scandir(tools_dir):
            tool_path = os.path.exists(f"{tools_dir}/{entry.name}/{entry.name}.py")
            if entry.is_dir() and \
            entry.name != '__pycache__':
                parts = entry.name.split('_')
                class_name = ''
                for part in parts:
                    class_name += part.capitalize()
                tool_pypath = f"{tools_pypath}.{entry.name}.{entry.name}.{class_name}"
                print(f"tool_pypath = {tool_pypath}")
                tool_file = '.'.join(tool_pypath.split('.')[:-1]).strip('.')
                print(f"Tool file is {tool_file}")
                classname = tool_pypath.split('.')[-1]
                tool_module = import_module(tool_file)
                tool_class = getattr(tool_module, classname)
                
                self.tool_classes[entry.name] = tool_class

                self.tool_descriptions[entry.name] = {
                    "py_path": tool_pypath,
                    "inputs": tool_class.get_inputs(),
                    "outputs": tool_class.get_outputs()
                }
        
    def handler(self, evt, ctx):
        print(f"ToolsProvider receved evt {evt}, context {ctx}")
        handler_evt = ToolsProviderEvent().from_lambda_event(evt)
        status = 200
        if handler_evt.operation == 'list_tools':
            result = self.list_tools()

        elif handler_evt.operation == 'invoke_tool':
            result = self.invoke_tool(handler_evt)
        
        print(f"ToolsProvider returning result {result}")
        return utils.format_response(status, result, handler_evt.origin)

    def invoke_tool(self, handler_evt):
        tool_name = handler_evt.args['tool_name']
        del handler_evt.args['tool_name']
        
        if 'user_id' in handler_evt.args:
            del handler_evt.args['user_id']
        # the remaining keys of args should be the same as the input
        # args for the tool
        got_required_args = True
        missing_args = []
        args = {}
        print(f"Remaining handler_evt.args {handler_evt.args}")
        tool_inputs = self.tool_descriptions[tool_name]['inputs'] 
        for key in tool_inputs.keys():
            print(f"Checking key {key} from inputs.")
            if tool_inputs[key]['required'] == True and \
            (
                key not in handler_evt.args.keys() or \
                not handler_evt.args[key]
            ):
                print(f"Missing value for required key {key}")
                got_required_args = False
                missing_args.append(key)
            else:
                if key in handler_evt.args.keys():
                    args[key] = handler_evt.args[key]
                    # delete the expected args after adding
                    # them to the clean args dict. If any
                    # are left at the end, throw an error
                    # for unexpected input args.
                    del handler_evt.args[key]
            
        if not got_required_args:
            raise Exception(f"ERROR: required args {missing_args} not provided")
        
        elif len(list(handler_evt.args.keys())) > 0:
            # if there are any keys left in the args then they were unexpected
            raise Exception(f"ERROR: ToolsProvider received unexpected args {handler_evt.args}.")


        args['user_id'] = handler_evt.user_id
        # proceed to use the tool
        print(f"Invoking tool with args {args}")
        response = self.tool_classes[tool_name]().handler({
            "operation": args['operation'],
            "origin": handler_evt.origin,
            "args": args
        })
        print(f"Got result from tool: {response}")
        result = response['body']
        
        return result

    def list_tools(self):
        return self.tool_descriptions


def handler(evt, ctx):
    global tp
    if not tp:
        tp = ToolsProvider()
    return tp.handler(evt, ctx)