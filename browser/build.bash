#!/bin/bash
set -ex
env
ls -l
npm install -g create-react-app
npm install
npm run build
cd build
ls -l
aws s3 rm s3://$BROWSER_S3_REF --recursive
aws s3 cp . s3://$BROWSER_S3_REF --recursive
