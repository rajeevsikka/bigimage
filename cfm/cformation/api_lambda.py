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
from troposphere.apigateway import Deployment, StageDescription, MethodSetting
from troposphere.apigateway import ApiKey, StageKey

import os
import cfnhelper

REST_API = True # can turn off for testing
STAGE_NAME = 'v1'

def id():
    return 'api_lambda.cfn.json'

def fileAsString(fileName):
    'Return the string that is in a sibling file'
    cwd = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    with open(os.path.join(cwd, fileName), 'r') as myfile:
        ret=myfile.read()
    return ret

def jsonFunctionStringApiGatewayMapping():
    return fileAsString('api_gateway_mapping.json')

def lambdaFunctionKeyword():
    return fileAsString('lambda_keyword.py')

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

    # read the lambda function from a file
    codeString=lambdaFunctionKeyword()

    apiRequestTemplateString=jsonFunctionStringApiGatewayMapping()

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

    # Create an HTTP GET rest api method for the keywordFunction Lambda resource
    uri=Join("/", [
        lambdaFunctionsJoin,
        GetAtt(keywordFunction, "Arn"),
        'invocations', # TODO why isn't this pathPart=keyword?
    ])

    # api gateway ----------------------------------------------------------

    if REST_API:
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

        methodRequestQuerystringWord = 'method.request.querystring.word'
        restApiKeywordGetMethod = t.add_resource(Method(
            "KeywordGET",
            ApiKeyRequired=False,
            AuthorizationType="NONE",
            #AuthorizerId
            DependsOn=keywordFunction.name, # not part of the API?
            HttpMethod="GET",
            RequestParameters={
                methodRequestQuerystringWord: True,
            },
            RestApiId=Ref(rest_api),
            ResourceId=Ref(resource),
            Integration=Integration(
                CacheKeyParameters=[methodRequestQuerystringWord],
                Credentials=GetAtt(lambdaExecutionRole, "Arn"),
                Type="AWS_PROXY",
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
                    ResponseModels={"application/json": "Empty"},
                    StatusCode='200'
                )
            ],
        ))

        # Create a deployment
        deployment = t.add_resource(Deployment(
            "%sDeployment" % STAGE_NAME,
            DependsOn=restApiKeywordGetMethod.name,
            RestApiId=Ref(rest_api),
            StageDescription=StageDescription(
                CacheClusterEnabled=True, # : (bool, False),
                CacheClusterSize="0.5", # : (basestring, False),
                CacheDataEncrypted=False, # : (bool, False),
                #CacheTtlInSeconds=30, # : (positive_integer, False),
                #CachingEnabled=True, # : (bool, False),
                #ClientCertificateId= : (basestring, False),
                #DataTraceEnabled=False, # : (bool, False),
                Description="Cached stage ttl=30, cache size = 0.5G", # : (basestring, False),
                #LoggingLevel= : (basestring, False),
                MethodSettings=[MethodSetting(
                    #CacheDataEncrypted=False, #: (bool, False),
                    CacheTtlInSeconds=30, #": (positive_integer, False),
                    CachingEnabled=True, #": (bool, False),
                    #DataTraceEnabled= False, #": (bool, False),
                    HttpMethod='*', # : (basestring, True),
                    #LoggingLevel= "OFF", #: (basestring, False),
                    #MetricsEnabled=False, # : (bool, False),
                    ResourcePath='/*', # : (basestring, True),
                    #ThrottlingBurstLimit=2000, # : (positive_integer, False),
                    #ThrottlingRateLimit=1000, # : (positive_integer, False)
                )],
                MetricsEnabled=False, # : (bool, False),
                StageName=STAGE_NAME, # : (basestring, False),
                #ThrottlingBurstLimit= : (positive_integer, False),
                #ThrottlingRateLimit= : (positive_integer, False),
                #Variables= : (dict, False)
            ),
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
    outputs = []
    if REST_API:
        outputs.append(Output(
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
        ))
    outputs.append(Output(
        "LambdaEndpoint",
        Value=uri,
        Description="Lambda calculated endpoint"
    ))
    t.add_output(outputs)

    return t

if __name__ == "__main__":
    print(template().to_json())
