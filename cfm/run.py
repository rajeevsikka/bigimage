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
import cformation
from cformation import *

# in the cformation directory
CFORMATION_TEMPLATES = [cformation.master, cformation.ingest, cformation.elasticsearch, cformation.firehose, cformation.codepipeline]

GIT_PERSONAL_ACCESS_TOKEN = 'GIT_PERSONAL_ACCESS_TOKEN'
TWITTER_VARIABLES = ['TWITTER_CONSUMER_KEY', 'TWITTER_CONSUMER_SECRET', 'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET', GIT_PERSONAL_ACCESS_TOKEN]

# command line parsing
parser = argparse.ArgumentParser(description="""Look at the switches below and notice the commands.
You can run any of these commands individually.
If none of the commands are specified then following commands will be run in order: -code, -codeupload, -template, -update.
Before the create or update commands are run the twitter credentials will be verified.
If twitter credential verification fails, fix the problem by setting the env variables and using the -p switch.
In addition it can be useful to execute -template followed by -update to make changes to the templates then update the existing stack.
The -name parameter can be used to create multiple stacks, you must use the same name to delete, update, etc.
""") 
parser.add_argument('-delete', action='store_true', help='command: delete the buckets and the stack')
parser.add_argument('-code', action='store_true', help='command: generate code in temporary directory')
parser.add_argument('-codeupload', action='store_true', help='command: upload the code generated by the code command, create s3 bucket, upload code s3 bucket')
parser.add_argument('-template', action='store_true', help='command: generate cloudformation templates in the temporary directory, create cfn bucket, put the templates into the cfn bucket')
parser.add_argument('-create', action='store_true', help='command: create the stack from the cloud formation templates created with -template')
parser.add_argument('-update', action='store_true', help='command: update the stack (normally run with -template)')
parser.add_argument('-creds', action='store_true', help='command: store twitter credentials, set these environment variables then use the -p option to store them:' + str(TWITTER_VARIABLES))
parser.add_argument('-n', action='store', default='bigimage', help='name any global objects, like s3 buckets, with this name')
parser.add_argument('-s', action='store_true', help='run silently')
args = parser.parse_args()


# globals for getting to boto3
clientSts = boto3.client('sts')
clientCloudformation = boto3.client('cloudformation')
clientS3 = boto3.client('s3')
s3 = boto3.resource('s3')
ssm = boto3.client('ssm')

# args
ARG_SILENT = args.s
ARG_NAME = args.n

# commands
ARG_DELETE = args.delete
ARG_CODE = args.code
ARG_CODEUPLOAD = args.codeupload
ARG_TEMPLATE = args.template
ARG_CREATE = args.create
ARG_UPDATE = args.update
ARG_CREDS = args.creds

if (not ARG_DELETE) and (not ARG_CODE) and (not ARG_TEMPLATE) and (not ARG_CREATE) and (not ARG_UPDATE) and (not ARG_CREDS):
    ARG_CODE = True
    ARG_CODEUPLOAD = True
    ARG_TEMPLATE = True
    ARG_UPDATE = True

# constants
STACK_NAME=ARG_NAME
ACCOUNT_ID = clientSts.get_caller_identity()['Account']
S3_TEMPLATE_BUCKET = STACK_NAME + 'cfn' + ACCOUNT_ID # cloudformation template are generated in this script and kept here
S3_CODE_BUCKET=STACK_NAME + 'code' + ACCOUNT_ID # code is generated in this script and kept here
REGION = boto3.session.Session().region_name
MASTER_TEMPLATE='master.cfn.json'

def masterTemplateParameters():
    'return the master template parameters, can only be called after verifyTwitterCreds()'
    gitParameterValue = getTwitterValueFromLastParameters(stackName(GIT_PERSONAL_ACCESS_TOKEN))
    MASTER_TEMPLATE_PARAMETERS=[{
        'ParameterKey': 'TemplateBucket',
        'ParameterValue': '{}/{}'.format(clientS3.meta.endpoint_url, S3_TEMPLATE_BUCKET),
        'UsePreviousValue': False
    },{
        'ParameterKey': 'CodeBucket',
        'ParameterValue': S3_CODE_BUCKET,
        'UsePreviousValue': False
    },{
        'ParameterKey': 'GitPersonalAccessToken',
        'ParameterValue': gitParameterValue,
        'UsePreviousValue': False
    }]
    return MASTER_TEMPLATE_PARAMETERS

# each module must have id() and template() functions.
# id() will return the name of the json file that should be generated
# template() will return the trophoshpere template

TROPHOSPHERE_NAME_TEMPLATE = {}
for moduleName in CFORMATION_TEMPLATES:
    TROPHOSPHERE_NAME_TEMPLATE.update({moduleName.id(): moduleName.template(STACK_NAME)})

# directories that contain a makeawszip command that will create a zip
MAKEAWSZIP_DIRS = ['python-v1']

def silentPrint(*args):
    if not ARG_SILENT:
        print(*args)


def stackName(name):
    "turn a environment variable name into a stack specific name"
    return STACK_NAME + "_" + name

def namedTwitterVariables():
    "return the stack named twitter variables"
    ret = []
    for name in TWITTER_VARIABLES:
        ret.append(stackName(name))
    return ret

def storeTwitterCreds():
    "store the twitter creds as Simple System Management System Parameters"
    ret = True
    parameterStore = {}
    for name in TWITTER_VARIABLES:
        if not os.environ.has_key(name):
            print(name, "not in environment")
            ret = False
            continue
        value = os.environ[name]
        if value == "":
            print(name, "in environment but does not have a vlue")
            ret = False
            continue
        parameterStore[stackName(name)] = value

    if not ret:
        return False

    for name in parameterStore:
        value = parameterStore[name]
        silentPrint('put_parameter name:', name, "value:", value)
        ssm.put_parameter(Name=name, Value=value, Type='SecureString', Overwrite=True)
                
    return True


LAST_TWITTER_PARAMETERS = []
def getTwitterValueFromLastParameters(name):
    for parameter in LAST_TWITTER_PARAMETERS:
        if parameter['Name'] == name:
            return parameter['Value']
    print(name, "not found in LAST_TWITTER_PARAMETERS:", LAST_TWITTER_PARAMETERS)
    quit()

def verifyTwitterCreds():
    "veriy that all of the twitter variables for this stack exist"
    names = namedTwitterVariables()
    ret = ssm.get_parameters(Names=names, WithDecryption=True)
    global LAST_TWITTER_PARAMETERS
    LAST_TWITTER_PARAMETERS = ret[u'Parameters']
    for parameter in LAST_TWITTER_PARAMETERS:
        print("name:", parameter['Name'], "value:", parameter['Value'])
    invalidParameters = ret['InvalidParameters']
    if len(invalidParameters) > 0:
        print("missing system parameters:", str(invalidParameters))
        return False
    return True

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

def bucketExists(bucket):
    'return True if the bucket exists'
    return bucket in s3.buckets.all()

def bucketNew(bucket):
    'create a new bucket'
    bucketCreate(bucket)
    bucket_policy = s3.BucketPolicy(bucket.name)
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
    silentPrint('create bucket:', bucket.name)
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

import imp

def uploadProjectCode(bucket, inputDirBasename, outputDir):
    'upload generated code from a project'
    file = os.path.join(outputDir, inputDirBasename + ".zip")
    key = os.path.basename(file)
    silentPrint("upload:", file, "key:", key, "url:", s3Url(bucket, key))
    # upload file
    bucket.upload_file(file, key)

def uploadCode(outputDir, bucketName):
    bucket = s3.Bucket(bucketName)
    try:
        bucketCreate(bucket)
        bucket_versioning = s3.BucketVersioning(bucketName)
        silentPrint("eable bucket_versioning:", bucket_versioning)
        bucket_versioning.enable()
    except:
        pass
    for inputDirBasename in MAKEAWSZIP_DIRS:
        uploadProjectCode(bucket, inputDirBasename, outputDir)

def generateProjectCode(inputDirBasename, outputDir):
    'call the inputDirBasename/build/build.py script to create a zip file to upload'
    buildPath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), inputDirBasename, "build", "build.py")
    silentPrint('building code:', buildPath)
    buildModule = imp.load_source("build", buildPath)
    zip_file_name = os.path.join(outputDir, inputDirBasename + ".zip")
    hash = buildModule.build(zip_file_name)
    print(hash)

def generateCode(outputDir):
    for inputDirBasename in MAKEAWSZIP_DIRS:
        generateProjectCode(inputDirBasename, outputDir)

# commands --------------------------

if ARG_CREDS:
    silentPrint("command: creds")
    if not storeTwitterCreds():
        quit()

if ARG_DELETE:
    silentPrint("command: delete")
    stackDelete(STACK_NAME)
    bucketDelete(S3_TEMPLATE_BUCKET)
    bucketDelete(S3_CODE_BUCKET)

if False:
    tempDir = tempfile.mkdtemp()
else:
    tempDir = os.path.abspath("build")
    silentPrint("temporary directory:", tempDir)
    try:
        shutil.rmtree(tempDir)
    except:
        pass
    os.mkdir(tempDir)

# generate new code zips
if ARG_CODE:
    silentPrint("command: code")
    generateCode(tempDir)

if ARG_CODEUPLOAD:
    silentPrint("command: codeupload")
    uploadCode(tempDir, S3_CODE_BUCKET)

# populate template bucket with fresh templates.  Generate them in the temporary directory then copy them to s3
templateBucket = s3.Bucket(S3_TEMPLATE_BUCKET)
if ARG_TEMPLATE:
    silentPrint("command: template")
    if not bucketExists(templateBucket):
        bucketNew(templateBucket)

    generateCfn(tempDir)
    bucketPopulate(tempDir, templateBucket)

if ARG_CREATE:
    silentPrint("command: create")
    if not verifyTwitterCreds():
        quit()
    stackCreate(STACK_NAME, templateBucket, MASTER_TEMPLATE, masterTemplateParameters())

if ARG_UPDATE:
    silentPrint("command: update")
    if not verifyTwitterCreds():
        quit()
    stackUpdate(STACK_NAME, templateBucket, MASTER_TEMPLATE, masterTemplateParameters())

#if ARG_CHANGE_SET:
#    print("not implemented yet")
#    quit()
#    stackCreateChangeSet(STACK_NAME, templateBucket, MASTER_TEMPLATE, masterTemplateParameters())
#    quit()

print("temporary directory:", tempDir)
