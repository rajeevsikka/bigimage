from troposphere import Output, GetAtt

STAGE = 'prod'
def propogateNestedStackOutputs(t, nestedStack, nestedTemplate, prefixString): 
    'propoage all fo the ouptuts of the nestedStack assuming they were provided by the nestedTemplate'
    for k in nestedTemplate.outputs:
        output = nestedTemplate.outputs[k]
        t.add_output(Output(
            prefixString + k,
            Description=output.Description,
            Value=GetAtt(nestedStack, "Outputs." + k),
        ))
