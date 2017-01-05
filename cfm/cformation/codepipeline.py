#!/usr/bin/env python
from troposphere import Template, Ref, GetAtt, Output, Tags, Parameter
from troposphere.iam import Role
from troposphere.iam import Policy as TropospherePolicy
from awacs.aws import Allow, Statement, Action, Principal, Policy
from awacs.sts import AssumeRole
from troposphere.codepipeline import (
    Pipeline, Stages, Actions, ActionTypeID, OutputArtifacts, InputArtifacts,
    ArtifactStore, DisableInboundStageTransitions)
from troposphere.s3 import (Bucket, PublicRead)


# TODO change this line and module when codebuild is released by troposphere
from troposphere_early_release.codebuild import Artifacts, Environment, Source, Project

import cfnhelper

CODEPIPELINE = 'CODEPIPELINE'

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

    # codebuild -------------------

    artifacts = Artifacts(Type=CODEPIPELINE)

    environment = Environment(
        ComputeType='BUILD_GENERAL1_SMALL',
        Image='aws/codebuild/python:2.7.12',
        Type='LINUX_CONTAINER',
        EnvironmentVariables=[],
    )

    # using CODEPIPELINE
    if True:
        source = Source(Type=CODEPIPELINE)
    else:
        source = Source(
            Type="GITHUB",
            Location="https://github.com/powellquiring/bigimage.git",
        )

    codeBuildProject = Project(
        stackName + "CodeBuildProject",
        Artifacts=artifacts,
        Environment=environment,
        Name=stackName,
        ServiceRole=codebuildRoleArn,
        Source=source,
    )
    t.add_resource(codeBuildProject)

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
                Name="Build",
                Actions=[
                    Actions(
                        Name="buildaction",
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
                    )
                ]
            ),
            Stages(
                Name="Prod",
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
        "CodebuildRoleArn",
        Value=codebuildRoleArn,
        Description="Codebuild role arn",
    ))

    return t

if __name__ == "__main__":
    print(template().to_json())
