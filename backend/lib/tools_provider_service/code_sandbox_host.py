from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3_assets as s3_assets,
    BundlingFileAccess,
    BundlingOptions,
    BundlingOutput,
    DockerImage,
    NestedStack,
    CfnOutput
)

from constructs import Construct


class CodeSandboxHost(NestedStack):
    def __init__(self, scope: Construct, construct_id: str,
        app_security_group: ec2.ISecurityGroup,
        parent_stack_name: str,
        vpc: ec2.IVpc,
        **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        build_cmds = [
            "zip -r /asset-output/mtfsrad.zip /asset-input/multi_tenant_full_stack_rag_application/utils/*.{py,txt}",
            "zip -r /asset-output/mtfsrad.zip /asset-input/multi_tenant_full_stack_rag_application/tools_provider/*.py",
            "zip -r /asset-output/mtfsrad.zip /asset-input/tools_provider/tools/*.py",
            "zip -r /asset-output/mtfsrad.zip /asset-input/tools_provider/tools/code_sandbox_tool_v2/*.{py,txt}",
        ]
        asset = s3_assets.Asset(self, "CodeSandboxAsset",
            path="src/multi_tenant_full_stack_rag_application",
            bundling=BundlingOptions(
                image=DockerImage.from_registry("debian"),
                command=[
                    "bash", "-c", " && ".join(build_cmds)
                ],
                output_type=BundlingOutput.ARCHIVED
            )
        )
        # Create the CDK resource for an EC2 instance running Amazon Linux 2023
        code_sandbox_host = ec2.Instance(
            self,
            "CodeSandboxHost",
            block_devices=[ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(10, encrypted=True),
            )],
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,
                ec2.InstanceSize.MICRO,
            ),
            machine_image=ec2.MachineImage.generic_linux(
                # generic debian on ARM
                ami_map={
                    'us-east-1': 'ami-0789039e34e739d67',
                    'us-west-2': 'ami-036566e195ea889e5'
                }
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
                "CodeSandboxHostRole",
                assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AmazonSSMManagedInstanceCore"
                    ),
                ]
            ),
            init=ec2.CloudFormationInit.from_elements(
                ec2.InitCommand.shell_command('apt update && apt install curl unzip python3 podman -y'),
                ec2.InitCommand.shell_command('python3 -m ensurepip'),
                ec2.InitUser.from_name("sandbox", home_dir='/app'),
                ec2.InitCommand.shell_command('cd /app && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"'),
                ec2.InitCommand.shell_command('cd /app && unzip awscliv2.zip'),
                ec2.InitCommand.shell_command('cd /app && ./aws/install'),
                ec2.InitCommand.shell_command(f'echo {asset.s3_object_url} > /app/s3_object_uri.txt'),
                ec2.InitSource.from_s3_object("/app", asset.s3_bucket_name, asset.s3_object_key),
                ec2.InitCommand.shell_command('chown -R sandbox:sandbox /app'),
                ec2.InitCommand.shell_command('pip3 install -t /app -r /app/multi_tenant_full_stack_rag_application/utils/utils_requirements.txt'),
                ec2.InitCommand.shell_command('pip3 install -t /app -r /app/multi_tenant_full_stack_rag_application/tools_provider/tools/code_sandbox_tool_v2/requirements_code_sandbox_tool.txt'),
            ),
        )
        code_sandbox_host.add_to_role_policy(iam.PolicyStatement(
            actions=["s3:GetObject"],
            resources=[f"{asset.bucket.bucket_arn}/{asset.s3_object_key}"]
        ))
                    
                
        