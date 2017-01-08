#!/bin/bash
set -ex
env
ls -l
npm install -g create-react-app
npm install
npm run build
cd build
ls -lR
aws s3 rm S3://$BROWSER_S3_REF --recursive
aws s3 cp . S3://$BROWSER_S3_REF --recursive
