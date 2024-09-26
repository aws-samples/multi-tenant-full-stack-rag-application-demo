#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    BundlingFileAccess,
    BundlingOptions,
    Duration,
    RemovalPolicy,
    Size,
    NestedStack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_opensearchservice as aos,
    aws_ssm as ssm,
)
from aws_cdk.aws_cognito import UserPool, UserPoolDomain
from aws_cdk.aws_cognito_identitypool_alpha import IdentityPool
from constructs import Construct

from lib.shared.opensearch_access_policy import OpenSearchAccessPolicy


class OpenSearchManagedStack(NestedStack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        auth_fn: lambda_.IFunction,
        auth_role_arn: str,
        cognito_identity_pool: IdentityPool,
        cognito_user_pool: UserPool,
        os_data_instance_ct: int,
        os_data_instance_type: str,
        os_data_instance_volume_size_gb: int,
        os_master_instance_ct: int,
        os_master_instance_type: str,
        os_multiaz_with_standby_enabled: bool,
        os_dashboards_ec2_cert_country: str,
        os_dashboards_ec2_cert_state: str,
        os_dashboards_ec2_cert_city: str,
        os_dashboards_ec2_cert_email_address: str,
        os_dashboards_ec2_cert_hostname: str,
        os_dashboards_ec2_enable_traffic_from_ip: str,
        parent_stack_name: str,
        user_pool_domain: UserPoolDomain,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # inference_role = iam.Role.from_role_arn(self, 'InferenceRoleRef', inference_role_arn)
        # ingestion_role = iam.Role.from_role_arn(self, 'IngestionRoleRef', ingestion_role_arn)

        cognito_dashboards_role = iam.Role(
            self, 
            'OpenSearchDashboardsCognitoRole',
            assumed_by=iam.ServicePrincipal('opensearchservice.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, 
                    'OsCognitoAccessPolicy',
                    'arn:aws:iam::aws:policy/AmazonOpenSearchServiceCognitoAccess'
                )
            ],
        )
        cognito_dashboards_role.assume_role_policy.add_statements(iam.PolicyStatement(
            actions=['sts:AssumeRole'],
            principals=[
                iam.ServicePrincipal('es.amazonaws.com'),
            ]
        ))

        self.domain = aos.Domain(self, 'OsDomain', 
            version=aos.EngineVersion.OPENSEARCH_2_7,
            capacity={
                "data_node_instance_type": os_data_instance_type,
                "data_nodes": os_data_instance_ct,
                "master_node_instance_type": os_master_instance_type,
                "master_nodes": os_master_instance_ct,
                "multi_az_with_standby_enabled": os_multiaz_with_standby_enabled
            },
            cognito_dashboards_auth={
                "identity_pool_id": cognito_identity_pool.identity_pool_id,
                "user_pool_id": cognito_user_pool.user_pool_id,
                "role": cognito_dashboards_role
            },
            ebs={
                "volume_size": os_data_instance_volume_size_gb,
                "volume_type": ec2.EbsDeviceVolumeType.GP3
            },
            enable_auto_software_update=True,
            enforce_https=True,
            node_to_node_encryption=True,
            encryption_at_rest={
                "enabled": True
            },
            removal_policy=RemovalPolicy(
                self.node.get_context('removal_policy')
            ),
            security_groups=[app_security_group],
            vpc=vpc,
            vpc_subnets=[{
                "subnetType": ec2.SubnetType.PRIVATE_ISOLATED
            }],
            zone_awareness={
                "enabled": True,
                "availability_zone_count": 2,
            }
        )
        
        OpenSearchAccessPolicy(self, "OpenSearchCognitoDashboardsAccess",
            self.domain,
            cognito_dashboards_role.grant_principal,
            True, True, True, True
        )
        
        self.vector_store_endpoint = self.domain.domain_endpoint

        self.vector_store_provider = lambda_.Function(self, 'VectorStoreProviderFunction',
            code=lambda_.Code.from_asset('src/multi_tenant_full_stack_rag_application',
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    bundling_file_access=BundlingFileAccess.VOLUME_COPY,
                    command=[
                        "bash", "-c", " && ".join([
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
                            "cp /asset-input/vector_store_provider/*.py /asset-output/multi_tenant_full_stack_rag_application/vector_store_provider",
                            "mkdir -p /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "cp /asset-input/utils/*.py /asset-output/multi_tenant_full_stack_rag_application/utils",
                            "pip3 install -r /asset-input/utils/utils_requirements.txt -t /asset-output",
                            "pip3 install -r /asset-input/vector_store_provider/opensearch_requirements.txt -t /asset-output"
                        ])
                    ]
                )
            ),
            memory_size=128,
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=lambda_.Architecture.X86_64,
            handler='multi_tenant_full_stack_rag_application.vector_store_provider.opensearch_vector_store_provider.handler',
            timeout=Duration.seconds(60),
            environment={
                'STACK_NAME': parent_stack_name,
                'VECTOR_STORE_ENDPOINT': self.vector_store_endpoint,
                # 'AWS_ACCOUNT_ID': self.account,
                # 'IDENTITY_POOL_ID': identity_pool_id,
                # 'USER_POOL_ID': user_pool_id,
                # 'USER_SETTINGS_TABLE': user_settings_table.table_name
            }
        )

        self.vector_store_provider.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction",
                ],
                resources=[auth_fn.function_arn],
            )
        )

        self.vector_store_provider.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['ssm:GetParameter','ssm:GetParametersByPath'],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/{parent_stack_name}*",            
            ]
        ))

        cognito_auth_role = iam.Role.from_role_arn(self, 'CognitoAuthRoleRef', auth_role_arn)

        self.vector_store_provider.grant_invoke(cognito_auth_role)

        OpenSearchAccessPolicy(self, 'OpenSearchAccessForCognitoRole',
            self.domain,
            cognito_auth_role.grant_principal,
            True, True, True, True
        )

        vs_fn_name = ssm.StringParameter(self, 'VectorStoreProviderFunctionName',
            parameter_name=f'/{parent_stack_name}/vector_store_provider_function_name',
            string_value=self.vector_store_provider.function_name
        )

        vs_fn_name.apply_removal_policy(RemovalPolicy.DESTROY)
        
        vs_origin_param = ssm.StringParameter(self, 'VectorStoreProviderOrigin',
            parameter_name=f'/{parent_stack_name}/origin_vector_store_provider',
            string_value=self.vector_store_provider.function_name
        )

        vs_origin_param.apply_removal_policy(RemovalPolicy.DESTROY)
        
        # Now do the OpenSearch Dashboards Proxy. Comment
        # this section out if you don't want it.
        handle = ec2.InitServiceRestartHandle()

        app_security_group.add_ingress_rule(
            ec2.Peer.ipv4(os_dashboards_ec2_enable_traffic_from_ip),
            ec2.Port.HTTPS
        )

        self.bastion_host = ec2.BastionHostLinux(self, 'OpenSearchDashboardsHost', 
            vpc=vpc,
            block_devices=[ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(10, encrypted=True),
            )],
            instance_name="OpenSearchDashboardsProxy",
            security_group=app_security_group,
            # CHANGE_PUBLIC_SUBNET_TO_ISOLATED if you want to
            # change the code to only use isolated subnets,
            # then search for all comments with 
            # CHANGE_PUBLIC_SUBNET_TO_ISOLATED
            # and change them from ec2.SubnetType.PUBLIC to ec2.SubnetType.PRIVATE_ISOLATED
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            init=ec2.CloudFormationInit.from_elements(
                ec2.InitCommand.shell_command('amazon-linux-extras install nginx1 -y'),
                ec2.InitFile.from_string(
                    '/etc/nginx/conf.d/default.conf',
                    """
                    server {{
                        listen 443;
                        server_name $host;
                        rewrite ^/$ https://$host/_dashboards redirect;
                        resolver <SUBNET_RESOLVER_IP> ipv6=off valid=5s;
                        set $domain_endpoint {domain_endpoint};
                        set $cognito_host {cognito_domain_name}.auth.{region}.amazoncognito.com;
                        
                        ssl_certificate           /etc/nginx/cert.crt;
                        ssl_certificate_key       /etc/nginx/cert.key;
                        
                        ssl on;
                        ssl_session_cache  builtin:1000  shared:SSL:10m;
                        ssl_protocols  TLSv1 TLSv1.1 TLSv1.2;
                        ssl_ciphers HIGH:!aNULL:!eNULL:!EXPORT:!CAMELLIA:!DES:!MD5:!PSK:!RC4;
                        ssl_prefer_server_ciphers on;
                        
                        location ^~ /_dashboards {{
                        
                            # Forward requests to Dashboards
                            proxy_pass https://$domain_endpoint;
                        
                            # Handle redirects to Cognito
                            proxy_redirect https://$cognito_host https://$host;
                        
                            # Handle redirects to Dashboards
                            proxy_redirect https://$domain_endpoint https://$host;
                        
                            # Update cookie domain and path
                            proxy_cookie_domain $domain_endpoint $host;
                            proxy_cookie_path ~*^/$ /_dashboards/;
                        
                            # Response buffer settings
                            proxy_buffer_size 128k;
                            proxy_buffers 4 256k;
                            proxy_busy_buffers_size 256k;
                        }}
                        
                        location ~ \/(log|sign|fav|forgot|change|saml|oauth2|confirm) {{
                        
                            # Forward requests to Cognito
                            proxy_pass https://$cognito_host;
                        
                            # Handle redirects to Dashboards
                            proxy_redirect https://$domain_endpoint https://$host;
                        
                            # Handle redirects to Cognito
                            proxy_redirect https://$cognito_host https://$host;
                        
                            proxy_cookie_domain $cognito_host $host;
                        }}

                        location ^~ /_aos {{
                            # Forward requests to AOS endpoint
                            proxy_pass https://$domain_endpoint;
                        
                            # Handle redirects to AOS endpoint
                            proxy_redirect https://$domain_endpoint https://$host;
                        
                            # Update cookie domain and path
                            proxy_cookie_domain $domain_endpoint $host;
                            proxy_cookie_path ~*^/$ /_aos/;
                        
                            # Response buffer settings
                            proxy_buffer_size 128k;
                            proxy_buffers 4 256k;
                            proxy_busy_buffers_size 256k;
                        }}
                    }}
                    """.format(
                        domain_endpoint=self.domain.domain_endpoint,
                        cognito_domain_name=user_pool_domain.domain_name,
                        region=self.region
                    ),
                    service_restart_handles=[handle] 
                ),
                ec2.InitFile.from_string(
                    '/tmp/ec2_cert_info.cfg',
                    """[ req ]
                    prompt                 = no
                    default_bits           = 2048
                    default_keyfile        = privkey.pem
                    distinguished_name     = req_distinguished_name
                    x509_extensions        = v3_ca
                    
                    dirstring_type = nobmp
                    
                    [ req_distinguished_name ]
                    countryName                    = {country}
                    stateOrProvinceName            = {state}
                    localityName                   = {city}
                    commonName                     = {hostname}
                    emailAddress                   = {email}
                    
                    
                    [ v3_ca ]
                    
                    subjectKeyIdentifier=hash
                    authorityKeyIdentifier=keyid:always,issuer:always
                    basicConstraints = CA:true
                    """.format(
                        country=os_dashboards_ec2_cert_country,
                        state=os_dashboards_ec2_cert_state,
                        city=os_dashboards_ec2_cert_city,
                        hostname=os_dashboards_ec2_cert_hostname,
                        email=os_dashboards_ec2_cert_email_address
                    ),
                    service_restart_handles=[handle] 
                ),
                ec2.InitCommand.shell_command('openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/cert.key -out /etc/nginx/cert.crt -config /tmp/ec2_cert_info.cfg'),
                ec2.InitCommand.shell_command("cd /tmp && ifconfig eth0 | grep 'inet ' > inet.txt && export IFS=' ' && read -a strarr <<< `cat inet.txt` && export localIp=`echo ${strarr[1]}` && echo Local IP is: $localIp && export IFS=. && read -a iparr <<< $localIp && export IFS=' ' && read -a iparr <<< ${iparr[*]} && export resolverIp=${iparr[0]}.${iparr[1]}.0.2 && echo Resolver IP is $resolverIp && sed -i \"s/<SUBNET_RESOLVER_IP>/${resolverIp}/\" /etc/nginx/conf.d/default.conf"),
                ec2.InitService.enable('nginx', service_restart_handle=handle )
            )
        )
        self.domain.grant_index_read_write('*', self.bastion_host.grant_principal)
        self.domain.grant_read_write(self.bastion_host.grant_principal)

        self.bastion_host.node.add_dependency(user_pool_domain)

        self.eip = ec2.CfnEIP(self, 'BastionHostEip',
            domain='vpc',
            instance_id=self.bastion_host.instance_id,
            network_border_group=self.region
        )

        