from datetime import datetime
import json
import os
import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr

#GET /User/DisplayData/FriendsToAdd?userId={someUserId}&searchText={searchText}
#Start with UserId and searchText
#Find Existing Friendships (senderUserId = UserId or receiverUserId = UserId AND confirmed = true)
#Find Pending Friendships (senderUserId = UserId or receiverUserId = UserId AND confirmed = false)
    #Sort Pending Friendships into (1) SentFriendRequests and (2) ReceivedFriendRequests
#Find valid Users (match search text, not current user, not current friend, not ReceivedFriendRequest)
#Add profilePictureUrl
#Add sentRequest boolean fact

USER_TABLE = os.environ.get("API_DEMIAPP_USERTABLE_NAME")
FRIENDSHIP_TABLE = os.environ.get("API_DEMIAPP_FRIENDSHIPTABLE_NAME")
S3_BUCKET_NAME = os.environ.get("STORAGE_S3DEMIUSERPROFILEPICTURES_BUCKETNAME")
REQUEST_HTTP_METHOD_FIELD = "httpMethod"
REQUEST_QS_PARAMS_FIELD = "queryStringParameters"

QS_USER_ID = "userId"
QS_SEARCH_TEXT = "searchText"

# TABLE COLUMNS
FRIENDSHIP_COL_SENT_ID = "senderUserId"
FRIENDSHIP_COL_RECEIVED_ID = "receiverUserId"
FRIENDSHIP_COL_CONFIRMED = "confirmed"

USER_COL_ID = "id"
USER_COL_FIRSTNAME = "firstName"
USER_COL_LASTNAME = "lastName"
USER_COL_USERNAME = "username"

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
user_table = dynamodb.Table(USER_TABLE)
friendship_table = dynamodb.Table(FRIENDSHIP_TABLE)

def handler(event, context):
    logger.info(f'## ENVIRONMENT VARIABLES:\n{os.environ}')
    logger.info(f'## EVENT:\n{event}')

    http_verb = event[REQUEST_HTTP_METHOD_FIELD]

    if http_verb == "GET": 
        try:
            qs_param_dict = event[REQUEST_QS_PARAMS_FIELD]
            if validate_qs_params(qs_param_dict):
                user_id = qs_param_dict[QS_USER_ID]
                search_text = qs_param_dict[QS_SEARCH_TEXT]
                
                current_friendships = find_friendships(user_id)

                confirmed_friendships = list(filter(lambda f: f[FRIENDSHIP_COL_CONFIRMED] == True), current_friendships)
                unconfirmed_friendships = list(filter(lambda f: f[FRIENDSHIP_COL_CONFIRMED] == False), current_friendships)
                
                received_unconfirmed_friendships = list(filter(lambda f: f[FRIENDSHIP_COL_RECEIVED_ID] == user_id), unconfirmed_friendships)
                sent_unconfirmed_friendships = list(filter(lambda f: f[FRIENDSHIP_COL_SENT_ID] == user_id), unconfirmed_friendships)
                
                users_to_display = find_users_to_display(user_id, confirmed_friendships, received_unconfirmed_friendships)
                
                transformed_user_data = transform_friend_user_data(users_to_display, sent_unconfirmed_friendships)

                return make_return_obj(200, [json.dumps(u.toJSON(), default=str) for u in transformed_user_data])
            
            else:
                logger.error(f"Bad QS params")
                return make_return_obj(400, "Error retrieving addable friends")

        except Exception as e:
            logger.exception(repr(e))
            return make_return_obj(500, "Error getting data for friends to add")

    else:
        return make_return_obj(400, "Invalid http request")


def make_return_obj(statusCode, body):
  return {
    'statusCode': statusCode,
    'headers': {
      'Access-Control-Allow-Headers': '*',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    },
    'body': body
  }

def validate_qs_params(qs_param_dict: dict):
    is_valid = True
    try:
        if len(qs_param_dict.keys()) != 2 :
            is_valid=False
        if not (isinstance(qs_param_dict[QS_USER_ID], str) and (len(qs_param_dict[QS_USER_ID]) < 50)):
            is_valid=False
        if not (isinstance(qs_param_dict[QS_SEARCH_TEXT], str) and (len(qs_param_dict[QS_SEARCH_TEXT]) < 50)):
            is_valid=False

    except Exception as e:
        logger.exception(repr(e))

    return is_valid

def find_friendships(user_id: str):

    response = friendship_table.scan(
        FilterExpression=(Attr(FRIENDSHIP_COL_SENT_ID).eq(user_id) | 
                          Attr(FRIENDSHIP_COL_RECEIVED_ID).eq(user_id))
    )
    
    return response["Items"]

def find_users_to_display(user_id: str, confirmed_friendships: list, received_unconfirmed_friendships:list):
    user_ids_to_exclude = []
    
    #can't add yourself as a friend
    user_ids_to_exclude.append(user_id) 

    #can't add friends that are already friends
    user_ids_to_exclude.append(f[FRIENDSHIP_COL_SENT_ID] for f in confirmed_friendships)
    user_ids_to_exclude.append(f[FRIENDSHIP_COL_RECEIVED_ID] for f in confirmed_friendships)

    #can't add friends that have already sent you friend requests
    user_ids_to_exclude.append(f[FRIENDSHIP_COL_SENT_ID] for f in received_unconfirmed_friendships)
    user_ids_to_exclude.append(f[FRIENDSHIP_COL_RECEIVED_ID] for f in received_unconfirmed_friendships)

    #Deduplicate list
    user_ids_to_exclude = list(dict.fromkeys(user_ids_to_exclude))

    response = user_table.scan(
        FilterExpression=(~Attr(USER_COL_ID).is_in(user_ids_to_exclude))
    )

    return response["Items"]

def transform_friend_user_data(users_to_display, sent_unconfirmed_friendships):
    transformed_data = []
    sent_unconfirmed_friendship_ids = list(map(lambda f: f[FRIENDSHIP_COL_RECEIVED_ID], sent_unconfirmed_friendships))

    for user_data in users_to_display:
        profile_picture_url = get_profile_picture_url(user_data[USER_COL_ID])
        request_sent = user_data[USER_COL_ID] in sent_unconfirmed_friendship_ids

        transformed_data.append(
            FriendUserDisplayData(user_data[USER_COL_ID],
                                  user_data[USER_COL_FIRSTNAME],
                                  user_data[USER_COL_LASTNAME],
                                  user_data[USER_COL_USERNAME],
                                  profile_picture_url,
                                  request_sent,
            )
        )

    return transformed_data

def get_profile_picture_url(user_id):
    presigned_url = "noProfilePicture"
    try:
        key = f"public/userProfilePictures/{user_id}/profilePicure.jpeg"
        presigned_url = s3.generate_presigned_url('get_object', 
                                                    Params = 
                                                        {'Bucket': S3_BUCKET_NAME,  
                                                        'Key': key}, 
                                                    ExpiresIn = 3600
                                                    )
    except Exception as e:
        logger.exception(e)
        logger.info(f"No profile picture found for user {user_id}")

    return presigned_url

class FriendUserDisplayData():
    def __init__(self, id: str, firstName: str, lastName: str, username: str, profilePictureUrl: str, sentRequest: bool):
        self.id = id
        self.firstName = firstName
        self.lastName = lastName
        self.username = username
        self.profilePictureUrl = profilePictureUrl
        self.sentRequest = sentRequest
    
    def toJSON(self):
        return {
            USER_COL_ID: self.id,
            USER_COL_FIRSTNAME: self.firstName,
            USER_COL_LASTNAME: self.lastName,
            USER_COL_USERNAME: self.username,
            "profilePictureUrl": self.profilePictureUrl,
            "sentRequest": self.permissionLevel
        }
    