import json
import boto3
import random
from boto3.dynamodb.conditions import Key
import requests
from requests_aws4auth import AWS4Auth
from datetime import datetime

# get credentials to authenticate Elastic search
credentials = boto3.Session().get_credentials()
authent = AWS4Auth(accessKey, secretAccessKey, 'us-east-1', 'es')

# connect to the dynamoDB table
dynamodb = boto3.resource(service_name='dynamodb',
                          aws_access_key_id=accessKey,
                          aws_secret_access_key=secretAccessKey,
                          region_name="us-east-1",
                         )
yelpTable = dynamodb.Table('yelp-restaurants')

dynamodb_state = boto3.resource(service_name='dynamodb', region_name="us-east-1")
stateTable = dynamodb_state.Table('StateOfUserSuggestions')

# Context Handler
def lambda_handler(event, context):
    
    sqs_queue_processing()

# SQS Queue Handling
def sqs_queue_processing():
    
    # Client to connect to SQS
    client = boto3.client('sqs')

    # Get a list of queue URLs
    queues = client.list_queues(QueueNamePrefix='DiningSuggestionsQueue')
    queue_url = queues['QueueUrls'][0]

    # Queue Response
    response = client.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'All'
        ],
        MaxNumberOfMessages=10,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=30,
        WaitTimeSeconds=0
    )
    print(response, "Queue Response")

    if response['Messages'] and len(response['Messages']) > 0:
        for message in response['Messages']:
            user_input = json.loads(message['Body'])
            cuisine = user_input['cuisine']
            email = user_input['email']
            phone = user_input['phone']

            # Open Search Query
            url = 'https://search-restaurants-tnmgae7arsgfy6sqvzp5yfar4i.us-east-1.es.amazonaws.com/restaurants/_search?q=cuisine:' + cuisine
            elastic_search_response = requests.get(url, auth = authent, headers={"Content-Type": "application/json"}).json()
            number_of_hits = elastic_search_response['_shards']["total"]
            
            # Getting a random number of restaurants to show
            if(number_of_hits > 3):
                restaurantIds = random.sample(range(0, number_of_hits - 1), 3)
            else:
                restaurantIds = random.sample(range(0, number_of_hits - 1), 1)
                
            output, cache = get_dining_suggestions(user_input, restaurantIds, cuisine)

            # Sending the suggestions via Email using SES
            send_email('sm9124@nyu.edu', [email], str(output))
            
            # store the suggestions for next time
            table2response = stateTable.update_item(Key={'identity': '1'}, UpdateExpression="set isFirstTime=:r, suggestions=:p",ExpressionAttributeValues={':r': True,':p': cache},ReturnValues="UPDATED_NEW")

            # Delete the Message from SQS
            client.delete_message(QueueUrl=queue_url, ReceiptHandle=message['ReceiptHandle'])
    else:
        print('Empty Queue')

# Dining Suggestions
def get_dining_suggestions(user_input, random_restaurantIds, cuisine):
    
    restaurantIds = []
    dynamoDB_Responses = []
    for random_id in random_restaurantIds:
        
        # Open Search Query
        url2 = 'https://search-restaurants-tnmgae7arsgfy6sqvzp5yfar4i.us-east-1.es.amazonaws.com/restaurants/_search?from=' + str(random_id) + '&&size=1&&q=cuisine:' + cuisine
        elastic_search_response = requests.get(url2, auth = authent, headers={"Content-Type": "application/json"}).json()
        restaurantIds.append(elastic_search_response['hits']['hits'][0]['_source']['Business ID'])
    
    for rIds in restaurantIds:
        # Get Details from DynamoDb using the above extracted Restaurant Ids
        dynamoDB_Responses.append(yelpTable.query(KeyConditionExpression=Key('Business ID').eq(rIds)))
    
    output = assemble_response(user_input, dynamoDB_Responses)
    return output
    
# Assemble Response
def assemble_response(user_input, responses):
    diningSuggestions=''
    
    cuisine = user_input['cuisine']
    numberOfPeople = user_input['numberOfPeople']
    time = user_input['time']
    date = user_input['date']
    count = 1
    
    for index, items in enumerate(responses):
        if items['Items']:
            data = items['Items'][0]
        else:
            continue
        restaurant_name = data['Name']
        restaurant_address = data['Address']
        suggestion = '\n{}. {}, located at {}. '.format(count, restaurant_name, restaurant_address)
        count += 1
        diningSuggestions += suggestion
    
    # Response
    reply = 'Hey there! Here are the {} restaurant suggestions for {} people, on {} at {}: '.format(cuisine, numberOfPeople, date, time) + diningSuggestions + '\nHope you enjoy your meal!'
    return reply, diningSuggestions

# Sending an Email to the User
def send_email(fromEmailAddress, toEmailAddress, message):
    
    ses_client = boto3.client("ses", region_name="us-east-1")
    CHARSET = "UTF-8"

    response = ses_client.send_email(
        Destination={
            "ToAddresses": toEmailAddress,
        },
        Message={
            "Body": {
                "Text": {
                    "Charset": CHARSET,
                    "Data": message,
                }
            },
            "Subject": {
                "Charset": CHARSET,
                "Data": "Here are your restaurant recommendations brought to you by your Dining Concierge",
            },
        },
        Source=fromEmailAddress,
    )
    print(response)
