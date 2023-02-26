import json
import boto3

# Define the client to interact with Lex
client = boto3.client('lexv2-runtime')

def lambda_handler(event, context):
    # get data from user
    msg_from_user = json.loads(event['body'])['messages'][0]['unstructured']['text']
    
    # default response to user
    default_response = { 
        "messages": [{
            "type": "unstructured",
            "unstructured": {
                "id": "string",
                "text": "I’m still under development. Please come back later.",
                "timestamp": "string"
            }
        }]
    }
    
    # Initiate conversation with Lex
    response = client.recognize_text(
            botId='FHNHX6NZJW',
            botAliasId='SS2MPPEU1X',
            localeId='en_US',
            sessionId='testuser',
            text=msg_from_user)
    
    # get message from lex
    msg_from_lex = response.get('messages', [])
    if msg_from_lex:
        # lex does return message
        
        # set response to user
        default_response['messages'][0]['unstructured']['text'] = msg_from_lex
      
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(default_response)
        }
    else:
        # lex return nothing
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(default_response)
        }