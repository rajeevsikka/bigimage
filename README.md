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

