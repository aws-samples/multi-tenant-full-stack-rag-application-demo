from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider_event import ToolProviderEvent

default_memory_mb = 128
default_cpus = 1

class CodeSandboxToolEvent(ToolProviderEvent):
    def __init__(self, 
        build_artifacts_zip_s3uri: str='',
        cpus: int=1,
        entrypoint_path: str='',
        memory_mb=default_memory_mb,
        operation: str='', 
    ):
        super().__init__(operation)
        self.build_artifacts_s3_uri = build_artifacts_zip_s3uri
        self.cpus = cpus
        self.entrypoint_path = entrypoint_path
        self.memory_mb = memory_mb
        self.operation = operation

    def from_lambda_event(self, evt):
        self.operation = evt['operation']
        self.build_artifacts_s3_uri = evt['args']['build_artifacts_zip_s3uri']
        self.cpus = default_cpus if 'cpus' not in evt['args'] \
            else evt['args']['cpus']
        self.entrypoint_path = '' if 'entrypoint_path' not in evt['args'] \
            else evt['args']['entrypoint_path']
        self.memory_mb = default_memory_mb if 'memory_mb' not in evt['args'] \
            else evt['args']['memory_mb']
        return self