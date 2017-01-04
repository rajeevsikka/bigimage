# bigimage - big data image processing
Read the ppt slide deck that describes the applicaion in a lot of detail with some pictures.  In Summary:
* A run script that will create the infrastructure utilizing the teamplate mechanism for the cloud provider (aws/run.py)
* An automated build system that automatically deploys on github changes
* Tweet reader python program that reads tweets and writes into a pipe in bursts that would exceed capacity directly writing to elasticsearch
* Drain the pipe into elasticsearch
* A curl command like the following will provide the data:

    curl -XGET 'https://search-bigimage-2gtgp2nq3ztfednwgnd6ma626i.us-west-2.es.amazonaws.com/indexname/_search?pretty' -d'
    {
        "query": {
            "query_string" : {
                "query":"sous",
                "analyze_wildcard":true
            }
        }
    }'

* Twitter and git credential secrets  need to be kept securely.
Each cloud provider must have a way to do this as an example see (aws/run.py -creds)
 * TWITTER_CONSUMER_KEY
 * TWITTER_CONSUMER_SECRET
 * TWITTER_ACCESS_TOKEN
 * TWITTER_ACCESS_SECRET
 * GIT_PERSONAL_ACCESS_TOKEN

