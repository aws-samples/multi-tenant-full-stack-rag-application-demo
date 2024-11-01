#!/usr/bin/env python3
import os
from aws_cdk import App, DefaultStackSynthesizer

from lib.app import MultiTenantRagStack


app = App()
MultiTenantRagStack(app, app.node.try_get_context('stack_name_backend') or "MultiTenantRagStack",
    synthesizer=DefaultStackSynthesizer(
        generate_bootstrap_version_rule=False
    )
)

app.synth()
