#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_opensearchservice as aos,
    aws_s3_assets as s3_assets
)
from constructs import Construct

class OpenSearchDashboardsProxyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
        app_security_group: ec2.ISecurityGroup,
        ec2_cert_city: str,
        ec2_cert_country: str,
        ec2_cert_email: str,
        ec2_cert_hostname: str,
        ec2_cert_state: str,
        ec2_enable_traffic_from_ip: str,
        os_domain: aos.IDomain,
        user_pool_domain: cognito.UserPoolDomain,
        #user_pool_id: str,
        vpc: ec2.IVpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)     
       
        handle = ec2.InitServiceRestartHandle()

        app_security_group.add_ingress_rule(
            ec2.Peer.ipv4(ec2_enable_traffic_from_ip),
            ec2.Port.all_traffic()
        )

        self.bastion_host = ec2.BastionHostLinux(self, 'OpenSearchDashboardsHost', 
            vpc=vpc,
            block_devices=[ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(10, encrypted=True),
            )],
            instance_name="OpenSearchDashboardsProxy",
            security_group=app_security_group,
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
                        domain_endpoint=os_domain.domain_endpoint,
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
                        country=ec2_cert_country,
                        state=ec2_cert_state,
                        city=ec2_cert_city,
                        hostname=ec2_cert_hostname,
                        email=ec2_cert_email
                    ),
                    service_restart_handles=[handle] 
                ),
                ec2.InitCommand.shell_command('openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/cert.key -out /etc/nginx/cert.crt -config /tmp/ec2_cert_info.cfg'),
                ec2.InitCommand.shell_command("cd /tmp && ifconfig eth0 | grep 'inet ' > inet.txt && export IFS=' ' && read -a strarr <<< `cat inet.txt` && export localIp=`echo ${strarr[1]}` && echo Local IP is: $localIp && export IFS=. && read -a iparr <<< $localIp && export IFS=' ' && read -a iparr <<< ${iparr[*]} && export resolverIp=${iparr[0]}.${iparr[1]}.0.2 && echo Resolver IP is $resolverIp && sed -i \"s/<SUBNET_RESOLVER_IP>/${resolverIp}/\" /etc/nginx/conf.d/default.conf"),
                ec2.InitService.enable('nginx', service_restart_handle=handle )
            )
        )
        os_domain.grant_index_read_write('*', self.bastion_host.grant_principal)
        os_domain.grant_read_write(self.bastion_host.grant_principal)

        self.bastion_host.node.add_dependency(user_pool_domain)

        self.eip = ec2.CfnEIP(self, 'BastionHostEip',
            domain='vpc',
            instance_id=self.bastion_host.instance_id,
            network_border_group=self.region
        )
