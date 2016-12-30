#cfm aws Cloudformation Templates
* cformation - python trophosphere implementation of cloudformation templates
* run.py - script to create a bucket for the templates, generate the templates in the cformation/ directory
and copy the templates to the bucket. It also creates a code bucket and assembles the code and copies it to the code bucket.
It then runs the cloudformation.
Try ./run.py -h for more information

Set up your environment, one time:

    pip install virtualenv
    ./afterclone.sh

Then each time you want to run the program in a new shell:

   source ./sourceme

Then use it:

    # build everything, copy, run, ... from scratch (delete it if it already exists)
    ./run.py -h

# codepipeline
* Create a personal access token (get it from powell?) [Aws from github](http://docs.aws.amazon.com/codepipeline/latest/userguide/troubleshooting.html#troubleshooting-gs2)
* Build - execute the run.py script

# More work
Take another look at:
http://docs.aws.amazon.com/firehose/latest/dev/controlling-access.html#using-iam-s3
