#!/usr/bin/env python
from __future__ import print_function
from string import Template

# run.py by default will delete cloudformation templates and buckets created by this script and create everything from scratch.
# other parameters (yet to be defined) will roll out a smaller change

import boto3
import os
import argparse
import re
import tempfile
import shutil
import importlib

# command line parsing
parser = argparse.ArgumentParser(description='deploy the application aws by deleting the existing stack and creating a new one') 
parser.add_argument('-cs', action='store_true', help='generate new templates, upload to bucket, generate change sets')
#parser.add_argument('-lcs', action='store_true', help='list the change sets')
parser.add_argument('-d', action='store_true', help='just delete the buckets and the stack and quit, if you need to start from scratch: -d and run again')
parser.add_argument('-k', action='store_true', default=False, help='keep the temporary directory of files that were uploaded to s3')
parser.add_argument('-n', action='store', default='bigimage', help='name any global objects, like s3 buckets, with this name')
parser.add_argument('-nc', action='store_true', help='do not generate code and upload to the code s3 bucket')
parser.add_argument('-s', action='store_true', help='run silently')
parser.add_argument('-u', action='store_true', help='generate new templates, upload to bucket, update stack')
args = parser.parse_args()

# globals for getting to boto3
clientSts = boto3.client('sts')
clientCloudformation = boto3.client('cloudformation')
clientS3 = boto3.client('s3')
s3 = boto3.resource('s3')

# constants
ARG_SILENT = args.s
ARG_CODE = not args.nc
ARG_KEEP = args.k
ARG_JUST_DELETE = args.d
ARG_NAME = args.n
ARG_CHANGE_SET = args.cs
ARG_UPDATE = args.u

STACK_NAME=ARG_NAME
ACCOUNT_ID = clientSts.get_caller_identity()['Account']
S3_TEMPLATE_BUCKET = STACK_NAME + 'cfn' + ACCOUNT_ID # cloudformation template are generated in this script and kept here
S3_CODE_BUCKET=STACK_NAME + 'code' + ACCOUNT_ID # code is generated in this script and kept here
REGION = boto3.session.Session().region_name
MASTER_TEMPLATE='master.cfn.json'
MASTER_TEMPLATE_PARAMETERS=[{
    'ParameterKey': 'TemplateBucket',
    'ParameterValue': '{}/{}'.format(clientS3.meta.endpoint_url, S3_TEMPLATE_BUCKET),
    'UsePreviousValue': False
},{
    'ParameterKey': 'CodeBucket',
    'ParameterValue': S3_CODE_BUCKET,
    'UsePreviousValue': False
}]

# each module must have id() and template() functions.
# id() will return the name of the json file that should be generated
# template() will return the trophoshpere template
CFORMATION_TEMPLATES = ['cformation.master', 'cformation.ingest', 'cformation.elasticsearch', 'cformation.firehose']
TROPHOSPHERE_NAME_TEMPLATE = {}
for moduleName in CFORMATION_TEMPLATES:
    idModule = importlib.import_module(moduleName)
    idF = getattr(idModule, 'id')
    templateF = getattr(idModule, 'template')
    TROPHOSPHERE_NAME_TEMPLATE.update({idF(): templateF(STACK_NAME)})

# directories that contain a makeawszip command that will create a zip
MAKEAWSZIP_DIRS = ['python-v1']

def silentPrint(*args):
    if not ARG_SILENT:
        print(*args)

def bucketCreate(bucket):
    bucket.create(CreateBucketConfiguration={'LocationConstraint': REGION}, GrantRead='uri="http://acs.amazonaws.com/groups/global/AllUsers"')

def bucketDelete(bucketName):
    'return a new bucket, clean all keys in bucket and delete if they currently exist'
    silentPrint('deleting bucket:', bucketName)
    bucket = s3.Bucket(bucketName)
    try:
        for key in bucket.objects.all():
            key.delete()
            silentPrint('delete key, bucket:', key.bucket_name, 'key:', key.key)
        bucket.delete()
        silentPrint('deleted bucket:', bucket.name)
    except:
        pass
    return bucket

def bucketExists(bucketName):
    'return True if the bucket exists'
    return s3.Bucket(bucketName) in s3.buckets.all()

def bucketNew(bucketName):
    'create a new bucket'
    bucket = s3.Bucket(bucketName)
    bucketCreate(bucket)
    bucket_policy = s3.BucketPolicy(bucketName)
    policy=Template('''{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AddPerm",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::$bucket/*"
                }
            ]
        }
    ''').substitute(bucket=S3_TEMPLATE_BUCKET)
    silentPrint("s3 teamplate bucket policy:", policy)
    bucket_policy.put(Policy=policy)
    silentPrint('create bucket:', bucketName)
    return bucket
        
def localFiles(reString):
    'return the files in this directory (just files not directories) that match the regular expression'
    prog = re.compile(reString)
    files = []
    for filename in os.listdir("."):
        if not prog.match(filename):
            continue
        files.append(filename)
    return files

def bucketPopulate(tempDir, bucket):
    'populate the bucket with the cf.json files in this directory'
    for key in TROPHOSPHERE_NAME_TEMPLATE:
        localFile = os.path.join(tempDir, key)
        silentPrint("upload:", localFile, "url:", s3Url(bucket, key))
        bucket.upload_file(localFile, key)


def nameToCfnJsonName(name):
    return name + ".cfn.json"

def generateCfn(outputDir):
    'generate the cloudformation templates for all the *.cfn.py files in this directory'
    for key, template in TROPHOSPHERE_NAME_TEMPLATE.iteritems():
        outputFile = open(os.path.join(outputDir, key), "w")
        outputFile.write(template.to_json())

def stackDeleteWait(stackName):
    waiter = clientCloudformation.get_waiter('stack_delete_complete')
    silentPrint("waiting for cloudformation stack to be deleted:", stackName)
    waiter.wait(StackName=stackName)


def stackDelete(stackName):
    try:
        silentPrint("delete stack:", stackName)
        clientCloudformation.delete_stack(StackName=stackName)
    except:
        return
    stackDeleteWait(stackName)

def stackWait(stackName, waitName):
    silentPrint("waiting for cloudformation stack to be", waitName, "stack:", stackName)
    waiter = clientCloudformation.get_waiter(waitName)
    waiter.wait(StackName=stackName)

def stackCreateWait(stackName):
    stackWait(stackName, 'stack_create_complete')

def stackUpdateWait(stackName):
    stackWait(stackName, 'stack_update_complete')

def s3Url(s3Bucket, s3Key):
    return '{}/{}/{}'.format(clientS3.meta.endpoint_url, s3Bucket.name, s3Key)

def stackCreate(stackName, templateBucket, s3MasterKey, cfnParameters):
    url = s3Url(templateBucket, s3MasterKey)
    response = clientCloudformation.create_stack(
        StackName=stackName,
        TemplateURL=url,
        Parameters=cfnParameters,
        #DisableRollback=True|False,
        #TimeoutInMinutes=123,
        #NotificationARNs=[
        #    'string',
        #],
        Capabilities=[
            'CAPABILITY_IAM'
        ],
        #ResourceTypes=[
        #    'string',
        #],
        #RoleARN='string',
        #OnFailure='DO_NOTHING'|'ROLLBACK'|'DELETE',
        #StackPolicyBody='string',
        #StackPolicyURL='string',
        Tags=[
            {
                'Key': 'project',
                'Value': STACK_NAME,
            },
        ]
    )
    stackCreateWait(stackName)

def stackUpdate(stackName, templateBucket, s3MasterKey, cfnParameters):
    url = s3Url(templateBucket, s3MasterKey)
    response = clientCloudformation.update_stack(
        StackName=stackName,
        TemplateURL=url,
        UsePreviousTemplate=False,
        # StackPolicyDuringUpdateBody
        Parameters=cfnParameters,
        #DisableRollback=True|False,
        #TimeoutInMinutes=123,
        #NotificationARNs=[
        #    'string',
        #],
        Capabilities=[
            'CAPABILITY_IAM'
        ],
        #ResourceTypes=[
        #    'string',
        #],
        #RoleARN='string',
        #OnFailure='DO_NOTHING'|'ROLLBACK'|'DELETE',
        #StackPolicyBody='string',
        #StackPolicyURL='string',
        Tags=[
            {
                'Key': 'project',
                'Value': STACK_NAME,
            },
        ]
    )
    stackUpdateWait(stackName)

def stackCreateChangeSet(stackName, templateBucket, s3MasterKey, cfnParameters):
    url = s3Url(templateBucket, s3MasterKey)
    response = clientCloudformation.create_change_set(
        ChangeSetName='changeSetName',
        # ClientToken='string',
        #Description='string',
        ChangeSetType='UPDATE',
        #
        StackName=stackName,
        TemplateURL=url,
        UsePreviousTemplate=False,
        Parameters=cfnParameters,
        #TimeoutInMinutes=123,
        #NotificationARNs=[
        #    'string',
        #],
        Capabilities=[
            'CAPABILITY_IAM'
        ],
        #ResourceTypes=[
        #    'string',
        #],
        #RoleARN='string',
        #OnFailure='DO_NOTHING'|'ROLLBACK'|'DELETE',
        #StackPolicyBody='string',
        #StackPolicyURL='string',
    )
    stackCreateWait(stackName)

def generateAndUploadDir(bucket, inputDir, outputDir):
    'inputDir is a directory that contains a makeawszip.sh script, call the script to create an inputDir.zip file and upload it'
    outputFile = os.path.join(outputDir, inputDir) # name the file portion of the output zip the same as the directory name
    systemCmd = "../" + inputDir + '/makeawszip.sh ' + outputFile
    silentPrint("execute:", systemCmd)
    os.system(systemCmd)
    file = outputFile + ".zip"
    key = inputDir + ".zip"
    # https://s3-us-west-2.amazonaws.com/bigimagecfn433331399117/master.cfn.json
    silentPrint("upload:", file, "url:", s3Url(bucket, key))
    bucket.upload_file(file, key)

def generateAndUploadCode(outputDir, bucketName):
    bucket = s3.Bucket(bucketName)
    try:
        bucketCreate(bucket)
    except:
        pass
    for inputDir in MAKEAWSZIP_DIRS:
        generateAndUploadDir(bucket, inputDir, outputDir)


# populate template bucket with fresh templates.  Generate them in the temporary directory then copy them to s3

if ARG_JUST_DELETE:
    stackDelete(STACK_NAME)
    bucketDelete(S3_TEMPLATE_BUCKET)
    bucketDelete(S3_CODE_BUCKET)
    quit()

if not bucketExists(S3_TEMPLATE_BUCKET):
    templateBucket = bucketNew(S3_TEMPLATE_BUCKET)

templateBucket = s3.Bucket(S3_TEMPLATE_BUCKET)
tempDir = tempfile.mkdtemp()
silentPrint("temporary directory:", tempDir)
generateCfn(tempDir)
bucketPopulate(tempDir, templateBucket)
if ARG_CHANGE_SET:
    print("not implemented yet")
    quit()
    stackCreateChangeSet(STACK_NAME, templateBucket, MASTER_TEMPLATE, MASTER_TEMPLATE_PARAMETERS)
    quit()

# generate new code zips
if ARG_CODE:
    generateAndUploadCode(tempDir, S3_CODE_BUCKET)

if ARG_UPDATE:
    stackUpdate(STACK_NAME, templateBucket, MASTER_TEMPLATE, MASTER_TEMPLATE_PARAMETERS)
else:
    # delete the existing stack and create a new stack
    stackDelete(STACK_NAME)
    stackCreate(STACK_NAME, templateBucket, MASTER_TEMPLATE, MASTER_TEMPLATE_PARAMETERS)

if ARG_KEEP:
    print("temporary directory:", tempDir)
else:
    shutil.rmtree(tempDir)
