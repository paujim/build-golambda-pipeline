#!/usr/bin/env python3

from aws_cdk import core

from pipeline.pipeline_stack import (
    RepoStack,
    PipelineStack,
)

app = core.App()
repo_stack = RepoStack(
    scope=app,
    id="pj-repo",
)
pipeline_stack = PipelineStack(
    scope=app,
    id="pj-pipeline",
    artifact_bucket_name=repo_stack.artifact_bucket_name,
)

app.synth()
