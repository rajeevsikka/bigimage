#!/usr/bin/python

from troposphere import Template, Parameter, Ref, Output, Join, Tags, GetAtt
from troposphere.firehose import (
    BufferingHints, CloudWatchLoggingOptions, CopyCommand, DeliveryStream,
    EncryptionConfiguration, KMSEncryptionConfig, ElasticsearchDestinationConfiguration, S3Configuration, RetryOptions)
from troposphere.s3 import (Bucket, PublicRead)

from troposphere.iam import Role
from troposphere.iam import PolicyType as IAMPolicy

from troposphere.logs import LogGroup, LogStream

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
        "firehose",
        AccessControl=PublicRead,
        Tags=Tags(stage=cfnhelper.STAGE),
    ))

    domainArn = t.add_parameter(Parameter(
        'DomainArn',
        Type='String',
        Description='Elasticsearch domain arn from the elasticsearch template'
    ))

    FIREHOSE_LOG_GROUP = stackName + "FirehoseLogGroup"
    logGroup = t.add_resource(LogGroup(
        FIREHOSE_LOG_GROUP,
        LogGroupName=FIREHOSE_LOG_GROUP,
        RetentionInDays=7,
    ))

    FIREHOSE_LOG_STREAM = stackName + "FirehoseLogStream"
    logStream = t.add_resource(LogStream(
        FIREHOSE_LOG_STREAM,
        LogGroupName=Ref(logGroup),
        LogStreamName=FIREHOSE_LOG_STREAM,
    ))

    FIREHOSE_FILE_GROUP = stackName + "FirehoseFileGroup"
    logFileGroup = t.add_resource(LogGroup(
        FIREHOSE_FILE_GROUP,
        LogGroupName=FIREHOSE_FILE_GROUP,
        RetentionInDays=7,
    ))

    FIREHOSE_FILE_STREAM = stackName + "FirehoseFileStream"
    logFileStream = t.add_resource(LogStream(
        FIREHOSE_FILE_STREAM,
        LogGroupName=Ref(logFileGroup),
        LogStreamName=FIREHOSE_FILE_STREAM,
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
    deliveryStreamId = stackName + 'TwitterDeliveryStream'
    deliveryStreamName = deliveryStreamId
    t.add_resource(DeliveryStream(
        deliveryStreamId,
        DeliveryStreamName=deliveryStreamName,
        ElasticsearchDestinationConfiguration=ElasticsearchDestinationConfiguration(
            BufferingHints=BufferingHints(
                IntervalInSeconds=60,
                SizeInMBs=1,
            ),
            CloudWatchLoggingOptions=CloudWatchLoggingOptions(
                Enabled=True,
                LogGroupName=Ref(logGroup),
                LogStreamName=Ref(logStream),
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
                    LogGroupName=Ref(logFileGroup),
                    LogStreamName=Ref(logFileStream),
                ),
                CompressionFormat='UNCOMPRESSED',
                # not required:
                #EncryptionConfiguration=EncryptionConfiguration(
                #    KMSEncryptionConfig=KMSEncryptionConfig(
                #        AWSKMSKeyARN='aws-kms-key-arn'
                #    ),
                #    NoEncryptionConfig='NoEncryption',
                #),
                Prefix='',
                RoleARN=fireHoseBucketRoleArn,
            ),
            TypeName='testypename',
        ),
    ))

    t.add_output(Output(
        "S3",
        Value=Ref(s3bucket),
        Description="Firehose S3 bucket name",
    ))
    t.add_output(Output(
        "DeliveryStreamName",
        Value=deliveryStreamName,
        Description="Firehose delivery stream name",
    ))
    t.add_output(Output(
        "RoleArn",
        Value=fireHoseRoleArn,
        Description="Firehose role arn",
    ))
    t.add_output(Output(
        "BucketRoleArn",
        Value=fireHoseBucketRoleArn,
        Description="Firehose bucket role arn",
    ))


    return t

def s3BucketArn(bucketReference):
   return Join("", ["arn:aws:s3:::", Ref(bucketReference)])

def roleArn(roleReference):
   return GetAtt(roleReference, "Arn")

if __name__ == "__main__":
    print(template().to_json())
