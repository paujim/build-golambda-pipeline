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


class RepoStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # lambda_repository = codecommit.Repository(
        #     scope=self,
        #     id="CODECOMIT-LAMBDA-REPO",
        #     repository_name=constants.CODECOMMIT_REPO_NAME,
        # )

        artifact_bucket = s3.Bucket(
            scope=self,
            id="S3-ARTIFACT",
            bucket_name=constants.ARTIFACT_BUCKET_NAME
        )
        self.artifact_bucket_name = artifact_bucket.bucket_name


class PipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, artifact_bucket_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # lambda_repository = codecommit.Repository.from_repository_name(
        #     scope=self,
        #     id="IMPORTED-REPO",
        #     repository_name=constants.CODECOMMIT_REPO_NAME,
        # )

        artifact_bucket = s3.Bucket.from_bucket_name(
            scope=self,
            id="ARTIFACT-BUCKET",
            bucket_name=artifact_bucket_name,
        )

        # Codebuild
        # codecommit_source = codebuild.Source.code_commit(
        #     repository=lambda_repository,
        #     branch_or_ref="refs/heads/master",
        # )

        github_source = codebuild.Source.git_hub(
            owner=constants.GITHUB,
            repo=constants.GITHUB_REPO,
            branch_or_ref="refs/heads/master",
        )
        lambda_build = codebuild.Project(
            scope=self,
            id="LAMBDA-BUILD",
            source=github_source,
            artifacts=codebuild.Artifacts.s3(
                identifier="artifact",
                bucket=artifact_bucket,
                encryption=False,
                path="codebuild_output",
                name="lambda.zip"),
        )

        oauth_token = core.SecretValue.secrets_manager(
            secret_id=constants.SECRET_GITHUB_ID,
            json_field=constants.SECRET_GITHUB_JSON_FIELD,
        )
        # Codepipeline
        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()

        # source_action = codepipeline_actions.CodeCommitSourceAction(
        #     action_name="CodeCommit",
        #     repository=lambda_repository,
        #     output=source_output
        # )

        source_action = codepipeline_actions.GitHubSourceAction(
            oauth_token=oauth_token,
            action_name="GitHub",
            owner=constants.GITHUB,
            repo=constants.GITHUB_REPO,
            output=source_output,
        )
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="CodeBuild",
            project=lambda_build,
            input=source_output,
            outputs=[build_output]
        )
        s3_action = codepipeline_actions.S3DeployAction(
            bucket=artifact_bucket,
            input=build_output,
            action_name="S3Upload",
            extract=False,
            object_key=constants.LAMBDA_KEY,
        )
        lambda_pipeline = codepipeline.Pipeline(
            scope=self,
            id="LAMBDA-PIPELINE",
        )
        lambda_pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )
        lambda_pipeline.add_stage(
            stage_name="Build",
            actions=[build_action]
        )
        lambda_pipeline.add_stage(
            stage_name="Upload",
            actions=[s3_action]
        )
