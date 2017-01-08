#!/usr/bin/env python
from troposphere import Template, Ref, Join, GetAtt, Output, Tags, Parameter
from troposphere.iam import Role
from troposphere.iam import Policy as TropospherePolicy
from awacs.aws import Allow, Statement, Action, Principal, Policy
from awacs.sts import AssumeRole
from troposphere.codepipeline import (
    Pipeline, Stages, Actions, ActionTypeID, OutputArtifacts, InputArtifacts,
    ArtifactStore, DisableInboundStageTransitions)
from troposphere.s3 import (Bucket, BucketPolicy, PublicRead, WebsiteConfiguration)


# TODO change this line and module when codebuild is released by troposphere
from troposphere_early_release.codebuild import Artifacts, Environment, EnvironmentVariable, Source, Project

import cfnhelper

CODEPIPELINE = 'CODEPIPELINE'

CODE_PIPELINE = True

def id():
    return 'codepipeline.cfn.json'

def template(stackName='bigimage'):
    t = Template()

    t.add_description('Codepipeline and codebuild for ' + stackName)

    # Create the role with a trust relationship that allows codebuild to assume the role
    # TODO the code build role runs the run.py to do the complete roll out and needs lots of privileges, the pipeline does not
    codeRole = t.add_resource(Role(
        "CodeRole",
        AssumeRolePolicyDocument=Policy(
            Version="2012-10-17",
            Statement=[
                Statement(
                    Sid="",
                    Effect=Allow,
                    Action=[AssumeRole],
                    Principal=Principal(
                        "Service", [
                            'codebuild.amazonaws.com',
                            'codepipeline.amazonaws.com',
                        ]
                    )
                )
            ]
        ),
        Path="/",
        Policies=[TropospherePolicy(
            "CodebuildAndCodepipelinePolicy",
            PolicyName="CodebuildAndCodepipelinePolicy",
            PolicyDocument=Policy(
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[Action("*")],
                        Resource=["*"],
                    ),
                ]
            ),
        )],
    ))
    codebuildRoleArn = GetAtt(codeRole, "Arn")

    # codebuild to execute run.py to deploy cloud and create ingest zip  -------------------

    artifacts = Artifacts(Type=CODEPIPELINE)

    environment = Environment(
        ComputeType='BUILD_GENERAL1_SMALL',
        Image='aws/codebuild/python:2.7.12',
        Type='LINUX_CONTAINER',
        EnvironmentVariables=[],
    )

    source = Source(Type=CODEPIPELINE)

    codeBuildProject = Project(
        stackName + "CodeBuildProject",
        Artifacts=artifacts,
        Environment=environment,
        Name=stackName,
        ServiceRole=codebuildRoleArn,
        Source=source,
    )
    t.add_resource(codeBuildProject)

    # codebuild to build browser application and write to s3 -------------------
    browserBucket = t.add_resource(Bucket(
        "BrowserBucket",
        AccessControl=PublicRead,
        DeletionPolicy='Retain',
        Tags=Tags(stage=cfnhelper.STAGE),
        WebsiteConfiguration=WebsiteConfiguration(
            IndexDocument='index.html',
        ),
    ))

    if False:
        browserBucketPolicy = t.add_resource(BucketPolicy(
            "BrowserBucketPolicy",
            Bucket=Ref(browserBucket),
            PolicyDocument={
                "Statement": [Statement(
                    Sid="AddPerm",
                    Effect=Allow,
                    Principal=Principal('*'),
                    Action=[Action("s3:GetObject")],
                    Resource=[
                        Join("/", [
                            GetAtt(browserBucket, "Arn"),
                            '*',
                        ]),
                    ],
                )],
            }
        ))

    environmentBrowser = Environment(
        ComputeType='BUILD_GENERAL1_SMALL',
        Image='aws/codebuild/nodejs:7.0.0',
        Type='LINUX_CONTAINER',
        EnvironmentVariables=[
            EnvironmentVariable(Name='BROWSER_S3', Value=cfnhelper.s3BucketArn(browserBucket)),
        ],
    )

    #sourceBrowser = Source(Type=CODEPIPELINE, BuildSpec='ls -lR && env')
    sourceBrowser = Source(Type=CODEPIPELINE)

    browserBuildProject = Project(
        stackName + "BrowserBuildProject",
        Artifacts=artifacts,
        Environment=environmentBrowser,
        Name=stackName+'Browser',
        ServiceRole=codebuildRoleArn,
        Source=sourceBrowser,
    )
    browserBuildProjectResource = t.add_resource(browserBuildProject)

    # codepipeline -------------------
    codepipelineBucket = t.add_resource(Bucket(
        "codepipelineBucket",
        AccessControl=PublicRead,
        DeletionPolicy='Retain',
        Tags=Tags(stage=cfnhelper.STAGE),
    ))

    ingestApplicationName = t.add_parameter(Parameter(
        "IngestApplicationName",
        Description="ingest beanstalk application name",
        Type="String"
    ))
    ingestEnvironmentName = t.add_parameter(Parameter(
        "IngestEnvironmentName",
        Description="ingest beanstalk environment name",
        Type="String"
    ))
    gitPersonalAccessToken = t.add_parameter(Parameter(
        'GitPersonalAccessToken',
        Type='String',
        Description='Git personal access token required for codepipeline'
    ))

    if CODE_PIPELINE:
        pipeline = t.add_resource(Pipeline(
            stackName + "codepipeline",
            Name=stackName,
            RoleArn=codebuildRoleArn,
            ArtifactStore=ArtifactStore(
                Type="S3",
                Location=Ref(codepipelineBucket)
            ),
            #DisableInboundStageTransitions=[
            #    DisableInboundStageTransitions(
            #        StageName="Release",
            #        Reason="Disabling the transition until "
            #               "integration tests are completed"
            #    )
            #]
            Stages=[
                Stages(
                    Name="Source",
                    Actions=[
                        Actions(
                            Name="SourceAction",
                            ActionTypeId=ActionTypeID(
                                Category="Source",
                                Owner="ThirdParty",
                                Version="1",
                                Provider="GitHub"
                            ),
                            OutputArtifacts=[
                                OutputArtifacts(
                                    Name="MyApp"
                                )
                            ],
                            Configuration={
                                "Owner": "powellquiring",
                                "Repo": "bigimage",
                                "Branch": "master",
                                "OAuthToken": Ref(gitPersonalAccessToken),
                            },
                            RunOrder="1"
                        )
                    ]
                ),
                Stages(
                    Name="BuildAllDeployCfn",
                    Actions=[
                        Actions(
                            Name="buildIngestDeployCfn",
                            InputArtifacts=[
                                InputArtifacts(
                                    Name="MyApp"
                                )
                            ],
                            OutputArtifacts=[
                                OutputArtifacts(
                                    Name="MyBuiltApp"
                                )
                            ],
                            ActionTypeId=ActionTypeID(
                                Category="Build",
                                Owner="AWS",
                                Version="1",
                                Provider="CodeBuild"
                            ),
                            Configuration={
                                "ProjectName": stackName,
                            },
                            RunOrder="1"
                        ),
                        Actions(
                            Name="buildBrowser",
                            InputArtifacts=[
                                InputArtifacts(
                                    Name="MyApp"
                                )
                            ],
                            OutputArtifacts=[
                                OutputArtifacts(
                                    Name="BrowserOutput"
                                )
                            ],
                            ActionTypeId=ActionTypeID(
                                Category="Build",
                                Owner="AWS",
                                Version="1",
                                Provider="CodeBuild"
                            ),
                            Configuration={
                                "ProjectName": browserBuildProject.Name,
                            },
                            RunOrder="1"
                        ),
                    ]
                ),
                Stages(
                    Name="DeployIngestApplication",
                    Actions=[
                        Actions(
                            Name="deploybeanstalk",
                            InputArtifacts=[
                                InputArtifacts(
                                    Name="MyBuiltApp"
                                )
                            ],
                            ActionTypeId=ActionTypeID(
                                Category="Deploy",
                                Owner="AWS",
                                Version="1",
                                Provider="ElasticBeanstalk"
                            ),
                            Configuration={
                                "ApplicationName": Ref(ingestApplicationName),
                                "EnvironmentName": Ref(ingestEnvironmentName),
                            },
                            RunOrder="1"
                        )
                    ]
                )
            ],
        ))

    t.add_output(Output(
        "CodepipelineBucket",
        Value=Ref(codepipelineBucket),
        Description="codepipeline S3 bucket name",
    ))

    t.add_output(Output(
        "CodebuildProject",
        Value=Ref(codeBuildProject),
        Description="codebuild ingest project",
    ))

    t.add_output(Output(
        "BrowserbuildProject",
        Value=Ref(browserBuildProjectResource),
        Description="browser codebuild project",
    ))

    t.add_output(Output(
        "CodebuildRoleArn",
        Value=codebuildRoleArn,
        Description="Codebuild role arn",
    ))

    return t

if __name__ == "__main__":
    print(template().to_json())
