#!/bin/bash
STACK_NAME=bigimagestackname
json=$( ./ingest.py )
set -ex
rm -f bigimage.zip
../biApi/makeawszip.sh bigimage
aws s3 cp bigimage.zip s3://elasticbeanstalk-us-west-2-433331399117
echo "$json" > /tmp/x
aws cloudformation delete-stack --stack-name $STACK_NAME
if [ $? -eq 0 ]; then
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME
fi

echo aws cloudformation create-stack --capabilities CAPABILITY_IAM --stack-name $STACK_NAME --template-body /tmp/x
aws cloudformation create-stack --capabilities CAPABILITY_IAM --stack-name $STACK_NAME --template-body "$json"
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME
