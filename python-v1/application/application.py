#!/usr/bin/env python

VERSION = "2.2"
# To work the following environment variables must be set:
# * StackName - twitter credentials are stored in the the aws system manager parameter store prefixed by this name (see TWITTER_VARIABLES)
# * DeliveryStreamName - firehose delivery stream name
#
# The aws system manager parameter store must have the StackName prefixed secure string values
# identified in TWITTER_VARIABLES below: $StackName_TWITTER_CONSUMER_KEY, like bigimage_TWITTER_CONSUMER_KEY for example

from flask import Flask, jsonify
import boto.utils
import boto3
import os
import threading, time
import requests
import sys
from pprint import pprint

TWITTER_VARIABLES = ['TWITTER_CONSUMER_KEY', 'TWITTER_CONSUMER_SECRET', 'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET']
firehose = boto3.client('firehose')

application = Flask(__name__)

main = True

STACK_NAME = os.environ.get('StackName')
if STACK_NAME is None:
    print "StackName not in environment, quitting"
    quit()
print "STACK_NAME:", STACK_NAME

DELIVERY_STREAM_NAME = os.environ.get('DeliveryStreamName')
if DELIVERY_STREAM_NAME is None:
    print "DeliveryStreamName not in environment, quitting"
    quit()
print "DELIVERY_STREAM_NAME:", DELIVERY_STREAM_NAME
fetchedStreams = firehose.list_delivery_streams()
print "firehose streams:", fetchedStreams
fetchedStreamNames = fetchedStreams['DeliveryStreamNames']
if not (DELIVERY_STREAM_NAME in fetchedStreamNames):
    print "Delivery stream not found, looking for:", DELIVERY_STREAM_NAME
    print "Existing stream names:", fetchedStreamNames
    quit()


def stackName(name):
    "turn a environment variable name into a stack specific name"
    return STACK_NAME + "_" + name

def namedTwitterVariables():
    "return the stack named twitter variables"
    ret = []
    for name in TWITTER_VARIABLES:
        ret.append(stackName(name))
    return ret

def verifyTwitterCreds():
    "veriy that all of the twitter variables for this stack exist"
    stackNameValue={}
    names = namedTwitterVariables()
    ssm = boto3.client('ssm')

    ret = ssm.get_parameters(Names=names, WithDecryption=True)
    parameters = ret[u'Parameters']
    for parameter in parameters:
        print("found name:", parameter['Name'])
        stackNameValue[parameter['Name']] =  parameter['Value']
    invalidParameters = ret['InvalidParameters']
    if len(invalidParameters) > 0:
        print("ERROR: missing the following aws secure string, system manager,  parameter store, parameters:", str(invalidParameters))
        quit()
    return stackNameValue

def isAws():
    'Return True if the program is running on an ec2 instance'
    ret = False
    try:
        with open("/sys/hypervisor/uuid") as f:
            c = f.read(3)
            if c == "ec2":
                ret = True
    finally:
        return ret

def metadata():
    'Return  the metadata dictionary or the string "none" if there is no metadata'
    if isAws():
        return boto.utils.get_instance_metadata()
    else:
        return "none"

jsonArray = [
    {
        'metadata': metadata()
    }
]

tweetCount = 0

@application.route('/', defaults={'path': '/'}, methods=['GET'])
@application.route('/<path:path>', methods=['GET'])
def dump(path):
    return jsonify({'~env': dict(os.environ), '~metadata': jsonArray, '~errorStatus': errorStatuses, 'tweetCount': tweetCount, 'env StackName': STACK_NAME, 'env DeliveryStreamName': DELIVERY_STREAM_NAME, 'path': path, 'main': main, 'version': VERSION})

##################### twitter ###################
import tweepy
from tweepy import Stream
from tweepy.streaming import StreamListener
import json
from threading import Thread

# override _start to fix <control>-C
class MyStream(Stream):
    def _start(self, async):
        print "MyListener, _start"
        self.running = True
        if async:
            self._thread = Thread(target=self._run)
            self._thread.daemon = True  # this is the only change I want to make so that <contro>-C works
            self._thread.start()
        else:
            self._run()

errorStatuses=[]
def logErrorStatus(status):
    try:
        # verify that it can be encoded as json
        json.dumps(status)
    except:
        # not json 
        print "logErrorStatus", {'type': str(type(status)), 'value': str(status)}
        errorStatuses.insert(0, {'type': str(type(status)), 'value': str(status)})
    else:
        print "logErrorStatus", status
        errorStatuses.insert(0, status)

def process_status_firehose(status):
    js = process_status(status)
    ret = firehose.put_record(DeliveryStreamName=DELIVERY_STREAM_NAME, Record={'Data': js})
    print "ret:", ret
    return ret

def process_status(status):
    print type(status)
    j = json.loads(status)
    js = json.dumps(j) + "\n"
    newstatus = json.loads(js)
    print json.dumps(newstatus, indent=4, sort_keys=True)
    return js

def process_friend(friend):
    #pprint(vars(friend))
    print friend.name, friend.screen_name

class MyListener(StreamListener):
    def on_data(self, data):
        global tweetCount
        tweetCount += 1
        process_status_firehose(data)
        return True

    def on_error(self, status):
        print("Error, status:", status)
        logErrorStatus(status)
        return True

stackNameValue = verifyTwitterCreds()

auth = tweepy.OAuthHandler(stackNameValue[stackName('TWITTER_CONSUMER_KEY')], stackNameValue[stackName('TWITTER_CONSUMER_SECRET')])
auth.set_access_token(stackNameValue[stackName('TWITTER_ACCESS_TOKEN')], stackNameValue[stackName('TWITTER_ACCESS_SECRET')])

api = tweepy.API(auth)

def testingTweepy():
    # Iterate through all of the authenticated user's friends
    for friend in tweepy.Cursor(api.friends).items():
        # Process the friend here
        process_friend(friend)

    # Iterate through the first 200 statuses in the friends timeline
    for status in tweepy.Cursor(api.home_timeline).items(100):
        # Process the status here
        process_status(status)


twitter_stream = MyStream(auth, MyListener())
tracks = [
    '#peoplewhomademy2016',
]
follows = [
    '@powellquiring',
]

def handleTwitter():
    while True:
        try:
            #twitter_stream.filter(track=tracks, async=True)
            #twitter_stream.filter(follow=follows, async=True)
            print "handleTwitter userstream"
            twitter_stream.userstream(_with='following')
        except requests.exceptions.ConnectionError as ex:
            print "twitter userstream ConnectionError exception:", ex
            logErrorStatus(ex)
        except Exception as ex:
            print "twitter userstream Exception, type:", type(ex), "exception:", ex
            logErrorStatus(ex)
        except:
            ex = sys.exc_info()[0]
            print "twitter userstream unexpected, type:", type(ex), "exception:", ex
            logErrorStatus(ex)
        time.sleep(5)


##################### twitter start ###################
t = threading.Thread(target=handleTwitter)
t.daemon = True
t.start()

##################### application start ###################
if __name__ == '__main__':
    application.run()
else:
    main = False
