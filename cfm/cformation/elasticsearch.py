#!/usr/bin/env python
from troposphere import Template, constants, Output, GetAtt, Tags, Join
from troposphere.elasticsearch import Domain, EBSOptions
from troposphere.elasticsearch import ElasticsearchClusterConfig
from troposphere.elasticsearch import SnapshotOptions

# not sure how to parameterize...
INSTANCE_TYPE = constants.ELASTICSEARCH_T2_SMALL
INSTANCE_TYPE = constants.ELASTICSEARCH_T2_MICRO

import cfnhelper

def id():
    return 'elasticsearch.cfn.json'

def template(stackName='bigimage'):
    domainName = stackName
    t = Template()

    t.add_description('Elasticsearch for ' + stackName)

    es_domain = t.add_resource(Domain(
        stackName + 'ElasticsearchDomain',
        AccessPolicies={'Version': '2012-10-17',
                        'Statement': [{
                            'Effect': 'Allow',
                            'Principal': {
                                'AWS': '*'
                            },
                            'Action': 'es:*',
                            'Resource': '*'
                        }]},
        AdvancedOptions={"rest.action.multi.allow_explicit_index": "true"},
        DomainName=domainName,
        EBSOptions=EBSOptions(EBSEnabled=True,
                              Iops=0,
                              VolumeSize=10,
                              VolumeType="gp2"),
        ElasticsearchClusterConfig=ElasticsearchClusterConfig(
            DedicatedMasterEnabled=False,
            InstanceCount=1,
            ZoneAwarenessEnabled=False,
            InstanceType=INSTANCE_TYPE
        ),
        ElasticsearchVersion='2.3',
        SnapshotOptions=SnapshotOptions(AutomatedSnapshotStartHour=0),
        Tags=Tags(stage=cfnhelper.STAGE),
    ))

    # handle to the results
    t.add_output(
        Output(
            "DomainName",
            Description="Domain name like: bigimage.  Needed as an endpiont for elasticsearch configuration",
            Value=domainName,
        )
    )
    t.add_output(
        Output(
            "DomainArn",
            Description="The Amazon Resource Name (ARN) of the domain, such as arn:aws:es:us-west-2:123456789012:domain/mystack-elasti-1ab2cdefghij",
            Value=GetAtt(es_domain, "DomainArn"),
        )
    )
    t.add_output(
        Output(
            "DomainEndpoint",
            Description="The domain-specific endpoint that is used to submit index, search, and data upload requests to an Amazon ES domain, such as search-mystack-elasti-1ab2cdefghij-ab1c2deckoyb3hofw7wpqa3cm.us-west-2.es.amazonaws.com",
            Value=GetAtt(es_domain, "DomainEndpoint"),
        )
    )
    t.add_output(
        Output(
            "DomainURL",
            Description="The https domain-specific endpoint",
            Value=Join("/", ["https:/", GetAtt(es_domain, "DomainEndpoint")]),
        )
    )
    t.add_output(
        Output(
            "KibanaURL",
            Description="The Kibana endpoint",
            Value=Join("/", ["https:/", GetAtt(es_domain, "DomainEndpoint"),"_plugin/kibana/"]),
        )
    )
    return t

if __name__ == "__main__":
    print(template().to_json())
