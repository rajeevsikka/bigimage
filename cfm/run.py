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

TWITTER_VARIABLES = ['TWITTER_CONSUMER_KEY', 'TWITTER_CONSUMER_SECRET', 'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET']

# command line parsing
parser = argparse.ArgumentParser(description="""Look at the switches below and notice the commands.
You can run any of these commands individually.
If none of the commands are specified then following commands will be run in order: -delete, -code, -template, -create.
Before the create or update commands are run the twitter credentials will be verified.
If twitter credential verification fails, fix the problem by setting the env variables and using the -p switch.
In addition it can be useful to execute -template followed by -update to make changes to the templates then update the existing stack.
The -name parameter can be used to create multiple stacks, you must use the same name to delete, update, etc.
""") 
parser.add_argument('-delete', action='store_true', help='command: delete the buckets and the stack')
parser.add_argument('-code', action='store_true', help='command: generate code in temporary directory, create s3 bucket, upload code s3 bucket')
parser.add_argument('-template', action='store_true', help='command: generate cloudformation templates in the temporary directory, create cfn bucket, put the templates into the cfn bucket')
parser.add_argument('-create', action='store_true', help='command: create the stack from the cloud formation templates created with -template')
parser.add_argument('-update', action='store_true', help='command: update the stack (normally run with -template)')
parser.add_argument('-creds', action='store_true', help='command: store twitter credentials, set these environment variables then use the -p option to store them:' + str(TWITTER_VARIABLES))
parser.add_argument('-k', action='store_true', default=False, help='keep the temporary directory of files that were uploaded to s3')
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
ARG_KEEP = args.k
ARG_NAME = args.n

# commands
ARG_DELETE = args.delete
ARG_CODE = args.code
ARG_TEMPLATE = args.template
ARG_CREATE = args.create
ARG_UPDATE = args.update
ARG_CREDS = args.creds

if (not ARG_DELETE) and (not ARG_CODE) and (not ARG_TEMPLATE) and (not ARG_CREATE) and (not ARG_UPDATE) and (not ARG_CREDS):
    ARG_DELETE = True
    ARG_CODE = True
    ARG_TEMPLATE = True
    ARG_CREATE = True
    

# constants
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


def verifyTwitterCreds():
    "veriy that all of the twitter variables for this stack exist"
    names = namedTwitterVariables()
    ret = ssm.get_parameters(Names=names, WithDecryption=True)
    parameters = ret[u'Parameters']
    for parameter in parameters:
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

def generateAndUploadDir(bucket, inputDir, outputDir):
    'inputDir is a directory that contains a makeawszip.sh script, call the script to create an inputDir.zip file and upload it'
    #TODO added a _20, this is a kludge, see similar kludge in ingest.py
    VERSION="_21" # TODO
    outputFile = os.path.join(outputDir, inputDir + VERSION) # name the file portion of the output zip the same as the directory name #TODO
    systemCmd = "../" + inputDir + '/makeawszip.sh ' + outputFile
    silentPrint("execute:", systemCmd)
    os.system(systemCmd)
    file = outputFile + ".zip"
    #key = inputDir + VERSION + ".zip" # TODO
    key = inputDir + ".zip" # TODO
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

if ARG_CREDS:
    if not storeTwitterCreds():
        quit()

if ARG_DELETE:
    stackDelete(STACK_NAME)
    bucketDelete(S3_TEMPLATE_BUCKET)
    bucketDelete(S3_CODE_BUCKET)

tempDir = tempfile.mkdtemp()
silentPrint("temporary directory:", tempDir)

# generate new code zips
if ARG_CODE:
    generateAndUploadCode(tempDir, S3_CODE_BUCKET)

# populate template bucket with fresh templates.  Generate them in the temporary directory then copy them to s3
templateBucket = s3.Bucket(S3_TEMPLATE_BUCKET)
if ARG_TEMPLATE:
    if not bucketExists(templateBucket):
        bucketNew(templateBucket)

    generateCfn(tempDir)
    bucketPopulate(tempDir, templateBucket)

if ARG_CREATE:
    if not verifyTwitterCreds():
        quit()
    stackCreate(STACK_NAME, templateBucket, MASTER_TEMPLATE, MASTER_TEMPLATE_PARAMETERS)

if ARG_UPDATE:
    if not verifyTwitterCreds():
        quit()
    stackUpdate(STACK_NAME, templateBucket, MASTER_TEMPLATE, MASTER_TEMPLATE_PARAMETERS)

#if ARG_CHANGE_SET:
#    print("not implemented yet")
#    quit()
#    stackCreateChangeSet(STACK_NAME, templateBucket, MASTER_TEMPLATE, MASTER_TEMPLATE_PARAMETERS)
#    quit()

if ARG_KEEP:
    print("temporary directory:", tempDir)
else:
    shutil.rmtree(tempDir)
