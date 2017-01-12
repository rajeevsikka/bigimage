import json
import os
import urllib2
import time

print('Loading elasticsearch keyword function')

#ELASTICSEARCH_URL = "https://search-bigimage-2gtgp2nq3ztfednwgnd6ma626i.us-west-2.es.amazonaws.com"
ELASTICSEARCH_URL = os.environ['ELASTICSEARCH_URL']

def extractImages(tweet):
    'return a list of some of the images in a tweet'
    ret = []
    for media in tweet.get('_source', {}).get('entities', {}).get('media', {}):
        for key in ['media_url', 'media_url_https']:
            if key in media:
                ret.append(media[key])
    return ret

def extractVideos(tweet):
    'return a list of videos of the images in a tweet'
    ret = []
    for media in tweet.get('_source', {}).get('extended_entities', {}).get('media', {}):
        for variant in media.get('video_info', {}).get('variants', {}):
            ret.append(variant)
    return ret


def condensedTweets(word):
    urlString = ELASTICSEARCH_URL + '/indexname/_search'
    data = {
        "query": {
            "query_string" : {
                "query":word,
                "analyze_wildcard":True
            }
        }
    }
    request = urllib2.Request(urlString, json.dumps(data))
    f = urllib2.urlopen(request)
    resultString = f.read()

    result = json.loads(resultString)
    ret=[]
    allTweets=[]
    for tweet in result['hits']['hits']:
        allTweets.append(tweet)
        tweetEntry = {}
        tweetEntry['text'] = tweet['_source']['text']
        id = tweet['_source']['id']
        tweetEntry['url'] = 'https://twitter.com/_/status/' + str(id)
        tweetEntry['videos'] = extractVideos(tweet)
        tweetEntry['images'] = extractImages(tweet)
        ret.append(tweetEntry)
    return {'ret': ret, 'tweets': allTweets}

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    SLEEP = 5
    print("TODO leeping seconds:", SLEEP)
    time.sleep(SLEEP)
    context_vars = dict(vars(context))
    keys = list(context_vars.keys())
    queryStringParameters = event.get('queryStringParameters', {})
    if queryStringParameters is None:
        queryStringParameters = {}
    word = queryStringParameters.get('word', 'coffee')
    tweets = condensedTweets(word)
    for key in keys:
        try:
            json.dumps(context_vars[key])
        except:
            print('delete:', key)
            context_vars.pop(key)
    
    body = json.dumps({'ret':tweets, 'version': '2.2', '~environ': dict(os.environ), '~event': event, '~context': context_vars})
    ret = {
        "statusCode": 200,
        "headers": { "Access-Control-Allow-Origin": "*"},
        "body": body,
    }
    return ret
