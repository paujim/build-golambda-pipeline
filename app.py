#!/usr/bin/env python3

from aws_cdk import core

from pipeline.pipeline_stack import (
    PipelineStack,
)

app = core.App()

pipeline_stack = PipelineStack(
    scope=app,
    id="build-golambda-pipeline",
)

app.synth()
