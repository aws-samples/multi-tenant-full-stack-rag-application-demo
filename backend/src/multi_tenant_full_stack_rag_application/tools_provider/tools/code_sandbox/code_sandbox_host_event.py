from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider_event import ToolProviderEvent
import os
import logging
from uuid import uuid4
from pydantic import BaseModel


logging.basicConfig(filename='/var/log/codesandbox/codesandbox.log', level=logging.INFO)
logger = logging.getLogger(__name__)

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
    'python': '/app/bin/pytest -x -s',
    'yaml': 'aws cloudformation validate-template --template-body',
}

languages_to_requirements_install_cmd = {
    'python': '/app/bin/pip3 install --upgrade pytest boto3'
}


class CodeSandboxHostEvent(BaseModel):
    business_logic_code: str=''
    business_logic_filename: str=''
    code_image: str=''
    code_language: str=''
    cpus: int=default_cpus
    entrypoint_path: str=''
    event_id: str=''
    iac_code: str=''
    iac_filename: str=''
    iac_image: str=''
    iac_language: str=''
    install_tdd_reqs: str=''
    memory_mb: int=default_memory_mb
    tdd_code: str=''
    tdd_command: str=''
    tdd_filename: str=''
    tmpdir: str=''

    def __init__(self, **kwargs):
        logger.info(f'code_sandbox_host_event got kwargs {kwargs}')
        super().__init__(**kwargs)
        self.event_id = kwargs['event_id']
        app_home = os.getenv('APP_HOME')
        tmpdir = f"/tmp/{self.event_id}"
        os.makedirs(tmpdir)
        logger.info(f"Got business_logic_code {kwargs['business_logic_code']}")
        logger.info(f"Got iac_code {kwargs['iac_code']}")
        self.cpus = kwargs['cpus']
        self.entrypoint_path = kwargs['entrypoint_path']
        self.iac_language = kwargs['iac_language']    
        self.memory_mb = kwargs['memory_mb']
        self.code_image = kwargs['code_image']
        self.iac_image = kwargs['iac_image']
        self.business_logic_filename = f"{tmpdir}/business_logic.{executables_to_extensions[self.code_language]}"
        self.tdd_filename = f"{tmpdir}/tdd.{executables_to_extensions[self.code_language]}"
        self.iac_filename = f"{tmpdir}/iac.{executables_to_extensions[self.iac_language]}"
        logger.info(f"Got business_logic_filename {self.business_logic_filename}")
        logger.info(f"Got tdd_filename {self.tdd_filename}")
        logger.info(f"Got iac_filename {self.iac_filename}")
        with open(self.business_logic_filename, 'w') as f:
            f.write(self.business_logic_code)
        print(f"Wrote {self.business_logic_filename}")
        with open(self.iac_filename, 'w') as f:
            f.write(self.iac_code)
        print(f"Wrote {self.iac_filename}")
        with open(self.tdd_filename, 'w') as f:
            f.write(self.tdd_code)
        print(f"Wrote {self.tdd_filename}")
        
        self.tmpdir = tmpdir
        self.tdd_command = kwargs['tdd_command']
        self.install_tdd_reqs = kwargs['install_tdd_reqs']

    def from_lambda_event(self, evt):
        pass

    @staticmethod
    def get_supported_code_languages():
        return supported_code_languages

    @staticmethod
    def get_supported_iac_languages():
        return supported_iac_languages
