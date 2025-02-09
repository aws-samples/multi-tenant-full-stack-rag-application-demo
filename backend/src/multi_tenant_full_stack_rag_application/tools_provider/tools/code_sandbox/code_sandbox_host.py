import boto3
import json
import logging
import os
import requests
import subprocess
import time
import zipfile 
from threading import Thread

from multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox.code_sandbox_host_event import CodeSandboxHostEvent

logging.basicConfig(filename='/var/log/codesandbox/codesandbox.log', level=logging.INFO)
logger = logging.getLogger(__name__)
csh = None

logger.info("Initializing code_sandbox_host.py.")


class CodeSandboxHost:
    def __init__(self):
        super().__init__()
        # all functions created must start with the prefix below 
        # self.guru = boto3.client('codeguru-security')
        # self.s3 = boto3.client('s3')
        logger.info("sandbox host initialized")

    # @param handler_evt:
    #   business_logic_code: str=''
    #   iac_code: str=''
    #   test_code: str=''      
    def build_image(self, handler_evt):
        tmpdir = handler_evt.tmpdir
        commands = handler_evt.tdd_command.split()
        commands.append(handler_evt.tdd_filename)
        image_id = tmpdir.split('/')[-1]
        dockerfile_contents = f"FROM {handler_evt.code_image}\n"
        dockerfile_contents += f"RUN mkdir {tmpdir}\n"
        # dockerfile_contents += f"RUN mkdir /tmp/containerd\n"
        # dockerfile_contents += f"RUN apt update && apt install -y\n"
        # dockerfile_contents += f"RUN wget https://github.com/containerd/nerdctl/releases/download/v1.5.0/nerdctl-1.5.0-linux-amd64.tar.gz\n"
        # dockerfile_contents += f"RUN tar -zxf nerdctl-1.5.0-linux-amd64.tar.gz nerdctl\n"
        # dockerfile_contents += f"RUN mv nerdctl /usr/bin/nerdctl\n"
        # dockerfile_contents += f"RUN rm nerdctl-1.5.0-linux-amd64.tar.gz\n"
        # dockerfile_contents += "RUN echo \"[grpc]\" >> /etc/containerd/config.toml\n"
        # dockerfile_contents += "RUN echo \"  address = \\\"/tmp/containerd/containerd.sock\\\"\" >> /etc/containerd/config.toml\n"
        # dockerfile_contents += "RUN cat /etc/containerd/config.toml\n"
        dockerfile_contents += f"RUN apt update\n"
        dockerfile_contents += f"RUN apt install --upgrade -y python3\n"
        dockerfile_contents += f"RUN python3 -m venv /app\n"
        dockerfile_contents += f"RUN /app/bin/python3 -m ensurepip\n"
        dockerfile_contents += f"RUN {handler_evt.install_tdd_reqs}\n"
        dockerfile_contents += f"COPY {handler_evt.business_logic_filename} {tmpdir}/\n"
        dockerfile_contents += f"COPY {handler_evt.tdd_filename} {tmpdir}/\n"
        dockerfile_contents += f"RUN ls -la {handler_evt.tdd_filename}\n"
        dockerfile_contents += f"CMD {json.dumps(commands)}\n"
        logger.info(f"Dockerfile contents:\n{dockerfile_contents}")
        with open(f"{tmpdir}/Dockerfile", "w") as f_out:
            f_out.write(dockerfile_contents)
                    
        args = [
            '/usr/bin/docker', 
            'build',
            '-t', 
            image_id, 
            '-f', 
            f"{tmpdir}/Dockerfile", 
            '/'
        ]
        logger.info(f"Running docker build with args {' '.join(args)}")
        proc_result = subprocess.run(args)
        logger.info(f"Got build_image proc result {proc_result}")
        
        return {
            "image_id": image_id,
            "stderr": proc_result.stderr,
            "stdout": proc_result.stdout,
            "exit_code": proc_result.returncode
        }
        
    @staticmethod
    def get_inputs():
        return {
            "comment": "Either iac_code is required or business_logic_code is required. tdd_code is optional.",
            "business_logic_code": {
                "required": "Either business_logic_code is required or iac_code. It's OK if both are sent.",
                "type": "string",
                "description": "The business logic code.",
            },
            "iac_code": {
                "required": "Either business_logic_code is required or iac_code.",
                "type": "string",
                "description": "The infrastructure code.",
            },
            "tdd_code": {
                "required": "Optional",
                "type": "string",
                "description": "The tdd code to run to tdd the business_logic_code. Always the same language as the business logic code."
            }
        }

    @staticmethod
    def get_outputs():
        return {
            "results": {
                "build": {
                    "stderr": "the error output from the docker build for the container.",
                    "stdout": "the standard output from the docker build for the container.",
                    "exit_code": "exit code from the docker build"
                },
                "tdd": {
                    "stderr": "the error output from the docker run for the container.",
                    "stdout": "the standard output from the docker run for the container.",
                    "exit_code": "exit code from the docker run"
                },
            }
        }

    def handler(self, evt):
        logger.info(f"CodeSandboxHost received Lambda event {evt}")
        handler_evt = CodeSandboxHostEvent(**evt.__dict__)
        logger.info(f"CodeSandboxHostEvent is now {handler_evt.__dict__}")
        build_results = self.build_image(handler_evt)
        logger.info(f"Got build_results {build_results}")
        if build_results['exit_code'] != 0:
            raise Exception(f"build_image failed: {build_results}")

        result = {
            "build": build_results
        }
        tdd_results = self.run_tool(
            build_results['image_id'], 
            handler_evt.cpus, 
            handler_evt.entrypoint_path,
            handler_evt.memory_mb
        )
        if tdd_results['exit_code'] != 0:
            raise Exception(f"run_tool failed: {tdd_results}")

        result['tdd'] = tdd_results

        logger.info(f"Result from code_sandbox_tool: {result}")
        
        return result

    def run_tool(self,
        image_id,
        cpus=1,
        entrypoint_path='',
        memory_mb=128,
    ):
        print(f"Run tool got memory {memory_mb}")
        args = [
            "/usr/bin/docker", 
            "run"
        ]
        # if entrypoint_path:
        #     args.append('--entrypoint')
        #     args.append(entrypoint_path)
        # the image_id here is the name tag of the
        # container built above. It should be the
        # last argument for the docker run command
        args.append(image_id)
        logger.info(f"Running tool with args: {args}")
        # don't append any more to args between the
        # two lines above and below this comment.
        try:
            logger.info(f"Running docker run with args {' '.join(args)}")
            proc_result = subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            logger.info(f"Got run_tool proc result {proc_result.__dict__}")                
            return {
                "image_id": image_id,
                "stderr": proc_result.stderr,
                "stdout": proc_result.stdout,
                "exit_code": proc_result.returncode
            }
        except Exception as e:
            logger.error(f"Got exception {e}")
            raise e
    
    # def start_containerd(self):
    #     logger.info("Starting containerd...")
    #     subprocess.Popen([
    #         'containerd',
    #         '-a',
    #         '/tmp/containerd/containerd.sock',
    #         '--root',
    #         '/tmp/containerd-root',
    #         '--state',
    #         '/tmp/containerd-state'
    #     ])
    #     logger.info(f"containerd started")
    #     # response = self.upload_code_artifact(cmd_script)
    #     # scan_results = self.scan_code(response['codeArtifactId'], response['scanName'])
        
    #     # if len(scan_results['findings']) == 0:
    #     #     executable = cmd_script_executable.split('/')[-1]
    #     #     cmd_script_extension = executables_to_extensions[executable]

    #     #     cmd_file = f"{tmp_folder}/cmd.{cmd_script_extension}"
    #     #     with open(cmd_file, "w") as f_out:
    #     #         f_out.write(cmd_script)
            
    #     #     subprocess.run([cmd_script_executable, cmd_file])
    #     # else:
    #     #     logger.info(f"scan of cmd_script got findings: {scan_results}.")
    #     #     raise Exception(f"[ERROR] cmd_script scan results had findings: {scan_results})")
        
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
    #     logger.info(f"response from create_scan: {response}")
    #     logger.info(f"Got runId {response['runId']}")
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
    #     logger.info(f"Upload response {upload_response.__dict__}")
    #     return response

    # def wait_for_scan_to_complete(self, run_id, scan_name):
    #     response = self.guru.get_scan(run_id, scan_name)
    #     if response['scanState'] == 'InProgress':
    #         time.sleep(2)
    #         return self.wait_for_scan_to_complete(run_id, scan_name)
    #     else:
    #         return response


def handler(evt, ctx):
    global csh
    logger.info(f"code_sandbox_host.handler got event {evt}")
    orig_evt = evt.copy()

    if not csh:
        csh = CodeSandboxHost()
    if 'node' in evt and 'inputs' in evt['node']:
        # this came from a bedrock prompt flow so the format
        # is a little different than in this stack. Modify
        # it a bit before passing it on.
        evt = {}
        for input_dict in orig_evt['node']['inputs']:
            evt[input_dict['name']] = input_dict['value']

    return csh.handler(evt)
