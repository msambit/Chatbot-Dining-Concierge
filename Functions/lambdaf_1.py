import json
import logging
import boto3
import math
import dateutil.parser
from boto3.dynamodb.conditions import Key
import datetime
import time
import os
import re

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# connect to the dynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('StateOfUserSuggestions')


# Get all the slots of the current Intent
def get_slots(intent_request):
    return intent_request['currentIntent']['slots']
    

# Context handler
def lambda_handler(event, context):
    
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return handleServices(event)
    
# Handle Services
def handleServices(event):

    logger.debug('Service userId={}, intentName={}'.format(event['userId'], event['currentIntent']['name']))
    
    intent_type = event['currentIntent']['name']

    # Handle the Bot's Services
    if (intent_type == 'GreetingIntent'):
        return handle_greeting_intent(event)
    elif(intent_type == 'DiningSuggestionsIntent'):
        return handle_dining_suggestions_intent(event)
    elif(intent_type == 'ThankYouIntent'):
        return handle_thankyou_intent(event)

    raise Exception('Intent - ' + intent_type + ' not implemented yet')

# Greeting Intent
def handle_greeting_intent(event):
    
    response = table.query(KeyConditionExpression=Key('identity').eq('1'))
    data = response['Items'][0]
    suggestions = data['suggestions']
    status = data['isFirstTime']

    if not status:
        return {
            'dialogAction': {
                "type": "ElicitIntent",
                'message': {
                    'contentType': 'PlainText',
                    'content': 'Hi, how can I help?'}
            }
        }
    else:
        return {
            'dialogAction': {
                "type": "ElicitIntent",
                'message': {
                    'contentType': 'PlainText',
                    'content': 'Welcome back! Here are some suggestions from your previous time here! \n' + suggestions}
            }
        }

# Dining Suggestions Intent
def handle_dining_suggestions_intent(event):
    
    invocation_source = event['invocationSource']

    slots = get_slots(event)
    cuisine = slots["Cuisines"]
    number_of_people = slots["NumberOfPeople"]
    date = slots["Date"]
    time = slots["DiningTime"]
    email = slots["Email"]
    location = slots["Location"]
    phone = slots["Phone"]

    if invocation_source == 'DialogCodeHook':
        
        validation_message = request_validation(
            date, time, email, location, phone, cuisine, number_of_people)

        if validation_message['isValid'] == False:
            slots[validation_message['violatedSlot']] = None
            return elicit_slot(event['sessionAttributes'],
                               event['currentIntent']['name'],
                               slots,
                               validation_message['violatedSlot'],
                               validation_message['message'])

        if event['sessionAttributes'] is not None:
            output_session_attributes = event['sessionAttributes']
        else:
            output_session_attributes = {}

        return delegate(output_session_attributes, get_slots(event))

    queue_message = {"cuisine": cuisine, "email": email, "location": location, "numberOfPeople": number_of_people, "date": date, "time": time, "phone": phone}
    
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName='DiningSuggestionsQueue')
    response = queue.send_message(MessageBody=json.dumps(queue_message))

    return close(event['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Great! You will receive your suggestions over Email shortly.'})

# Thank You Intent
def handle_thankyou_intent(event):
    
    return {
        'dialogAction': {
            "type": "ElicitIntent",
            'message': {
                'contentType': 'PlainText',
                'content': 'Happy to Help!'}
        }
    }

# Request Validation
def request_validation(date, time, email, location, phone, cuisine, number_of_people):

    # Cuisine List
    cuisines = ['indian', 'thai', 'turkish', 'japanese', 'chinese', 'italian', 'french', 'vietnamese', 'mexican']
    
    # Location
    locations = ['new york', 'ny']

    # Check if User specified cuisine in our list of cuisines
    if cuisine is not None and cuisine.lower() not in cuisines:
        return message_validation_response(False,
                                       'Cuisines',
                                       ' ' + cuisine + ' is not in our list of cuisines, can you please try another?')

    # Number of People should be in the range [1-10]
    if number_of_people is not None:
        number_of_people = int(number_of_people)
        if number_of_people < 0:
            return message_validation_response(False,
                                           'NumberOfPeople',
                                           'You need to have a minimum of 1 to make a reservation, please try again.')
        elif number_of_people > 10:
            return message_validation_response(False,
                                           'NumberOfPeople',
                                           'You are allowed to have a maximum of 10 people to make a reservation, please try again.')

    # Date validation
    if date is not None:
        if (is_valid_date(date) == False):
            return message_validation_response(False,
                                           'Date',
                                           'The input seems invalid, what date would you like to go dining?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() <= datetime.date.today():
            return message_validation_response(True, 'Date', 'Awesome, you can good to go dining on {}.'.format(date))

    # Time validation
    if time is not None:
        if len(time) != 5:
            # Time invalid
            return message_validation_response(False, 'Time', 'Not a valid input for time, please try again.')

        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Time invalid
            return message_validation_response(False, 'Time', 'Not a valid input for time, please try again.')

        if hour < 10 or hour > 16:
            # Outside of business hours
            return message_validation_response(False, 'Time', 'Business hours are from 10am to 4pm, please specify accordingly.')

    # Location Validation
    if location is not None:
        if location is not None and location.lower() not in locations:
            return message_validation_response(False, 'Location', 'This city is currently not in our range, please try again.')

    # Email validation
    if email is not None:
        if (is_valid_email(email) == False):
            return message_validation_response(False,
                                           'Email',
                                           'Not a valid input for email, please try again.')
                                           
    # Phone validation
    if phone is not None:
        if len(phone) != 10:
            return message_validation_response(False,
                                           'Phone',
                                           'Not a valid input for phone, please try again.')

    return message_validation_response(True, None, None)
    
# Message validation response
def message_validation_response(is_message_valid, violated_slot, message_content):
    # Case: If message content is not there
    if message_content is None:
        return {
            "isValid": is_message_valid,
            "violatedSlot": violated_slot,
        }

    # Case: Content present and responded with the violated slot and the content
    return { 
        'isValid': is_message_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }
    
# --- Helper Functions --- #

# Converting int to float
def parse_int(num):
    try:
        return int(num)
    except ValueError:
        return float('nan')

# Date validation
def is_valid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

# Email Validation
def is_valid_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if(re.fullmatch(regex, email)):
        return True
    else:
        return False
        
# Eliciting a slot
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

# Response function
def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response

# Delegating slots
def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }