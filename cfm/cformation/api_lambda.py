#!/usr/bin/python

from troposphere import Template, Parameter, Ref, Output, Join, Tags, GetAtt, AWS_REGION

from troposphere.iam import Role
from troposphere.iam import PolicyType as IAMPolicy
from troposphere.iam import Policy as TropospherePolicy

from awacs.aws import Allow, Statement, Action, Principal, Policy
from awacs.sts import AssumeRole

from troposphere_early_release.awslambda import Environment, Function, Code
from troposphere.apigateway import RestApi, Method
from troposphere.apigateway import Resource, MethodResponse
from troposphere.apigateway import Integration, IntegrationResponse
from troposphere.apigateway import Deployment
from troposphere.apigateway import ApiKey, StageKey

import cfnhelper

METHOD = True  # just testing
STAGE = True  # just testing
STAGE_NAME = 'v2'

def id():
    return 'api_lambda.cfn.json'

def template(stackName='bigimage'):
    t = Template()
    t.add_version('2010-09-09')
    t.add_description('api gateway connected to the lambda functions that read stuff like elasticsearch')

    # lambda function ----------------------------------------------------------

    # must be parameters
    elasticsearchUrl = 'https://search-bigimage-2gtgp2nq3ztfednwgnd6ma626i.us-west-2.es.amazonaws.com'
    elasticsearchIndex = 'indexname'
    
    # could be parameters
    memorySize = '128'
    timeout = '60'

    # join these two together to make region specific access to lambda functions at stack creation time
    # for example (notice us-west-2) arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions
    apiGateway = "arn:aws:apigateway"
    apiLambda = "lambda:path/2015-03-31/functions"
    lambdaFunctionsJoin = Join(":", [apiGateway, Ref(AWS_REGION), apiLambda])

    # TODO should the code be in here?
    codeString='''
import json
import os
import urllib2

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
    for tweet in result['hits']['hits']:
        tweetEntry = {}
        tweetEntry['text'] = tweet['_source']['text']
        id = tweet['_source']['id']
        tweetEntry['url'] = 'https://twitter.com/_/status/' + str(id)
        tweetEntry['videos'] = extractVideos(tweet)
        tweetEntry['images'] = extractImages(tweet)
        ret.append(tweetEntry)
    return ret

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    context_vars = dict(vars(context))
    keys = list(context_vars.keys())
    word = event.get('params', {}).get('querystring', {}).get('word', 'coffee')
    tweets = condensedTweets(word)
    for key in keys:
        try:
            json.dumps(context_vars[key])
        except:
            print('delete:', key)
            context_vars.pop(key)
    
    ret = {'ret':tweets, 'version': '2.2', '~environ': dict(os.environ), '~event': event, '~context': context_vars}
    return ret

'''

    apiRequestTemplateString='''
##  See http://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-mapping-template-reference.html
##  This template will pass through all parameters including path, querystring, header, stage variables, and context through to the integration endpoint via the body/payload
#set($allParams = $input.params())
{
"body-json" : $input.json('$'),
"params" : {
#foreach($type in $allParams.keySet())
    #set($params = $allParams.get($type))
"$type" : {
    #foreach($paramName in $params.keySet())
    "$paramName" : "$util.escapeJavaScript($params.get($paramName))"
        #if($foreach.hasNext),#end
    #end
}
    #if($foreach.hasNext),#end
#end
},
"stage-variables" : {
#foreach($key in $stageVariables.keySet())
"$key" : "$util.escapeJavaScript($stageVariables.get($key))"
    #if($foreach.hasNext),#end
#end
},
"context" : {
    "account-id" : "$context.identity.accountId",
    "api-id" : "$context.apiId",
    "api-key" : "$context.identity.apiKey",
    "authorizer-principal-id" : "$context.authorizer.principalId",
    "caller" : "$context.identity.caller",
    "cognito-authentication-provider" : "$context.identity.cognitoAuthenticationProvider",
    "cognito-authentication-type" : "$context.identity.cognitoAuthenticationType",
    "cognito-identity-id" : "$context.identity.cognitoIdentityId",
    "cognito-identity-pool-id" : "$context.identity.cognitoIdentityPoolId",
    "http-method" : "$context.httpMethod",
    "stage" : "$context.stage",
    "source-ip" : "$context.identity.sourceIp",
    "user" : "$context.identity.user",
    "user-agent" : "$context.identity.userAgent",
    "user-arn" : "$context.identity.userArn",
    "request-id" : "$context.requestId",
    "resource-id" : "$context.resourceId",
    "resource-path" : "$context.resourcePath"
    }
}
'''

    code = codeString.split("\n") #TODO remove
    ####### delete me end

    # Create the role with a trust relationship that allows lambda or the api gateway to assume the role
    lambdaExecutionRole = t.add_resource(Role(
        "LambdaExecutionRole",
        AssumeRolePolicyDocument=Policy(
            Version="2012-10-17",
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[AssumeRole],
                    Principal=Principal(
                        "Service", [
                            'lambda.amazonaws.com',
                            'apigateway.amazonaws.com',
                        ]
                    )
                )
            ]
        ),
        Path="/",
        Policies=[TropospherePolicy(
            "LambdaExecutionPolicy",
            PolicyName="LambdaExecutionPolicy",
            PolicyDocument=Policy(
                Statement=[
                    Statement(
                        Effect=Allow,
                        NotAction=Action("iam", "*"),
                        Resource=["*"],),
                ]
            ),
        )],
    ))

    keywordFunction = t.add_resource(Function(
        "KeywordFunction",
        Code=Code(
            #ZipFile=Join('\n', code)
            ZipFile=codeString
        ),
        Description='convert word parameter to keywords, pull the records with the keywords from elasticsearch',
        Environment=Environment(Variables={
            'ELASTICSEARCH_URL': elasticsearchUrl,
            'ELASTICSEARCH_INDEX': elasticsearchIndex,
        }),
        #FunctionName=generated
        Handler="index.lambda_handler",
        Role=GetAtt(lambdaExecutionRole, "Arn"),
        Runtime="python2.7",
        MemorySize=memorySize,
        Timeout=timeout,
    ))

    # api gateway ----------------------------------------------------------

    # Create the Api Gateway
    rest_api = t.add_resource(RestApi(
        stackName + "restapi",
        Name=stackName + "restapi",
    ))

    # Create the api resource (.ie a path) /keyword
    pathPart = 'keyword'
    resource = t.add_resource(Resource(
        "KeywordSearchResource",
        RestApiId=Ref(rest_api),
        PathPart=pathPart,
        ParentId=GetAtt(rest_api, "RootResourceId"), # / is created when the RestApi is added
    ))

    # Create an HTTP GET rest api method for the keywordFunction Lambda resource
    uri=Join("/", [
        lambdaFunctionsJoin,
        GetAtt(keywordFunction, "Arn"),
        'invocations', # TODO why isn't this pathPart=keyword?
    ])

    if METHOD:
        restApiKeywordGetMethod = t.add_resource(Method(
            "KeywordGET",
            ApiKeyRequired=False,
            AuthorizationType="NONE",
            #AuthorizerId
            DependsOn=keywordFunction.name, # not part of the API?
            HttpMethod="GET",
            RequestParameters={
                'method.request.querystring.word': False,
            },
            RestApiId=Ref(rest_api),
            ResourceId=Ref(resource),
            Integration=Integration(
                Credentials=GetAtt(lambdaExecutionRole, "Arn"),
                Type="AWS",
                IntegrationHttpMethod='POST', #TODO changed from GET
                IntegrationResponses=[
                    IntegrationResponse(
                        #ResponseTemplates={    #TODO added
                        #    "application/json": None # null not allowed
                        #},
                        StatusCode='200'
                    ),
                ],
                PassthroughBehavior='WHEN_NO_MATCH', # TODO specified default
                RequestTemplates={'application/json': apiRequestTemplateString},
                Uri=uri,
            ),
            MethodResponses=[
                MethodResponse(
                    "CatResponse",
                    StatusCode='200'
                )
            ],
        ))

        if STAGE:
            # Create a deployment
            deployment = t.add_resource(Deployment(
                "%sDeployment" % STAGE_NAME,
                DependsOn=restApiKeywordGetMethod.name,
                RestApiId=Ref(rest_api),
                StageName=STAGE_NAME
            ))

        #key = t.add_resource(ApiKey(
        #    "ApiKey",
        #    StageKeys=[StageKey(
        #        RestApiId=Ref(rest_api),
        #        StageName=STAGE_NAME
        #    )]
        #))

    # Add the deployment endpoint as an output
    # TODO fix up this for REGION
    t.add_output([
        Output(
            "ApiEndpoint" + pathPart,
            Value=Join("", [
                "https://",
                Ref(rest_api),
                ".execute-api.",
                Ref(AWS_REGION),
                ".amazonaws.com/",
                STAGE_NAME,
                "/",
                pathPart,
            ]),
            Description="Endpoint for this stage of the api"
        ),
        Output(
            "LambdaEndpoint",
            Value=uri,
            Description="Lambda calculated endpoint"
        ),
    ])


    return t

if __name__ == "__main__":
    print(template().to_json())
