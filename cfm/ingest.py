#!/usr/bin/python

from troposphere import (
    GetAtt, Join, Output,
    Parameter, Ref, Template, FindInMap
)

from troposphere.elasticbeanstalk import (
    Application, ApplicationVersion, ConfigurationTemplate, Environment,
    SourceBundle, OptionSettings
)

from troposphere.iam import Role, InstanceProfile
from troposphere.iam import PolicyType as IAMPolicy

from awacs.aws import Allow, Statement, Action, Principal, Policy
from awacs.sts import AssumeRole


t = Template()

t.add_version()

t.add_description("bigimage template")

keyname = t.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing EC2 KeyPair to enable SSH access to "
                "the AWS Elastic Beanstalk instance",
    Type="AWS::EC2::KeyPair::KeyName",
    ConstraintDescription="must be the name of an existing EC2 KeyPair.",
    Default="pics"
))

t.add_mapping("Region2Principal", {
    'ap-northeast-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'ap-southeast-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'ap-southeast-2': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'cn-north-1': {
        'EC2Principal': 'ec2.amazonaws.com.cn',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com.cn'},
    'eu-central-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'eu-west-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'sa-east-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'us-east-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'us-west-1': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'},
    'us-west-2': {
        'EC2Principal': 'ec2.amazonaws.com',
        'OpsWorksPrincipal': 'opsworks.amazonaws.com'}
    }
)

t.add_resource(Role(
    "WebServerRole",
    AssumeRolePolicyDocument=Policy(
        Statement=[
            Statement(
                Effect=Allow, Action=[AssumeRole],
                Principal=Principal(
                    "Service", [
                        FindInMap(
                            "Region2Principal",
                            Ref("AWS::Region"), "EC2Principal")
                    ]
                )
            )
        ]
    ),
    Path="/"
))

t.add_resource(IAMPolicy(
    "WebServerRolePolicy",
    PolicyName="WebServerRole",
    PolicyDocument=Policy(
        Statement=[
            Statement(Effect=Allow, NotAction=Action("iam", "*"),
                      Resource=["*"])
        ]
    ),
    Roles=[Ref("WebServerRole")]
))

t.add_resource(InstanceProfile(
    "WebServerInstanceProfile",
    Path="/",
    Roles=[Ref("WebServerRole")]
))

t.add_resource(Application(
    "SampleApplication",
    Description="Docker based application"
))

t.add_resource(ApplicationVersion(
    "SampleApplicationVersion",
    Description="Version 1.0",
    ApplicationName=Ref("SampleApplication"),
    SourceBundle=SourceBundle(
        S3Bucket="elasticbeanstalk-us-west-2-433331399117",
        S3Key="bigimage.zip"
    )
))

t.add_resource(ConfigurationTemplate(
    "SampleConfigurationTemplate",
    ApplicationName=Ref("SampleApplication"),
    Description="SSH access to Node.JS Application",
    SolutionStackName="64bit Amazon Linux 2016.09 v2.2.0 running Docker 1.11.2",
    OptionSettings=[
        OptionSettings(
            Namespace="aws:autoscaling:launchconfiguration",
            OptionName="EC2KeyName",
            Value=Ref("KeyName")
        ),
        OptionSettings(
            Namespace="aws:autoscaling:launchconfiguration",
            OptionName="IamInstanceProfile",
            Value=Ref("WebServerInstanceProfile")
        )
    ]
))

t.add_resource(Environment(
    "SampleEnvironment",
    Description="AWS Elastic Beanstalk Environment running Sample Node.js "
                "Application",
    ApplicationName=Ref("SampleApplication"),
    TemplateName=Ref("SampleConfigurationTemplate"),
    VersionLabel=Ref("SampleApplicationVersion")
))

t.add_output(
    Output(
        "URL",
        Description="URL of the AWS Elastic Beanstalk Environment",
        Value=Join("", ["http://", GetAtt("SampleEnvironment", "EndpointURL")])
    )
)

print(t.to_json())
