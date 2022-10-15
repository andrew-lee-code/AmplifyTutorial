import json
import os
import pathlib

TABLE_NAME = os.environ.get("API_AMPLIFIEDTODO_TODOTABLE_NAME")

def handler(event, context):
  print("EVENT:")
  print(event)
  print("CONTEXT:")
  print(context)
  print("Hello form labda layer")

  http_verb = event["httpMethod"]

  if http_verb == "POST":
    print("Received and recognized POST request")
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    print("ROOOT DIR")
    print(ROOT_DIR)

    requestBody = json.loads(event["body"])
    print("Working directory:")
    working_dir= pathlib.Path().resolve()
    print(working_dir)
    print("All items")
    all_files = [print(f + "\n") for f in os.listdir(working_dir)]
    print("All items in BUILD")
    all_files = [print(f + "\n") for f in os.listdir(os.path.join(working_dir, "build", "lib"))]
    #updateExpression, expressionValues = APIUtils.get_update_params(requestBody)
    print("Update Expression")
    #print(updateExpression)
    print("Update Attributes")
    #print(expressionValues)
  
  return {
      'statusCode': 200,
      'headers': {
          'Access-Control-Allow-Headers': '*',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
      },
      'body': json.dumps(requestBody)
  }