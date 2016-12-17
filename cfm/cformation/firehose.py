#!/usr/bin/python

from troposphere import Template, Parameter, Ref, Output, Join, Tags, GetAtt
from troposphere.firehose import (
    BufferingHints, CloudWatchLoggingOptions, CopyCommand, DeliveryStream,
    EncryptionConfiguration, KMSEncryptionConfig, ElasticsearchDestinationConfiguration, S3Configuration, RetryOptions)
from troposphere.s3 import (Bucket, PublicRead)

from troposphere.iam import Role
from troposphere.iam import PolicyType as IAMPolicy

from awacs.aws import Allow, Statement, Action, Principal, Policy
from awacs.sts import AssumeRole

import cfnhelper

def id():
    return 'firehose.cfn.json'

def template(stackName='bigimage'):
    t = Template()
    t.add_version('2010-09-09')
    t.add_description('Kinesis firehose deliver twitter to elasticsearch')

    s3bucket = t.add_resource(Bucket(
        stackName + "Firehose",
        AccessControl=PublicRead,
        Tags=Tags(stage=cfnhelper.STAGE),
    ))

    domainArn = t.add_parameter(Parameter(
        'DomainArn',
        Type='String',
        Description='Elasticsearch domain arn from the elasticsearch template'
    ))

    # Create the role with a trust relationship that allows an ec2 service to assume a role
    role = t.add_resource(Role(
        "FirehoseRole",
        AssumeRolePolicyDocument=Policy(
            Version="2012-10-17",
            Statement=[
                Statement(
                    Sid="",
                    Effect=Allow,
                    Action=[AssumeRole],
                    Principal=Principal(
                        "Service", [
                            'firehose.amazonaws.com'
                        ]
                    )
                )
            ]
        ),
        Path="/",
    ))

    # Add a policy directly to the role (a policy in the policy view is not created)
    t.add_resource(IAMPolicy(
        "FirehoseRolePolicy",
        PolicyName="FirehoseRolePolicy",
        PolicyDocument=Policy(
            Statement=[
                Statement(
                    Effect=Allow,
                    NotAction=Action("iam", "*"),
                    Resource=["*"],),
            ]),
        Roles=[Ref(role)],
    ))

    fireHoseRoleArn = roleArn(role)
    fireHoseBucketRoleArn = roleArn(role)
    t.add_resource(DeliveryStream(
        stackName + 'TwitterDeliveryStream',
        DeliveryStreamName=stackName + 'TwitterDeliveryStreamName',
        ElasticsearchDestinationConfiguration=ElasticsearchDestinationConfiguration(
            BufferingHints=BufferingHints(
                IntervalInSeconds=60,
                SizeInMBs=1,
            ),
            CloudWatchLoggingOptions=CloudWatchLoggingOptions(
                Enabled=True,
                LogGroupName='kinesis-log-group',
                LogStreamName='kinesis-log-stream',
            ),
            DomainARN=Ref(domainArn),
            IndexName = 'indexname',
            IndexRotationPeriod='NoRotation',
            RetryOptions=RetryOptions(
                DurationInSeconds=300,
            ),
            RoleARN=fireHoseRoleArn,
            S3BackupMode='AllDocuments',
            S3Configuration=S3Configuration(
                BucketARN=s3BucketArn(s3bucket),
                BufferingHints=BufferingHints(
                    IntervalInSeconds=60,
                    SizeInMBs=5,
                ),
                CloudWatchLoggingOptions=CloudWatchLoggingOptions(
                    Enabled=True,
                    LogGroupName='my-other-log-group',
                    LogStreamName='my-other-log-stream',
                ),
                CompressionFormat='UNCOMPRESSED',
                # not required:
                #EncryptionConfiguration=EncryptionConfiguration(
                #    KMSEncryptionConfig=KMSEncryptionConfig(
                #        AWSKMSKeyARN='aws-kms-key-arn'
                #    ),
                #    NoEncryptionConfig='NoEncryption',
                #),
                Prefix='my-firehose-prefix-',
                RoleARN=fireHoseBucketRoleArn,
            ),
            TypeName='testypename',
        ),
    ))

    t.add_output(Output(
        "S3",
        Value=Ref(s3bucket),
        Description="Firehose S3 bucket name"
    ))
    t.add_output(Output(
        "RoleArn",
        Value=fireHoseRoleArn,
        Description="Firehose role arn"
    ))
    t.add_output(Output(
        "BucketRoleArn",
        Value=fireHoseBucketRoleArn,
        Description="Firehose bucket role arn"
    ))


    return t

def s3BucketArn(bucketReference):
   return Join("", ["arn:aws:s3:::", Ref(bucketReference)])

def roleArn(roleReference):
   return GetAtt(roleReference, "Arn")

if __name__ == "__main__":
    print(template().to_json())
