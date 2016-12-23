#!/usr/bin/python

from troposphere import (
    GetAtt, Join, Output,
    Parameter, Ref, Tags, Template, FindInMap
)

from troposphere.elasticbeanstalk import (
    Application, ApplicationVersion, ConfigurationTemplate, Environment,
    SourceBundle, OptionSettings
)

from troposphere.iam import Role, InstanceProfile
from troposphere.iam import PolicyType as IAMPolicy

from awacs.aws import Allow, Statement, Action, Principal, Policy
from awacs.sts import AssumeRole

import cfnhelper

AWS_DEFAULT_REGION = 'us-west-2'
VERSION = "_21" #TODO

# choose python or docker
BEANSTALK_DOCKER = False
def getBeanstalkEnvironment():
    if BEANSTALK_DOCKER:
        raise 'this has not been tested'
        return {
            'SolutionStackName': "64bit Amazon Linux 2016.09 v2.2.0 running Docker 1.11.2",
            'Description': "Docker Elastic Beanstalk"
        }
    else:
        return {
            'SolutionStackName': "64bit Amazon Linux 2016.09 v2.2.0 running Python 2.7",
            'Description': "Python Elastic Beanstalk"
        }


def id():
    return 'ingest.cfn.json'

def template(stackName='bigimage'):
    'return the troposphere Template for the ingest beanstalk'
    t = Template()

    t.add_version()

    t.add_description("twitter ingest template")

    codeBucket = t.add_parameter(Parameter(
        'CodeBucket',
        Type='String',
        Description='Bucket containing all of the templates for this stack, simple bucket name, example: elasticbeanstalk-us-west-2-433331399117'
    ))

    keyname = t.add_parameter(Parameter(
        "KeyName",
        Description="Name of an existing EC2 KeyPair to enable SSH access to "
                    "the AWS Elastic Beanstalk instance",
        Type="AWS::EC2::KeyPair::KeyName",
        ConstraintDescription="must be the name of an existing EC2 KeyPair.",
        Default="pics"
    ))

    deliveryStreamName = t.add_parameter(Parameter(
        "DeliveryStreamName",
        Type='String',
        Description="Firehose delivery stream name",
    ))

    # Create the role with a trust relationship that allows an ec2 service to assume a role
    role = t.add_resource(Role(
        "IngestRole",
        AssumeRolePolicyDocument=Policy(
            Statement=[
                Statement(
                    Effect=Allow, Action=[AssumeRole],
                    Principal=Principal(
                        "Service", [
                            'ec2.amazonaws.com'
                        ]
                    )
                )
            ]
        ),
        Path="/",
    ))

    # Add a policy directly to the role (a policy in the policy view is not created)
    t.add_resource(IAMPolicy(
        "IngestRolePolicy",
        PolicyName="IngestRolePolicy",
        PolicyDocument=Policy(
            Statement=[
                Statement(Effect=Allow, NotAction=Action("iam", "*"),
                          Resource=["*"])
            ]
        ),
        Roles=[Ref(role)],
    ))

    # Create an instance profile role that can be used to attach the embedded role to the ec2 instance
    ec2InstanceProfile = t.add_resource(InstanceProfile(
        "IngestInstanceProfile",
        Path="/",
        Roles=[Ref(role)],
    ))

    # dynamically generated application name: stackname-IngestApplication-uid
    ingestApplication = t.add_resource(Application(
        "IngestApplication",
        Description="Elasticbeanstalk based ingest application",
    ))

    # dynamically generate aplication version: stackname-ingestapplicationversion-uid
    ingestApplicationVersion = t.add_resource(ApplicationVersion(
        "IngestApplicationVersion",
        Description="Version 2.0",
        ApplicationName=Ref(ingestApplication),
        SourceBundle=SourceBundle(
            S3Bucket=Ref(codeBucket),
            S3Key="python-v1" + ".zip" #TODO kludge see similar kludge in run.py
            #S3Key="python-v1" + VERSION + ".zip" #TODO kludge see similar kludge in run.py
        ),
    ))


    # add an application with a dynamically generated application name, a ssh key, and the instance profile
    ebEnvironment = getBeanstalkEnvironment()
    ingestApplicationTemplate = t.add_resource(ConfigurationTemplate(
        "IngestConfigurationTemplate",
        Description="Template with dynamic generated name, " + ebEnvironment['Description'] + ", ssh access, and instance profile containing the IAM role",
        ApplicationName=Ref(ingestApplication),
        SolutionStackName=ebEnvironment['SolutionStackName'],
        OptionSettings=[
            OptionSettings(
                Namespace="aws:autoscaling:launchconfiguration",
                OptionName="EC2KeyName",
                Value=Ref(keyname),
            ),
            OptionSettings(
                Namespace="aws:autoscaling:launchconfiguration",
                OptionName="IamInstanceProfile",
                Value=Ref(ec2InstanceProfile),
            ),
            OptionSettings(
                Namespace="aws:elasticbeanstalk:application:environment",
                OptionName="DeliveryStreamName",
                Value=Ref(deliveryStreamName),
            ),
            OptionSettings(
                Namespace="aws:elasticbeanstalk:application:environment",
                OptionName="StackName",
                Value=stackName,
            ),
            OptionSettings(
                Namespace="aws:elasticbeanstalk:application:environment",
                OptionName="AWS_DEFAULT_REGION",
                Value=AWS_DEFAULT_REGION,
            ),
        ],
    ))

    # add the environment
    ingestEnvironment = t.add_resource(Environment(
        "IngestEnvironment",
        Description="AWS Elastic Beanstalk Environment",
        ApplicationName=Ref(ingestApplication),
        TemplateName=Ref(ingestApplicationTemplate),
        VersionLabel=Ref(ingestApplicationVersion),
        Tags=Tags(stage=cfnhelper.STAGE),
    ))

    # handle to the results
    t.add_output(
        Output(
            "URL",
            Description="URL of the AWS Elastic Beanstalk Environment",
            Value=Join("", ["http://", GetAtt(ingestEnvironment, "EndpointURL")])
        )
    )
    return t

if __name__ == "__main__":
    print(template().to_json())
