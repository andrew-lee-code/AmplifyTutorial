import json
from operator import ge
import os
import time
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get("API_AMPLIFIEDTODO_TODOTABLE_NAME")

def get_update_params(body):
    """Given a dictionary we generate an update expression and a dict of values
    to update a dynamodb table.

    Params:
        body (dict): Parameters to use for formatting.

    Returns:
        update expression, dict of values.
    """
    update_expression = ["set "]
    update_values = dict()

    for key, val in body.items():
        update_expression.append(f" {key} = :{key},")
        update_values[f":{key}"] = val


    update_expression, update_values = add_metadata(update_expression, update_values)

    return "".join(update_expression)[:-1], update_values

def add_metadata(update_expression, update_values):
    last_updated = int(time.time()) 
    update_expression.append(" updatedAt = :updatedAt,")
    update_values[f":updatedAt"] = datetime.utcfromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
    #update_expression.append(" _lastChangedAt = :lastChangedAt,")
    #update_values[f":lastChangedAt"] = datetime.utcfromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')

    return update_expression, update_values


def handler(event, context):  
  print("EVENT:")
  print(event)
  print("CONTEXT:")
  print(context)

  http_verb = event["httpMethod"]

  if http_verb == "GET":  
    table = dynamodb.Table(TABLE_NAME)
    response = table.query(
        KeyConditionExpression=Key('id').eq('454df42d-5a42-4dac-82e6-9c27e2941769')
    )

    items = response['Items']

    data = {
        "id": items[0]["id"],
        "isComplete": items[0]["isComplete"],
        "name": items[0]["name"],
        "description": items[0]["description"]
    }

    print(json.dumps(data))
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },

        'body': json.dumps(data)
    }
  if http_verb == "POST":
    print("Received and recognized POST request")

    table = dynamodb.Table(TABLE_NAME)
    requestBody = json.loads(event["body"])

    updateExpression, expressionValues = get_update_params(requestBody)
    print("Update Expression")
    print(updateExpression)
    print("Update Attributes")
    print(expressionValues)

    table.update_item(
        Key={
            'id': '454df42d-5a42-4dac-82e6-9c27e2941769'
        },
        UpdateExpression=updateExpression,
        ExpressionAttributeValues=expressionValues
    )

    updated_item_response = table.query(
        KeyConditionExpression=Key('id').eq('454df42d-5a42-4dac-82e6-9c27e2941769')
    )

    updated_item = updated_item_response["Items"]

    data = {
        "id": updated_item[0]["id"],
        "isComplete": updated_item[0]["isComplete"],
        "name": updated_item[0]["name"],
        "description": updated_item[0]["description"]
    }

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },

        'body': json.dumps(data)
    }    

