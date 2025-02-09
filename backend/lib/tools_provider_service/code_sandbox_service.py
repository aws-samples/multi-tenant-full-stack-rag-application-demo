from aws_cdk import (
  aws_bedrock as bedrock,
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_lambda as lambda_,
  aws_s3_assets as s3_assets,
  aws_ssm as ssm,
  BundlingFileAccess,
  BundlingOptions,
  BundlingOutput,
  DockerImage,
  Duration,
  NestedStack,
  CfnOutput
)

from constructs import Construct

from lib.tools_provider_service.prompts.architect import prompt as architect_prompt
from lib.tools_provider_service.prompts.business_logic_dev import prompt as business_logic_dev_prompt
from lib.tools_provider_service.prompts.iac_dev import prompt as iac_dev_prompt
from lib.tools_provider_service.prompts.loop_orchestrator import prompt as loop_orchestrator_prompt
from lib.tools_provider_service.prompts.tdd_dev import prompt as tdd_dev_prompt
import json


class CodeSandboxService(NestedStack):
    def __init__(self, scope: Construct, construct_id: str,
        app_security_group: ec2.ISecurityGroup,
        parent_stack_name: str,
        vpc: ec2.IVpc,
        **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        build_cmds = [
            "apt update && apt install zip -y",
            "cd /asset-input/",
            "zip -r /asset-output/mtfsrad.zip . -i multi_tenant_full_stack_rag_application/utils/*.{py,txt}",
            "zip -r /asset-output/mtfsrad.zip . -i multi_tenant_full_stack_rag_application/tools_provider/*.py",
            "zip -r /asset-output/mtfsrad.zip . -i multi_tenant_full_stack_rag_application/tools_provider/tools/*.py",
            "zip -r /asset-output/mtfsrad.zip . -i multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox/*.{py,txt}",
            "chown 1000:1000 /asset-output/mtfsrad.zip"
        ]
        asset = s3_assets.Asset(self, "CodeSandboxAssetv1.43",
            path="src",
            bundling=BundlingOptions(
                user="root",
                image=DockerImage.from_registry("debian"),
                command=[
                    "bash", "-c", " && ".join(build_cmds)
                ],
                output_type=BundlingOutput.ARCHIVED
            )
        )
        handle = ec2.InitServiceRestartHandle()
        # Create the CDK resource for an EC2 instance running Amazon Linux 2023
        code_sandbox_host = ec2.Instance(
            self,
            "CodeSandboxEc2Host1.43",
            block_devices=[ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(100, encrypted=True),
            )],
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.SMALL,
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(
                cpu_type=ec2.AmazonLinuxCpuType.X86_64
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            # Allow the instance to connect to the app
            security_group=app_security_group,
            # Allow the instance to connect to the app
            role=iam.Role(
                self,
                "CodeSandboxHostV2Role",
                assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AmazonSSMManagedInstanceCore"
                    ),
                ]
            ),
            init=ec2.CloudFormationInit.from_elements(
                ec2.InitCommand.shell_command('dnf install unzip python3 wget docker amazon-cloudwatch-agent augeas-libs -y'),
                ec2.InitCommand.shell_command('python3 -m ensurepip'),
                ec2.InitCommand.shell_command('pip3 install --upgrade pip'),
                ec2.InitGroup.from_name('docker'),
                ec2.InitGroup.from_name('sandbox'),
                ec2.InitCommand.shell_command('systemctl enable docker && systemctl start docker'),
                ec2.InitCommand.shell_command("useradd -g sandbox -G docker -d /app sandbox"),
                ec2.InitCommand.shell_command(f'echo {asset.s3_object_url} > /app/s3_object_uri.txt'),
                ec2.InitSource.from_s3_object("/app", asset.bucket, asset.s3_object_key),
                ec2.InitCommand.shell_command('chown -R sandbox:sandbox /app'),
                ec2.InitCommand.shell_command('python3 -m venv /app'),
                ec2.InitCommand.shell_command('/app/bin/python3 -m ensurepip'),
                ec2.InitCommand.shell_command('/app/bin/pip3 install --upgrade -r /app/multi_tenant_full_stack_rag_application/utils/utils_requirements.txt'),
                ec2.InitCommand.shell_command('/app/bin/pip3 install --upgrade -r /app/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox/requirements_code_sandbox_host.txt'),
                # ec2.InitCommand.shell_command('/app/bin/pip3 install fastapi[standard] certbot certbot-dns-route53'),
                ec2.InitCommand.shell_command('ln -s /app/bin/certbot /usr/bin/certbot'),
                ec2.InitFile.from_string('/etc/letsencrypt/cli.ini', f"""
# This is an example of the kind of things you can do in a configuration file.
# All flags used by the client can be configured here. Run Certbot with
# "--help" to learn more about the available options.
#
# Note that these options apply automatically to all use of Certbot for
# obtaining or renewing certificates, so opt
# ions specific to a single
# certificate on a system with several certificates should not be placed
# here.

# Use ECC for the private key
key-type = ecdsa
elliptic-curve = secp384r1

# Use a 4096 bit RSA key instead of 2048
rsa-key-size = 4096

# Uncomment and update to register with the specified e-mail address
email = foo@example.com

# Uncomment to use the standalone authenticator on port 443
# authenticator = standalone

# Uncomment to use the webroot authenticator. Replace webroot-path with the
# path to the public_html / webroot folder being served by your web server.
# authenticator = webroot
# webroot-path = /usr/share/nginx/html

# Uncomment to automatically agree to the terms of service of the ACME server
# agree-tos = true

# An example of using an alternate ACME server that uses EAB credentials
# server = https://acme.sectigo.com/v2/InCommonRSAOV
# eab-kid = somestringofstuffwithoutquotes
# eab-hmac-key = yaddayaddahexhexnotquoted
"""),
                ec2.InitCommand.shell_command('su - sandbox -c "touch /app/.bash_profile"'),
                ec2.InitCommand.shell_command('su - sandbox -c "cd /app && curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"'),
                ec2.InitCommand.shell_command('su - sandbox -c "source ~/.bash_profile && nvm install 20"'),
                ec2.InitCommand.shell_command('su - sandbox -c "echo nvm use 20 >> ~/.bash_profile"'),
                ec2.InitCommand.shell_command('su - sandbox -c "export APP_HOME=/app >> /app/.bash_profile"'),
                ec2.InitCommand.shell_command('su - sandbox -c "source ~/.bash_profile &&  npm install -g aws-cdk"'),
                ec2.InitFile.from_string('/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json', """{
    "agent": {
      "metrics_collection_interval": 10,
      "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
    },
    "metrics": {
      "namespace": "MTFSRAD-EC2-Metrics",
      "metrics_collected": {
        "cpu": {
          "resources": [
            "*"
          ],
          "measurement": [
            {"name": "cpu_usage_idle", "rename": "CPU_USAGE_IDLE", "unit": "Percent"},
            {"name": "cpu_usage_nice", "unit": "Percent"},
            "cpu_usage_guest"
          ],
          "totalcpu": false,
          "metrics_collection_interval": 10
        },
        "disk": {
          "resources": [
            "/",
            "/tmp"
          ],
          "measurement": [
            {"name": "free", "rename": "DISK_FREE", "unit": "Gigabytes"},
            "total",
            "used"
          ],
           "ignore_file_system_types": [
            "sysfs", "devtmpfs"
          ],
          "metrics_collection_interval": 60
        },
        "diskio": {
          "resources": [
            "*"
          ],
          "measurement": [
            "reads",
            "writes",
            "read_time",
            "write_time",
            "io_time"
          ],
          "metrics_collection_interval": 60
        },
        "swap": {
          "measurement": [
            "swap_used",
            "swap_free",
            "swap_used_percent"
          ]
        },
        "mem": {
          "measurement": [
            "mem_used",
            "mem_cached",
            "mem_total"
          ],
          "metrics_collection_interval": 1
        },
        "net": {
          "resources": [
            "eth0"
          ],
          "measurement": [
            "bytes_sent",
            "bytes_recv",
            "drop_in",
            "drop_out"
          ]
        },
        "netstat": {
          "measurement": [
            "tcp_established",
            "tcp_syn_sent",
            "tcp_close"
          ],
          "metrics_collection_interval": 60
        },
        "processes": {
          "measurement": [
            "running",
            "sleeping",
            "dead"
          ]
        }
      },
      "append_dimensions": {
        "ImageId": "${aws:ImageId}",
        "InstanceId": "${aws:InstanceId}",
        "InstanceType": "${aws:InstanceType}",
        "AutoScalingGroupName": "${aws:AutoScalingGroupName}"
      },
      "aggregation_dimensions" : [["ImageId"], ["InstanceId", "InstanceType"], ["d1"],[]],
      "force_flush_interval" : 30
    },
    "logs": {
      "logs_collected": {
        "files": {
          "collect_list": [
            {
              "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
              "log_group_name": "amazon-cloudwatch-agent.log",
              "log_stream_name": "amazon-cloudwatch-agent.log",
              "timezone": "UTC"
            },
            {
              "file_path": "/var/log/codesandbox/*",
              "log_group_name": "mtfsrad-codesandbox",
              "log_stream_name": "${instance_id}",
              "timezone": "Local"
            }
          ]
        }
      },
      "log_stream_name": "mtfsrad-ec2-logs",
      "force_flush_interval" : 16
  }
}"""),
                ec2.InitCommand.shell_command("/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"),
                ec2.InitCommand.shell_command('mkdir /var/log/codesandbox && chown -R sandbox:sandbox /var/log/codesandbox'),
                # ec2.InitCommand.shell_command("touch /var/log/codesandbox/codesandbox.log"),
                ec2.InitFile.from_string('/etc/systemd/system/codesandbox.service', """
[Unit]
Description=CodeSandboxService
After=network.target

[Service]
User=sandbox
Group=sandbox
Type=simple
Environment="PYTHONPATH=/app"
Environment="APP_HOME=/app"
ExecStart=/app/bin/fastapi run api_server.py
Restart=always
RestartSec=5
WorkingDirectory=/app/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox
StandardOutput=inherit
StandardError=inherit
[Install]
WantedBy=default.target
"""),
                # TODO: Fix this so the sandbox doesn't need to own the app files, just a tmp dir
                # needs to be coordinated with the docker build command in the code_sandbox_host.py file.
                ec2.InitCommand.shell_command("chown -R sandbox:sandbox /app"),
                ec2.InitService.enable("codesandbox",
                    service_restart_handle=handle
                )
            )
        )
        code_sandbox_host.add_to_role_policy(iam.PolicyStatement(
            actions=["s3:GetObject"],
            resources=[f"{asset.bucket.bucket_arn}/{asset.s3_object_key}"]
        ))
        code_sandbox_host.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "cloudwatch:PutMetricData",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams",
                "ec2:DescribeTags",
            ],
            resources=["*"]
        ))

        # deploy code sandbox service Bedrock prompts
        architect = bedrock.CfnPrompt(self, "ArchitectPrompt",
          name=f"{parent_stack_name}_code_sandbox_architect",
          # the properties below are optional
          variants=[bedrock.CfnPrompt.PromptVariantProperty(
              name="default",
              template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                  text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                      text=architect_prompt["text"],
                      input_variables=[bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="use_case_details"
                      )]
                  )
              ),
              template_type="TEXT",
              inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                  text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                      max_tokens=architect_prompt['max_tokens'],
                      stop_sequences=architect_prompt["stop_seqs"],
                      temperature=architect_prompt['temperature'],
                      top_p=architect_prompt['top_p']
                  )
              ),
              model_id=architect_prompt['model']
          )]
        )
        architect_prompt['id'] = architect.attr_id

        business_logic_dev = bedrock.CfnPrompt(self, "BusinessLogicDevPrompt",
          name=f"{parent_stack_name}_code_sandbox_business_logic_dev",
          # the properties below are optional
          variants=[bedrock.CfnPrompt.PromptVariantProperty(
              name="default",
              template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                  text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                      text=business_logic_dev_prompt["text"],
                      input_variables=[
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="use_case_details"
                        ),
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="architecture_plan"
                        )
                      ]
                  )
              ),
              template_type="TEXT",
              inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                  text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                      max_tokens=business_logic_dev_prompt['max_tokens'],
                      stop_sequences=business_logic_dev_prompt["stop_seqs"],
                      temperature=business_logic_dev_prompt['temperature'],
                      top_p=business_logic_dev_prompt['top_p']
                  )
              ),
              model_id=business_logic_dev_prompt['model']
          )]
        )
        business_logic_dev_prompt['id'] = business_logic_dev.attr_id

        iac_dev = bedrock.CfnPrompt(self, "IacDevPrompt",
          name=f"{parent_stack_name}_code_sandbox_iac_dev",
          # the properties below are optional
          variants=[bedrock.CfnPrompt.PromptVariantProperty(
              name="default",
              template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                  text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                      text=iac_dev_prompt["text"],
                      input_variables=[
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="use_case_details"
                        ),
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="architecture_plan"
                        ),
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="business_logic_code"
                        )
                      ]
                  )
              ),
              template_type="TEXT",
              inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                  text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                      max_tokens=iac_dev_prompt['max_tokens'],
                      stop_sequences=iac_dev_prompt["stop_seqs"],
                      temperature=iac_dev_prompt['temperature'],
                      top_p=iac_dev_prompt['top_p']
                  )
              ),
              model_id=iac_dev_prompt['model']
          )]
        )

        iac_dev_prompt['id'] = iac_dev.attr_id

        loop_orchestrator = bedrock.CfnPrompt(self, "LoopOrchestratorPrompt",
          name=f"{parent_stack_name}_code_sandbox_loop_orchestrator",
          # the properties below are optional
          variants=[bedrock.CfnPrompt.PromptVariantProperty(
              name="default",
              template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                  text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                      text=loop_orchestrator_prompt["text"],
                      input_variables=[
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="business_logic_code"
                        ),
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="iac_code"
                        ),
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="previous_results"
                        ),
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="tdd_code"
                        ),
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="use_case_details"
                        ),
                      ]
                  )
              ),
              template_type="TEXT",
              inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                  text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                      max_tokens=loop_orchestrator_prompt['max_tokens'],
                      stop_sequences=loop_orchestrator_prompt["stop_seqs"],
                      temperature=loop_orchestrator_prompt['temperature'],
                      top_p=loop_orchestrator_prompt['top_p']
                  )
              ),
              model_id=loop_orchestrator_prompt['model']
          )]
        )
        loop_orchestrator_prompt['id'] = loop_orchestrator.attr_id

        tdd_dev = bedrock.CfnPrompt(self, "TddDevPrompt",
          name=f"{parent_stack_name}_code_sandbox_tdd_dev",
          # the properties below are optional
          variants=[bedrock.CfnPrompt.PromptVariantProperty(
              name="default",
              template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                  text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                      text=tdd_dev_prompt["text"],
                      input_variables=[
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="use_case_details"
                        ),
                        bedrock.CfnPrompt.PromptInputVariableProperty(
                          name="business_logic_code"
                        )
                      ]
                  )
              ),
              template_type="TEXT",
              inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                  text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                      max_tokens=tdd_dev_prompt['max_tokens'],
                      stop_sequences=tdd_dev_prompt["stop_seqs"],
                      temperature=tdd_dev_prompt['temperature'],
                      top_p=tdd_dev_prompt['top_p']
                  )
              ),
              model_id=tdd_dev_prompt['model']
          )]
        )
        tdd_dev_prompt['id'] = tdd_dev.attr_id

        build_cmds = [
            "pip3 install -t /asset-output requests",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox/',
            "cp /asset-input/tools_provider/tools/*.py /asset-output/multi_tenant_full_stack_rag_application/tools_provider/tools/",
            "cp /asset-input/tools_provider/tools/code_sandbox/*.py /asset-output/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox/",
            'pip3 install -t /asset-output -r /asset-input/utils/utils_requirements.txt',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils/',
            'pip3 install -t /asset-output -r /asset-input/tools_provider/tools/code_sandbox/requirements_code_sandbox_tool.txt',
            "cp -r /asset-input/utils/* /asset-output/multi_tenant_full_stack_rag_application/utils/",
        ]
        
        self.code_sandbox_runner_function = lambda_.Function(self, 'CodeSandboxRunnerFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.ARM_64,
            handler='multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox.code_sandbox.handler',
            timeout=Duration.seconds(900),
            environment={
                "STACK_NAME": parent_stack_name,
                "CODE_SANDBOX_HOST": code_sandbox_host.instance_private_ip,
                "APP_HOME": "/var/task"
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[app_security_group]
        )
        
        self.code_sandbox_runner_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:Invoke*",
                ],
                resources=["*"],
            )
        )
        code_sandbox_runner_fn_name_param = ssm.StringParameter(self, 'CodeSandboRunnerFnParamName',
            parameter_name=f'/{parent_stack_name}/code_sandbox_runner_function_name',
            string_value=self.code_sandbox_runner_function.function_name
        )

        build_cmds = [
            "pip3 install -t /asset-output requests",
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox/',
            "cp /asset-input/tools_provider/tools/*.py /asset-output/multi_tenant_full_stack_rag_application/tools_provider/tools/",
            "cp /asset-input/tools_provider/tools/code_sandbox/*.py /asset-output/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox/",
            'pip3 install -t /asset-output -r /asset-input/utils/utils_requirements.txt',
            'mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils/',
            'pip3 install -t /asset-output -r /asset-input/tools_provider/tools/code_sandbox/requirements_code_sandbox_tool.txt',
            "cp -r /asset-input/utils/* /asset-output/multi_tenant_full_stack_rag_application/utils/",
        ]
        
        self.code_sandbox_orchestrator_function = lambda_.Function(self, 'CodeSandboxOrchestratorFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application/',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join(build_cmds)
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.ARM_64,
            handler='multi_tenant_full_stack_rag_application.tools_provider.tools.code_sandbox.code_sandbox_orchestrator.handler',
            timeout=Duration.seconds(900),
            environment={
                "STACK_NAME": parent_stack_name,
                "CODE_SANDBOX_HOST": code_sandbox_host.instance_private_ip,
                "APP_HOME": "/var/task",
                "PROMPTS": json.dumps({
                    "architect": architect_prompt['id'],
                    "business_logic_dev": business_logic_dev_prompt['id'],
                    "iac_dev": iac_dev_prompt['id'],
                    "loop_orchestrator": loop_orchestrator_prompt['id'],
                    "tdd_dev": tdd_dev_prompt['id']
                })
            },
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[app_security_group]
        )
        
        self.code_sandbox_orchestrator_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:Invoke*",
                ],
                resources=["*"],
            )
        )

        code_sandbox_orchestrator_fn_name_param = ssm.StringParameter(self, 'CodeSandboxOrchestratorFnNameParam',
            parameter_name=f'/{parent_stack_name}/code_sandbox_orchestrator_function_name',
            string_value=self.code_sandbox_runner_function.function_name
        )

        code_sandbox_orchestrator_origin_param = ssm.StringParameter(self, 'CodeSandboxOrchestratorOriginParam',
            parameter_name=f'/{parent_stack_name}/origin_code_sandbox_orchestrator',
            string_value=self.code_sandbox_runner_function.function_name
        )
        