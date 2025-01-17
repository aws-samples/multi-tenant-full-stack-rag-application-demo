from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider_event import ToolProviderEvent
import os
from uuid import uuid4

default_memory_mb = 128
default_cpus = 1

supported_code_languages = ['python']
supported_iac_languages = ['yaml', 'python']
docker_base_images = {
    'yaml':  'python:3.12-slim-bullseye',
    'python': 'python:3.12-slim-bullseye'
}

executables_to_extensions = {
    "bash": "sh",
    "yaml": "yaml",
    "node": "jsx",
    "python": "py",
    "python3": "py",
    "python-cdk": "py",
    "sh": "sh"
}

languages_to_tdd_commands = {
    'python': 'pytest -x -s',
    'yaml': 'aws cloudformation validate-template --template-body',
}

languages_to_requirements_install_cmd = {
    'python': 'pip install -t /var/task pytes'
}


class CodeSandboxToolV2Event(ToolProviderEvent):
    def __init__(self, 
        business_logic_code: str='',
        cpus: int=default_cpus,
        entrypoint_path: str='',
        iac_code: str='',
        memory_mb: int=default_memory_mb,
        tdd_code: str='',
    ):
        operation = 'invoke_code_sandbox_tool_v2'
        super().__init__(operation)
        self.event_id = uuid4().hex
        tmpdir = f"/tmp/{self.event_id}"
        os.makedirs(tmpdir)

        
        self.business_logic_code = business_logic_code
        self.code_language = self.detect_code_language(business_logic_code)
        self.code_base_image = docker_base_images[self.code_language]
        self.cpus = cpus
        self.entrypoint_path = entrypoint_path
        self.iac_code = iac_code
        self.iac_language = self.detect_code_language(iac_code)
        self.memory_mb = memory_mb
        self.tdd_code = tdd_code

        self.code_image = docker_base_images[self.code_language]
        self.iac_image = docker_base_images[self.iac_language]
        
        if business_logic_code and self.code_language:
            self.business_logic_filename = f"{tmpdir}/business_logic.{executables_to_extensions[self.code_language]}"
            with open(self.business_logic_filename, 'w') as f:
                f.write(business_logic_code)
        if iac_code and self.iac_language:
            self.iac_filename = f"{tmpdir}/iac.{executables_to_extensions[self.iac_language]}"
            with open(self.iac_filename, 'w') as f:
                f.write(iac_code)
        if tdd_code and self.code_language:
            self.tdd_filename = f"{tmpdir}/tdd.{executables_to_extensions[self.code_language]}"
            with open(self.tdd_filename, 'w') as f:
                f.write(t_code)
        self.tmpdir = tmpdir
        self.tdd_command = languages_to_tdd_commands[self.code_language]
        self.install_tdd_reqs = languages_to_requirements_install_cmd[self.code_language]
    
    def detect_code_language(self, input_str):
        lines = input_str.split("\n")
        firstline = lines[0].replace('```','').split()[0]
        if firstline in supported_code_languages or \
           firstline in supported_iac_languages:
            return firstline
        else:
            raise Exception(f"Failed to find language in firstline {lines[0]}")
    
    def from_lambda_event(self, evt):
        pass

    @staticmethod
    def get_supported_code_languages():
        return supported_code_languages

    @staticmethod
    def get_supported_iac_languages():
        return supported_iac_languages
