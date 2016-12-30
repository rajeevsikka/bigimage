#!/usr/bin/python

from troposphere import (
    GetAtt, Join, Output,
    Parameter, Ref, Template, FindInMap
)

from troposphere.cloudformation import Stack

from awacs.aws import Allow, Statement, Action, Principal, Policy
from awacs.sts import AssumeRole
import firehose
import elasticsearch
import ingest
import cfnhelper
import codepipeline

INGEST = True
ELASTICSEARCH = True
FIREHOSE = True
CODEPIPELINE = True

def id():
    return 'master.cfn.json'

def template(stackName='bigimage'):
    'generate a template for this stack'
    t = Template()

    t.add_version()

    t.add_description("bigImage master which calls out to child templates: Ingest, Elasticsearch, Firehose, ...")

    templateBucket = t.add_parameter(Parameter(
        'TemplateBucket',
        Type='String',
        Description='Bucket containing all of the templates for this stack, https address, example: https://s3-us-west-2.amazonaws.com/home433331399117/master.cfn.json'
    ))

    codeBucket = t.add_parameter(Parameter(
        'CodeBucket',
        Type='String',
        Description='Bucket containing all of the templates for this stack, simple bucket name, example: elasticbeanstalk-us-west-2-433331399117'
    ))

    gitPersonalAccessToken = t.add_parameter(Parameter(
        'GitPersonalAccessToken',
        Type='String',
        Description='Git personal access token required for codepipeline'
    ))

    if ELASTICSEARCH:
        elasticsearchStack = t.add_resource(Stack(
            'ElasticsearchStack',
            TemplateURL=Join('/', [Ref(templateBucket), elasticsearch.id()]),
        ))
        # propogate all outputs from the firehose template
        cfnhelper.propogateNestedStackOutputs(t, elasticsearchStack, elasticsearch.template(), "Elasticsearch")

    if FIREHOSE:
        firehoseStack = t.add_resource(Stack(
            'FirehoseStack',
            TemplateURL=Join('/', [Ref(templateBucket), firehose.id()]),
            Parameters={'DomainArn': GetAtt(elasticsearchStack, "Outputs.DomainArn")},
        ))
        # propogate all outputs from the firehose template
        cfnhelper.propogateNestedStackOutputs(t, firehoseStack, firehose.template(), "Firehose")

    if INGEST:
        ingestStack = t.add_resource(Stack(
            'IngestStack',
            TemplateURL=Join('/', [Ref(templateBucket), ingest.id()]),
            Parameters={
                'CodeBucket': Ref(codeBucket),
                'DeliveryStreamName': GetAtt(firehoseStack, "Outputs.DeliveryStreamName"),
            },
        ))
        # propogate all outputs from the firehose template
        cfnhelper.propogateNestedStackOutputs(t, ingestStack, ingest.template(), "Ingest")

    if CODEPIPELINE:
        codepipelineStack = t.add_resource(Stack(
            'CodepipelineStack',
            TemplateURL=Join('/', [Ref(templateBucket), codepipeline.id()]),
            Parameters={
                'IngestApplicationName': GetAtt(ingestStack, "Outputs.ApplicationName"),
                'IngestEnvironmentName': GetAtt(ingestStack, "Outputs.EnvironmentName"),
                'GitPersonalAccessToken': Ref(gitPersonalAccessToken),
            },
        ))
        cfnhelper.propogateNestedStackOutputs(t, codepipelineStack, codepipeline.template(), "Codepipeline")

    return t



if __name__ == "__main__":
    print(template('foo').to_json())
