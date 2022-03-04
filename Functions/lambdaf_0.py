import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Context Handler
def lambda_handler(event, context):
    
    print(type(event['body']))
    temp  = json.loads(event['body'])
    
    message = temp["messages"][0]['unstructured']['text']
    client = boto3.client('lex-runtime')
    
    response = client.post_text(
        botAlias='DiningBot_SIT',
        botName='EatWithPleasure',
        userId='AdamEve',
        inputText=message)
    
    return {
        'statusCode': 200,
        'body': json.dumps(response['message']),
        "headers": { 
            "Access-Control-Allow-Origin": "*" 
        }
    }