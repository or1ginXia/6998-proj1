import json
import boto3
import logging
import random
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def query_open_search_by_cuisine(cuisine):
    cred = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(cred.access_key,
                    cred.secret_key ,
                    'us-east-1',
                    'es',
                    session_token=cred.token)
                    
    client = OpenSearch(
        hosts=[{
            'host': 'search-restaurants-eb7mvny6gaqsabongxe2ywfwpe.us-east-1.es.amazonaws.com',
            'port': 443
        }],
        http_auth=aws_auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection)
        
    res = client.search(index='restaurants', body={'size': 1000, 'query': {'multi_match': {'query': cuisine}}})
    # random
    res_random = random.choices(res['hits']['hits'],k = 3)
    results = []
    # for hit in res['hits']['hits']:
    for hit in res_random:
        results.append(hit['_source']['Business ID'])
    logger.info("Quried from OpenSearch: %s", results)
    return results
    
def query_dynamo_by_business_ids(businessIds):
    db = boto3.resource('dynamodb')
    table = db.Table('yelp-restaurants')
    try:
        items = list()
        for bid in businessIds:
            item = table.get_item(Key={'Business ID': bid})['Item']
            items.append(item)
        
        logger.info("Queried from DynamoDB: %s", items)
        return items
    except Exception as e:
        logger.error("Failed to query dynamo db: Business IDs - %s, Error - %s", businessIds, e)
        return None

def poll_from_sqs():
    # client of sqs
    client = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/824654559654/DiningQueue'

    # get data from sqs
    response = client.receive_message(
        QueueUrl=queue_url,
        AttributeNames=['SentTimestamp'],
        MaxNumberOfMessages=1,
        MessageAttributeNames=['All'],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    
    if 'Messages' not in response.keys():
        logger.info("No more message received, stop here")
        return None
    
    # message from sqs
    message = response['Messages'][0]
    logger.info('Received message from SQS: %s', message)
    receipt_handle = message['ReceiptHandle']

    # delete message from queue
    client.delete_message(
        QueueUrl = queue_url,
        ReceiptHandle=receipt_handle
    )
    
    return json.loads(message['Body'])

def format_email_body(restaurants, message):
    # formate the email data
    message_1 = 'Hello! Here are my ' + message['cuisine']
    message_2 = ' restaurant suggestions for ' + str(message['numberOfPeople']) + ' people,'
    message_3 = ' for ' + message['diningDate'] + ' at ' + message['diningTime'] + ': '
    
    message_list = []
    for i in range(len(restaurants)):
        message_4 = str(i+1) + '. ' + restaurants[i]['Name'] + ', '
        message_5 = 'located at ' + restaurants[i]['Address'] + ', '
        message_list.append(message_4 + message_5)
    
    result_message = message_1 + message_2 + message_3
    for value in message_list:
        result_message += value
    result_message += 'enjoy your meal!'
        
    return result_message   

def send_email(emailAddress, body):
    ses_client = boto3.client('ses')
    subject = 'Dining Restaurant Suggestions'
    message = {'Subject':{'Data':subject}, 'Body':{"Html":{"Data": body}}}
    ses_response = ses_client.send_email(Source = emailAddress, 
                    Destination = {"ToAddresses": [emailAddress]}, 
                    Message = message)
    logger.info("Email sent Successfully: target - %s, body - %s", emailAddress, body)

def lambda_handler(event, context):
    while True:
        """
        message = {
            "location": "string",
            "cuisine": "string",
            "diningDate": "string",
            "diningTime": "string",
            "numberOfPeople": number,
            "emailAddress": "string
        }
        """
        message = poll_from_sqs()
        if message is None:
            return "Success"
        
        """
        businessIds = [
            "Business ID: string",
            "Business ID: string",
            ...
        ]
        """
        businessIds = query_open_search_by_cuisine(message['cuisine'].lower())
        if businessIds is None:
            logger.error("query_open_search_by_cuisine failed: businessIds is None")
            
        """
        restaurants = [
            {
                "Business ID": "string",
                "Address": "string",
                "Coordinates": "string",
                "insertedAtTimestamp": "string",
                "Name": "string,
                "Number of Reviews": "string",
                "Rating": "string",
                "Zip Code": "string"
            },
            ...
        ]
        """
        restaurants = query_dynamo_by_business_ids(businessIds)
        if restaurants is None:
            logger.error("query_dynamo_by_business_ids failed: restaurants is None")
        
        body = format_email_body(restaurants, message)
        if body is None:
            logger.error("format_email_body failed: body is None")
        
        try:
            send_email(message['emailAddress'], body)
        except Exception as e:
            logger.error('send_email failed: %s', e)
