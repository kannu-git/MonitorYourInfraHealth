from __future__ import print_function
import pickle
from googleapiclient.discovery import build
import json
import base64
import hashlib
import hmac
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import azure.functions as func
import logging
import os
import time
import re
from .state_manager import StateManager
from .state_manager import AzureStorageQueueHelper
from datetime import datetime, timedelta


customer_id = os.environ['WorkspaceID']
fetchDelay = os.getenv('FetchDelay',10)
chunksize = 9999
calendarFetchDelay = os.getenv('CalendarFetchDelay',6)
chatFetchDelay = os.getenv('ChatFetchDelay',1)
userAccountsFetchDelay = os.getenv('UserAccountsFetchDelay',3)
loginFetchDelay = os.getenv('LoginFetchDelay',6)
shared_key = os.environ['WorkspaceKey']
connection_string = os.environ['AzureWebJobsStorage']
logAnalyticsUri = os.environ.get('logAnalyticsUri')
max_time_window_per_api_call_mins = os.getenv('max_time_window_per_api_call',5)
'''
customer_id = "dac5fbbc-f2c9-4589-8fe5-abe35946b964"
fetchDelay = 10
chunksize = 9999
calendarFetchDelay = 6
chatFetchDelay = 1
userAccountsFetchDelay = 3
loginFetchDelay = 6
shared_key = "GR3mgHlxiKY3y1HvMF9GInHvd7v9nKBTeReW7GGv+eT7jUkuMMlslOLwQx7GleUA2t/4s2JWkd3h8jRt8Zp8LQ=="
pickle_str = "gASVvgMAAAAAAACMGWdvb2dsZS5vYXV0aDIuY3JlZGVudGlhbHOUjAtDcmVkZW50aWFsc5STlCmBlH2UKIwFdG9rZW6UjNp5YTI5LmEwQWZCX2J5Q2dxS09mMGJacDllVngtbFJhbFp3cnBfMU91SUdHVzRzRkI2MDRtMWlnZ0xScTZDNzBwUzhlS0NVRGZWZHhqbjZKMmRHSG5ZcFpLVUVnTzJPRldwR1J5MERTS0lWOVJxTTZPMnVXZmNqN29lTFdWWm9OSmxkaUhRX1o1Szh6NlVfdjY2U3NRZVdhcUtyb1NibmhhX240S2FnVFZCMklhQ2dZS0FiTVNBUkFTRlFIR1gyTWlXM2lGSkN4ZFpSYktWNGloMHdHa3BnMDE3MZSMBmV4cGlyeZSMCGRhdGV0aW1llIwIZGF0ZXRpbWWUk5RDCgfnDAMUCzkFatyUhZRSlIwRX3F1b3RhX3Byb2plY3RfaWSUTowPX3RydXN0X2JvdW5kYXJ5lE6MEF91bml2ZXJzZV9kb21haW6UjA5nb29nbGVhcGlzLmNvbZSMB19zY29wZXOUXZSMPGh0dHBzOi8vd3d3Lmdvb2dsZWFwaXMuY29tL2F1dGgvYWRtaW4ucmVwb3J0cy5hdWRpdC5yZWFkb25seZRhjA9fZGVmYXVsdF9zY29wZXOUTowOX3JlZnJlc2hfdG9rZW6UjGcxLy8wNlpLVXFmaFk0S0puQ2dZSUFSQUFHQVlTTndGLUw5SXJ6d2s0QnJ6MlJaS2FLZ1V0TEg4eW5FRVJyM29vUkRNM2J1UFBWUGpIZGVYbGtuM01BNVpxdm9iR3c5Y1ozWUVvTUJRlIwJX2lkX3Rva2VulE6MD19ncmFudGVkX3Njb3Blc5RdlIw8aHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vYXV0aC9hZG1pbi5yZXBvcnRzLmF1ZGl0LnJlYWRvbmx5lGGMCl90b2tlbl91cmmUjCNodHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbpSMCl9jbGllbnRfaWSUjEg5NjcxMzg3NTAzOTUtZXZhczZqb3BudDlxY2V2aHEza211cm9jdTRnZTNpZDEuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb22UjA5fY2xpZW50X3NlY3JldJSMI0dPQ1NQWC1UaHVpUUMtOUxQZG1mUTAzWnJjcU1ybWkwSFhplIwLX3JhcHRfdG9rZW6UTowWX2VuYWJsZV9yZWF1dGhfcmVmcmVzaJSJdWIu"
pickle_string = base64.b64decode(pickle_str)
connection_string = "DefaultEndpointsProtocol=https;AccountName=gworkspacepoidok7eik2bg;AccountKey=2CLGKVW8Peq+VGBSwBaKwiKyvDfbNd7ulPMAf1taa7+lH7Bxm8KX/qJ5EA/OGrC5Kf/Eub81eq9d+AStpszESA==;EndpointSuffix=core.windows.net"
logAnalyticsUri = "https://dac5fbbc-f2c9-4589-8fe5-abe35946b964.ods.opinsights.azure.com"
'''
MAX_QUEUE_MESSAGES_MAIN_QUEUE = 1000
MAX_SCRIPT_EXEC_TIME_MINUTES = 3
TIME_WINDOW_To_POLL_API = 60 * int(max_time_window_per_api_call_mins)    # in seconds
SCOPES = ['https://www.googleapis.com/auth/admin.reports.audit.readonly']
activities = [
            "user_accounts",
            "access_transparency", 
            "admin",
            "calendar",
            "chat",
            "drive",
            "gcp",
            "gplus",
            "groups",
            "groups_enterprise",
            "jamboard", 
            "login", 
            "meet", 
            "mobile", 
            "rules", 
            "saml", 
            "token", 
            "context_aware_access", 
            "chrome", 
            "data_studio"
            ]

# Remove excluded activities
excluded_activities = os.environ.get('ExcludedActivities')
if excluded_activities:
    excluded_activities = excluded_activities.replace(" ", "").split(",")
    activities = [activ for activ in activities if activ not in excluded_activities]


if ((logAnalyticsUri in (None, '') or str(logAnalyticsUri).isspace())):
    logAnalyticsUri = 'https://' + customer_id + '.ods.opinsights.azure.com'
pattern = r'https:\/\/([\w\-]+)\.ods\.opinsights\.azure.([a-zA-Z\.]+)$'
match = re.match(pattern,str(logAnalyticsUri))
if(not match):
    raise Exception("Google Workspace Reports: Invalid Log Analytics Uri.")



def GetEndTime(logType):
    end_time = datetime.utcnow().replace(second=0, microsecond=0)
    if logType == "calendar":
        end_time = (end_time - timedelta(hours=int(calendarFetchDelay)))
        logging.info("End time for activity {} after fetch delay {} hour(s) applied - {}".format(logType,int(calendarFetchDelay),end_time))
    if logType == "chat":
        end_time = (end_time - timedelta(days=int(chatFetchDelay)))
        logging.info("End time for activity {} after fetch delay {} day(s) applied - {}".format(logType,int(chatFetchDelay),end_time))
    if logType == "user_accounts":
        end_time = (end_time - timedelta(hours=int(userAccountsFetchDelay)))
        logging.info("End time for activity {} after fetch delay {} hour(s) applied - {}".format(logType,int(userAccountsFetchDelay),end_time))
    if logType == "login":
        end_time = (end_time - timedelta(hours=int(loginFetchDelay)))
        logging.info("End time for activity {} after fetch delay {} hour(s) applied - {}".format(logType,int(loginFetchDelay),end_time))
    else:
        end_time = (end_time - timedelta(minutes=int(fetchDelay)))
        logging.info("End time for activity {} after default fetch delay {} minute(s) applied - {}".format(logType,int(fetchDelay),end_time))
    return end_time

def isBlank (myString):
    return not (myString and myString.strip())

def isNotBlank (myString):
    return bool(myString and myString.strip())

def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError as e:
        return False
    return True

def is_valid_datetime(input):
    try:
        datetime.strptime(input, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return False
    return True

# Function to convert string to datetime
def convertToDatetime(date_time,format):
    #format = '%b %d %Y %I:%M%p'  # The format
    datetime_str = datetime.strptime(date_time, format) 
    return datetime_str

def GetDates(logType):
    end_time = GetEndTime(logType)
    state = StateManager(connection_string=connection_string)
    past_time = state.get()
    activity_list = {}
    if past_time is not None and len(past_time) > 0:
        if is_json(past_time):
            activity_list = past_time
        # Check if state file has non-date format. If yes, then set start_time to past_time
        else:
            try:
                newtime = datetime.strptime(past_time[:-1] + '.000Z', "%Y-%m-%dT%H:%M:%S.%fZ")
                newtime = newtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                newtime = newtime[:-4] + 'Z'
                for activity in activities:
                    activity_list[activity] = newtime
                activity_list = json.dumps(activity_list)
            except Exception as err:
                logging.info("Error while converting state. Its neither a json nor a valid date format {}".format(err))
                logging.info("Setting start time to get events for last 5 minutes.")
                past_time = (end_time - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                for activity in activities:
                    activity_list[activity] = past_time[:-4] + 'Z'
                activity_list = json.dumps(activity_list)
    else:
        logging.info("There is no last time point, trying to get events for last 5 minutes.")
        past_time = (end_time - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        for activity in activities:
            activity_list[activity] = past_time[:-4] + 'Z'
        activity_list = json.dumps(activity_list)
    end_time = end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    end_time = end_time[:-4] + 'Z'
    return json.loads(activity_list) if (isBlank(logType)) else (json.loads(activity_list)[logType],end_time)

def check_if_script_runs_too_long(script_start_time):
    now = int(time.time())
    duration = now - script_start_time
    max_duration = int(MAX_SCRIPT_EXEC_TIME_MINUTES * 60 * 0.9)
    return duration > max_duration            

def format_message_for_queue_and_add(start_time, end_time, activity, mainQueueHelper):
    queue_body = {}
    queue_body["start_time"] = start_time
    queue_body["end_time"] = end_time
    queue_body["activity"] = activity
    mainQueueHelper.send_to_queue(queue_body,True)
    logging.info("Added to queue: {}".format(queue_body))
    

def main(mytimer: func.TimerRequest):
    logging.getLogger().setLevel(logging.INFO)
    if mytimer.past_due:
        logging.info('The timer is past due!')
    script_start_time = int(time.time())
    logging.info('Starting GWorkspaceReport-TimeTrigger program at {}'.format(time.ctime(int(time.time()))) )
    mainQueueHelper = AzureStorageQueueHelper(connectionString=connection_string, queueName="gworkspace-queue-items")
    logging.info("Check if we already have enough backlog to process in main queue. Maxmum set is MAX_QUEUE_MESSAGES_MAIN_QUEUE: {} ".format(MAX_QUEUE_MESSAGES_MAIN_QUEUE))
    mainQueueCount = mainQueueHelper.get_queue_current_count()
    logging.info("Main queue size is {}".format(mainQueueCount))
    while (mainQueueCount ) >= MAX_QUEUE_MESSAGES_MAIN_QUEUE:
        time.sleep(15)
        if check_if_script_runs_too_long(script_start_time):
            logging.info("We already have enough messages to process. Not clearing any backlog or reading a new SQS message in this iteration.")
            return
        mainQueueCount = mainQueueHelper.get_queue_current_count()
    
    latest_timestamp = ""
    postactivity_list = GetDates("")
    for line in activities:
        if check_if_script_runs_too_long(script_start_time):
            logging.info("Some more backlog to process, but ending processing for new data for this iteration, remaining will be processed in next iteration")
            return
        try:
            start_time,end_time = GetDates(line)
            if start_time is None:
                logging.info("There is no last time point, trying to get events for last one day.")
                end_time = datetime.strptime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ")
                start_time = (end_time - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                end_time = end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            logging.info("Start time: {} and End time: {} for activity {}".format(start_time,end_time,line))
            
            state = StateManager(connection_string)
            
            # check if difference between start_time and end_time is more than TIME_WINDOW_To_POLL_API, if yes, then split time window to make each call to TIME_WINDOW_To_POLL_API
            while (convertToDatetime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ") - convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ")).total_seconds() > TIME_WINDOW_To_POLL_API:
                if check_if_script_runs_too_long(script_start_time):
                    logging.info("Some more backlog to process, but ending processing for new data for this iteration, remaining will be processed in next iteration")
                    return
                loop_end_time = end_time
                # check if start_time is less than end_time. If yes, then process sending to queue
                if not(convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ") >= convertToDatetime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ")):
                    end_time = (convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(seconds=TIME_WINDOW_To_POLL_API)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    end_time = end_time[:-4] + 'Z' 
                    format_message_for_queue_and_add(start_time, end_time, line, mainQueueHelper)
                    #update state file
                    latest_timestamp = end_time
                    postactivity_list[line] = latest_timestamp
                    logging.info("Updating state file with latest timestamp : {} for activity {}".format(latest_timestamp, line))
                    state.post(str(json.dumps(postactivity_list)))
                    start_time = end_time
                    end_time = loop_end_time

            if (convertToDatetime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ") - convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ")).total_seconds() <= TIME_WINDOW_To_POLL_API and not(convertToDatetime(start_time,"%Y-%m-%dT%H:%M:%S.%fZ") >= convertToDatetime(end_time,"%Y-%m-%dT%H:%M:%S.%fZ")):
                format_message_for_queue_and_add(start_time, end_time, line, mainQueueHelper)
                #update state file
                latest_timestamp = end_time
                postactivity_list[line] = latest_timestamp
                logging.info("Updating state file with latest timestamp : {} for activity {}".format(latest_timestamp, line))
                state.post(str(json.dumps(postactivity_list)))

        except Exception as err:
            logging.error("Something wrong. Exception error text: {}".format(err))
            logging.error( "Error: Google Workspace Reports data connector execution failed with an internal server error.")
            raise
    logging.info('Ending GWorkspaceReport-TimeTrigger program at {}'.format(time.ctime(int(time.time()))) )

'''
if __name__ == '__main__':
    main()

'''
