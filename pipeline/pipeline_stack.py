import constants
from aws_cdk import (
    core,
    aws_secretsmanager as secretsmanager,
    aws_codebuild as codebuild,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_lambda as lambda_, aws_s3 as s3,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_ssm as ssm,
)


class PipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        artifact_bucket = s3.Bucket(
            scope=self,
            id="s3-artifact",
            bucket_name=constants.ARTIFACT_BUCKET_NAME,
            removal_policy=core.RemovalPolicy.DESTROY,
            versioned=True,
        )

        lambda_build = codebuild.Project(
            scope=self,
            id="codebuild-build",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "env": {
                    "variables": {
                        "ENV_NAME": "pj",
                        "GO111MODULE": "on",
                    }
                },

                "phases":
                {
                    "install": {
                        "commands": [
                            "go get .",

                        ]
                    },
                    "pre_build": {
                        "commands": [
                            "go vet .",  # Check the Go code for common problems with 'go vet'
                            "go test .",  # Run all tests included with our application
                        ]
                    },
                    "build": {
                        "commands": [
                            "go build -o main",  # Build the go application
                            "zip main.zip main",
                        ]
                    }
                },
                "artifacts": {
                    "files": ["main.zip"],
                    "name": "$ENV_NAME-lambda-$(date +%Y-%m-%d).zip"
                }

            }
            ),
        )

        oauth_token = core.SecretValue.secrets_manager(
            secret_id=constants.SECRET_GITHUB_ID,
            json_field=constants.SECRET_GITHUB_JSON_FIELD,
        )

        # Codepipeline
        lambda_pipeline = codepipeline.Pipeline(
            scope=self,
            id="lambda-pipeline",
            # artifact_bucket=artifact_bucket,
        )

        source_output = codepipeline.Artifact()
        lambda_pipeline.add_stage(
            stage_name="Source",
            actions=[
                codepipeline_actions.GitHubSourceAction(
                    oauth_token=oauth_token,
                    action_name="GitHub",
                    owner=constants.GITHUB,
                    repo=constants.GITHUB_REPO,
                    output=source_output,
                )]
        )

        build_output = codepipeline.Artifact()
        lambda_pipeline.add_stage(
            stage_name="Build",
            actions=[codepipeline_actions.CodeBuildAction(
                action_name="CodeBuild",
                project=lambda_build,
                input=source_output,
                outputs=[build_output]
            )]
        )

        s3_action = codepipeline_actions.S3DeployAction(
            bucket=artifact_bucket,
            input=build_output,
            action_name="S3Upload",
            extract=True,
            object_key=constants.LAMBDA_KEY,
        )

        lambda_pipeline.add_stage(
            stage_name="Upload",
            actions=[s3_action]
        )
