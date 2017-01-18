# ibm blue mix
Experience with bluemix
## template
No infrastructure as code templates.
It is required that I write a script to create/destroy/change infrastructure by hand
### python script
Search: aws python api for provisioning services.
Top hit: boto3 - I used this on aws, it worked great.

Search: ibm bluemix python api for provisioning services.
Hits: cloud foundry apps written in python.  No provisioning support.

Bummer
### shell script
cf api https://api.ng.bluemix.net
cf login
cf create-service compose-for-elasticsearch Standard my-compose-for-elasticsearch-service
cf bind-service compose-elasticsearch-helloworld-nodejs my-compose-for-elasticsearch-service

failed to provision ES

cf dsk -f bigimage-messagehub creds
cf ds -f bigimage-messagehub
bx service create messagehub standard bigimage-messagehub
cf csk bigimage-messagehub creds
cf delete -f bigimage-ingest
cf delete-orphaned-routes -f
cd ibm/ingest
cf push; # will fail, keep going
~/thhatwitter.bash bigimage-ingest
cf push
cf logs --recent bigimage-ingest
cf map-route bigimage-ingest mybluemix.net --hostname bigimage-ingest
open https://bigimage-ingest.mybluemix.net

https://developer.ibm.com/messaging/2016/12/05/updated-message-hub-samples/ - blog post on nodejs usage


# Details
Provisioned using the docs here and it failed: https://github.com/IBM-Bluemix/compose-elasticsearch-helloworld-nodejs
Opened the ticket, got email from "softlayer".  What is softlayer?  I was using Bluemix.

There are two featured links in the provisioned message hub service:
* Message Connect that was deleted a month ago.
* Streaming analytics that requires a VMWare image to demonstrate (are you kidding me)

Why are there two command lines: bx and cf with overlapping functionality?  This is making the system harder to learn.

host name is truncated by the cf routes command - can not delete it
cf routes
Getting routes for org billhart@us.ibm.com / space Powell as pquiring@us.ibm.com ...

space    host                            domain          port   path   type   apps             service
Powell   message-hub-chat-setaceous-qt   mybluemix.net

~/work/github.com/powellquiring/bigimage/ibm/ingest$ cf dsk -f 'Compose for Elasticsearch-83' 'Credentials-1'
Deleting key Credentials-1 for service instance Compose for Elasticsearch-83 as pquiring@us.ibm.com...
OK
Service instance Compose for Elasticsearch-83 does not exist.
~/work/github.com/powellquiring/bigimage/ibm/ingest$ cf s
Getting services in org billhart@us.ibm.com / space Powell as pquiring@us.ibm.com...
OK

name                           service                     plan       bound apps   last operation
Compose for Elasticsearch-7c   compose-for-elasticsearch   Standard                create succeeded
Compose for Elasticsearch-83   compose-for-elasticsearch   Standard                create succeeded
Compose for MongoDB-ps         compose-for-mongodb         Standard                create succeeded

~/work/github.com/powellquiring/bigimage/ibm/ingest$ cf ds -f 'Compose for Elasticsearch-83'
Deleting service Compose for Elasticsearch-83 in org billhart@us.ibm.com / space Powell as pquiring@us.ibm.com...
FAILED
Cannot delete service instance, service keys and bindings must first be deleted
~/work/github.com/powellquiring/bigimage/ibm/ingest$
