# bigimage - big data image processing
Read the ppt slide deck that describes the applicaion in a lot of detail with some pictures.  In Summary:
* Twitter and git credential secrets  need to be kept securely.
Set the following environment variables and execute: aws/run.py -creds
 * TWITTER_CONSUMER_KEY
 * TWITTER_CONSUMER_SECRET
 * TWITTER_ACCESS_TOKEN
 * TWITTER_ACCESS_SECRET
 * GIT_PERSONAL_ACCESS_TOKEN
* A run script that will create the infrastructure utilizing the teamplate mechanism for the cloud provider (cfm/run.py)
* In aws open cloudeformation see the stacks created, the main stack has the default name: bigimage
* Delete the main stack at any time to delete most resources, s3 buckets are configured not to be deleted (non empty s3 buckets will fail to delete by cformation)
* see the output section of the main cloudformation stack, See the kibana link for elastisearch, ingestURL for the twitter reader, and the CodepipelineBrowserS3WebsiteUrl for the application
* An automated build system (codepipeline steps that call out to codebuild actions) any future updates to the github project will re-build.
For example change the file python-v1/application/application.py VERSION string and take a look at the ingestURL.
* Tweet reader python program (python-v1) that reads tweets and writes into a pipe in bursts that would exceed capacity directly writing to elasticsearch
* Drain the pipe into elasticsearch
* A curl command like the following would retrieve data from elastic search after the index is created (

    curl -XGET 'https://search-bigimage-2gtgp2nq3ztfednwgnd6ma626i.us-west-2.es.amazonaws.com/indexname/_search?pretty' -d'
    {
        "query": {
            "query_string" : {
                "query":"sous",
                "analyze_wildcard":true
            }
        }
    }'

# Restricting access to credentials
The above credentials are only accessible to those that have access to my aws account.
If the account is used for a project with lots of users then all the users would have access to the creds.
I ran the following test to verify that the --key-id parameter could be used to restrict access to a smaller set of users by using IAM policies.
A role assigned to the twitter ingest app would need to have access to the kms key as well.

Create a yesuser and nouser and give them ssm capabilities.
Created a kms key "deleteme" in us-west-2.
When creating the key give yesuser all of the capabilities to use the key (nouser gets nothing)
The arn is included in the commands below

Test creating with yes user and get with yesuser and no user.  nouser should have access:
    aws ssm put-parameter --name nokey --value secret --type SecureString
    aws ssm get-parameters --names nokey --with-decryption


Test again using the --key-id arn that only the yesuser has access and verify that the nouser can not get to this key:
    aws ssm put-parameter --name yeskey --value secret2 --type SecureString --key-id arn:aws:kms:us-west-2:433331399117:key/c92ffcf8-1d03-40ce-80ca-9ccf7f648ea2
    aws ssm get-parameters --names yeskey --with-decryption 


Create access keys for each user.  Something like the following:

    yesuser
    export AWS_ACCESS_KEY_ID=AKIAJC5TYZIBO4OTPTBA
    export AWS_SECRET_ACCESS_KEY=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
    PS1='yes $'

    nouser
    export AWS_ACCESS_KEY_ID=AKIAJOSHBLTHBTDQPSYA
    export AWS_SECRET_ACCESS_KEY=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
    PS1='no $'

