# bigimage - big data image processing
Read the ppt slide deck that describes the applicaion in a lot of detail with some pictures.  In Summary:
* A run script that will create the infrastructure utilizing the teamplate mechanism for the cloud provider (aws/run.py)
* Tweet reader python program that reads tweets and writes into elasticsearch through a pipe.
Twitter credential secrets  need to be kept securely.
Each cloud provider must have a way to do this (aws/run.py -p)
    TWITTER_CONSUMER_KEY
    TWITTER_CONSUMER_SECRET
    TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_SECRET
* The pipe
