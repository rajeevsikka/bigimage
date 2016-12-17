#cfm aws Cloudformation Templates
* cformation - python trophosphere implementation of cloudformation templates
* run.py - script to create a bucket for the templates, generate the templates in the cformation/ directory
and copy the templates to the bucket. It also creates a code bucket and assembles the code and copies it to the code bucket.
It then runs the cloudformation.
Try ./run.py -h for more information

    # build everything, copy, run, ... from scratch (delete it if it already exists)
    ./run.py

    # delete everything and quit (no building)
    ./run.py -d

Take another look at:

http://docs.aws.amazon.com/firehose/latest/dev/controlling-access.html#using-iam-s3
