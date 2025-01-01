import boto3
import os
import requests
import subprocess
import time
import zipfile 

from multi_tenant_full_stack_rag_application.tools_provider.tools.tool_provider import ToolProvider
from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox_tool.code_sandbox_tool_event import CodeSandboxToolEvent
from uuid import uuid4

executables_to_extensions = {
    "python": "py",
    "python3": "py",
    "node": "jsx",
    "bash": "sh",
    "sh": "sh"
}

class CodeSandboxTool(ToolProvider):
    def __init__(self):
        super().__init__()
        # all functions created must start with the prefix below 
        self.lambda_ = boto3.client('lambda')
        self.guru = boto3.client('codeguru-security')
        self.s3 = boto3.client('s3')
        
    # @param build_artifacts_s3_uri: a zip file that has a Dockerfile at the top
    # level, and any other required files for the build included. Do not 
    # build the zip file with the Dockerfile and other files under a top-level
    # directory. The build image should have the entrypo
    def build_image(self, 
        build_artifacts_zip_s3uri,
    ):
        uid = uuid4().hex
        local_zip_file = self.download_s3_file(build_artifacts_zip_s3uri)
        tmp_folder = '/'.join(local_zip_file.split('/')[:-1])
        with zipfile.ZipFile(local_zip_file, 'r') as zip_ref:
            zip_ref.extractall(tmp_folder)
        file_path = f"{tmp_folder}/Dockerfile"

        subprocess.run([
            'nerdctl', 
            'build', 
            '-t', 
            uid, 
            '-f', 
            file_path, 
            '.'
        ])
        return uid
        # if not init_script_extension:
        #     executable = init_script_executable.split('/')[-1]
        #     init_script_extension = executables_to_extensions[executable]
        # response = self.upload_code_artifact(init_script)
        # scan_results = self.scan_code(response['codeArtifactId'], response['scanName'])
        # if len(scan_results['findings']) == 0:
        #     init_file = f"{tmp_folder}/init.{init_script_extension}"
        #     with open(init_file, "w") as f_out:
        #         f_out.write(init_script)
        #     subprocess.run([init_script_executable, init_file])
        # else:
        #     print(f"scan of init_script got findings: {scan_results}.")
        #     raise Exception(f"[ERROR] init script scan results had findings: {scan_results})")

    def download_s3_file(self, s3_uri):
        print(f"Downloading {s3_uri}")
        parts = s3_uri.split('/')
        bucket = parts[2]
        filename = parts[-1]
        s3_path = '/'.join(parts[3:])
        local_dir = f"/tmp/{uuid4().hex}"
        os.makedirs(local_dir)
        local_path = f"{local_dir}/{filename}"
        print(f"to local path {local_path}")
        self.s3.download_file(
            bucket,
            s3_path,
            local_path
        )
        return local_path

    @staticmethod
    def get_inputs():
        return {
            "build_artifacts_zip_s3uri": {
                "required": True,
                "type": "string",
                "description": "the S3 path to the zip file containing the Dockerfile and any other required files referenced from the Dockerfile",
            },
            "cpus": {
                "required": False,
                "type": "int",
                "description": "The number of CPUs to assign to the code execution container when it runs.",
                "default": 1
            },
            "entrypoint_path": {
                "required": False,
                "type": "string",
                "description": "An alternate entrypoint path to use instead of the default one built into the container.",
                "default": ""
            },
            "memory_mb": {
                "required": False,
                "type": "int",
                "description": "The number of megabytes of memory assigned to the code execution container.",
                "default": 128
            },
            "operation": {
                "required": True,
                "type": "str",
                "description": "The operation being called in the invocation. Currently only 'run_tool'.",
            },
        }

    @staticmethod
    def get_outputs():
        return {
            "results": {
                "s3_result_uri": "s3 URI to the output from the sandbox, zipped and uploaded to S3."
            }
        }

    def handler(self, evt):
        handler_evt = CodeSandboxToolEvent().from_lambda_event(evt)
        print(f"WebSearchToolEvent is now {handler_evt.__dict__}")
        uid = self.build_image(handler_evt.build_artifacts_s3_uri)
        result = self.run_tool(uid, handler_evt.entrypoint_path, handler_evt.memory_mb)
        print(f"Result from web search tool: {result}")
        return result

    def run_tool(self,
        uid,
        cpus=1,
        entrypoint_path='',
        memory_mb=128,
    ):
        args = [
            'nerdctl', 
            'run', 
            '-it',
            '--memory',
            memory_mb,
            '--cpus',
            1
        ]
        if entrypoint_path:
            args.append('--entrypoint')
            args.append(entrypoint_path)
        args.append(uid)
        subprocess.run(args)
        
    #     response = self.upload_code_artifact(cmd_script)
    #     scan_results = self.scan_code(response['codeArtifactId'], response['scanName'])
        
    #     if len(scan_results['findings']) == 0:
    #         executable = cmd_script_executable.split('/')[-1]
    #         cmd_script_extension = executables_to_extensions[executable]

    #         cmd_file = f"{tmp_folder}/cmd.{cmd_script_extension}"
    #         with open(cmd_file, "w") as f_out:
    #             f_out.write(cmd_script)
            
    #         subprocess.run([cmd_script_executable, cmd_file])
    #     else:
    #         print(f"scan of cmd_script got findings: {scan_results}.")
    #         raise Exception(f"[ERROR] cmd_script scan results had findings: {scan_results})")
        
    # def scan_code(self, code_artifact_id, scan_name):
    #     response = self.guru.create_scan(
    #         analysisType='Security',
    #         resourceId={
    #             'codeArtifactId': code_artifact_id
    #         },
    #         scanName=scan_name,
    #         scanType='Standard',
    #         # tags={
    #         #     'string': 'string'
    #         # }
    #     )
    #     print(f"response from create_scan: {response}")
    #     print(f"Got runId {response['runId']}")
    #     result = self.wait_for_scan_to_complete(response['runId'], scan_name)
    #     if result['scanState'] == 'Successful':
    #         return self.guru.get_findings(scanName=scan_name)
    #     else:
    #         raise Exception(f'ScanFailed: {result}')

    # def upload_code_artifact(self, code_contents):
    #     scanName = uuid4().hex
    #     response = self.guru.create_upload_url(
    #         scanName=scanName
    #     )
    #     response['scanName'] = scanName
    #     upload_response = requests.put(response['s3Url'], data=code_contents)
    #     print(f"Upload response {upload_response.__dict__}")
    #     return response

    # def wait_for_scan_to_complete(self, run_id, scan_name):
    #     response = self.guru.get_scan(run_id, scan_name)
    #     if response['scanState'] == 'InProgress':
    #         time.sleep(2)
    #         return self.wait_for_scan_to_complete(run_id, scan_name)
    #     else:
    #         return response
