import json
import datetime
import time
import os
import logging
import boto3
import dateutil

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Helpers that build all of the responses ---
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_to_elicit,
            },
            'intent': {
                'name': intent_name,
                'slots': slots
            }
        },
        'messages': [message]
    }

def delegate(session_attributes, slots):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Delegate'
            },
            "intent": {
                "name": "DiningSuggestionsIntent",
                "slots": slots
            }
        }
    }

def close(session_attributes, fulfillment_state, message, slots):
    response = {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Delegate'
            },
            'intent': {
                'name': 'DiningSuggestionsIntent',
                'state': fulfillment_state,
                'slots': slots
            }
        },
        'messages': [message]
    }

    return response

# --- Helper Functions ---
def safe_int(n):
    """
    Safely convert n value to int.
    """
    try:
        return int(n)
    except Exception:
        return n
    
def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except Exception:
        return False
    
def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """
    try:
        return func()
    except Exception as e:
        return None

def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }
    
def validate_dining(slots):
    diningDate = try_ex(lambda: slots['DiningDate']['value']['interpretedValue'])
    diningTime = try_ex(lambda: slots['DiningTime']['value']['interpretedValue'])
    numberOfPeople = safe_int(try_ex(lambda: slots['NumberOfPeople']['value']['interpretedValue']))
    
    if diningDate:
        if not isvalid_date(diningDate):
            return build_validation_result(False, 'DiningDate', 'I did not understand your date input. Can you make it more clear? e.g. today or 2023-02-25')
        if datetime.datetime.strptime(diningDate, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'DiningDate', 'I cannot search info for a past date. Can you try a different date? e.g. today or tomorrow')
    
    if diningTime:
        user_datetime = datetime.datetime.strptime(diningDate + ' ' + diningTime, '%Y-%m-%d %H:%M')
        user_datetime = user_datetime + datetime.timedelta(minutes=2)
        if user_datetime < datetime.datetime.now():
            return build_validation_result(False, 'DiningTime', 'I cannot search info for a past time. Can you try a different time? e.g. now')
    
    if numberOfPeople is not None:
        if (not isinstance(numberOfPeople, int)):
            return build_validation_result(False, 'NumberOfPeople', 'Please enter the actual number of people will come')
        if numberOfPeople <= 0:
            return build_validation_result(False, 'NumberOfPeople', 'Please enter the actual number of people will come')

    return {'isValid': True}

def sendMessagetoSQS(dining):
    sqs = boto3.client('sqs')
    sqs.send_message(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/824654559654/DiningQueue", 
        MessageBody=json.dumps(dining)
    )
    
""" --- Functions that control the bot's behavior --- """
def diningSuggestions(intent_request, invocationSource):
    """
    Performs dialog management and fulfillment for dining suggstion.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    location = try_ex(lambda: intent_request['intent']['slots']['Location']['value']['interpretedValue'])
    cuisine = try_ex(lambda: intent_request['intent']['slots']['Cuisine']['value']['interpretedValue'])
    diningDate = try_ex(lambda: intent_request['intent']['slots']['DiningDate']['value']['interpretedValue'])
    diningTime = try_ex(lambda: intent_request['intent']['slots']['DiningTime']['value']['interpretedValue'])
    numberOfPeople = safe_int(try_ex(lambda: intent_request['intent']['slots']['NumberOfPeople']['value']['interpretedValue']))
    emailAddress = try_ex(lambda: intent_request['intent']['slots']['EmailAddress']['value']['interpretedValue'])
    
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    dining = {
        'location': location,
        'cuisine': cuisine,
        'diningDate': diningDate,
        'diningTime': diningTime,
        'numberOfPeople': numberOfPeople,
        'emailAddress': emailAddress
    }
    logger.info("Done parsing: %s", dining)
    
    if invocationSource == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_dining(intent_request['intent']['slots'])
        if not validation_result['isValid']:
            slots = intent_request['intent']['slots']
            slots[validation_result['violatedSlot']] = None

            logger.error("Slot Validation Failed: viodlatedSlot = %s, message = %s", validation_result['violatedSlot'], validation_result['message'])
            return elicit_slot(
                session_attributes,
                try_ex(lambda: intent_request['intent']['name']),
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )
        
        return delegate(session_attributes, intent_request['intent']['slots'])
        
    sendMessagetoSQS(dining)
    
    logger.info("SUCCESSFULLY DONE")
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Thanks, I have started collection work. An email will be sent to you soon.'
        },
        intent_request['intent']['slots']
    )
    
# --- Intents ---

def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """
    invocationSource = try_ex(lambda: intent_request['invocationSource'])
    intent_request = try_ex(lambda: intent_request['sessionState'])
    intent_name = try_ex(lambda: intent_request['intent']['name'])
    
    logger.info("invocationSource = %s, intent_name = %s", invocationSource, intent_name)
    
    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionsIntent':
        return diningSuggestions(intent_request, invocationSource)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---

def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    
    logger.info('Retrieved event: %s', event)
    return dispatch(event)
