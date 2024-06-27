import sys
from azure.identity import DefaultAzureCredential
import csv
import json
import requests

workspace_id = "YOUR_WORKSPACE_ID"
workspaceName = "personal-workspace"
resourceGroupName = "test_infrastructure"
subscriptionId = "f70efef4-6505-4727-acd8-9d0b3bc0b80e"

lia_supported_builtin_table = ['ADAssessmentRecommendation','ADSecurityAssessmentRecommendation','Anomalies','ASimAuditEventLogs','ASimAuthenticationEventLogs','ASimDhcpEventLogs','ASimDnsActivityLogs','ASimDnsAuditLogs','ASimFileEventLogs','ASimNetworkSessionLogs','ASimProcessEventLogs','ASimRegistryEventLogs','ASimUserManagementActivityLogs','ASimWebSessionLogs','AWSCloudTrail','AWSCloudWatch','AWSGuardDuty','AWSVPCFlow','AzureAssessmentRecommendation','CommonSecurityLog','DeviceTvmSecureConfigurationAssessmentKB','DeviceTvmSoftwareVulnerabilitiesKB','ExchangeAssessmentRecommendation','ExchangeOnlineAssessmentRecommendation','GCPAuditLogs','GoogleCloudSCC','SCCMAssessmentRecommendation','SCOMAssessmentRecommendation','SecurityEvent','SfBAssessmentRecommendation','SharePointOnlineAssessmentRecommendation','SQLAssessmentRecommendation','StorageInsightsAccountPropertiesDaily','StorageInsightsDailyMetrics','StorageInsightsHourlyMetrics','StorageInsightsMonthlyMetrics','StorageInsightsWeeklyMetrics','Syslog','UCClient','UCClientReadinessStatus','UCClientUpdateStatus','UCDeviceAlert','UCDOAggregatedStatus','UCServiceUpdateStatus','UCUpdateAlert','WindowsEvent','WindowsServerAssessmentRecommendation']
reserved_columns = ["_ResourceId", "id", "_SubscriptionId", "TenantId", "Type", "UniqueId", "Title","_ItemId"]
def read_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    print(f"Content of {file_path}:\n{content}")

def convert_schema_csv_to_json(csv_file):
    data = []
    with open(csv_file, 'r',encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['ColumnName'] in reserved_columns:
                continue
            else:
                data.append({        
                'name': row['ColumnName'],
                'type': row['ColumnType'],
                })       
    return data

def convert_data_csv_to_json(csv_file):
    data = []
    with open(csv_file, 'r',encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            table_name=row['Type']
            data.append(row)       
    return data , table_name

def check_for_custom_table(table_name):
    if table_name in lia_supported_builtin_table:
        log_ingestion_supported=True
        table_type="builtin"
    if table_name not in lia_supported_builtin_table:
        if table_name.endswith('_CL') or table_name.endswith('_cl'):
            log_ingestion_supported=True
            table_type="custom_log"           
        else:
            log_ingestion_supported=False
            table_type="unknown"
    return log_ingestion_supported,table_type

def create_table(schema,table):
     request_object = {
    "properties": {
        "schema": {
        "name": table,
        "columns": json.loads(schema)
        },
        "retentionInDays": 30,
        "totalRetentionInDays": 30
    }
    }
     method="PUT"
     url=f"https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.OperationalInsights/workspaces/{workspaceName}/tables/{table}?api-version=2022-10-01"
     return request_object , url , method

def get_access_token():
    credential = DefaultAzureCredential()
    token = credential.get_token('https://management.azure.com/.default')
    return token.token   

def hit_api(url,request,method):
    access_token = get_access_token()
    headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
    }
    response = requests.request(method, url, headers=headers, json=request)
    print(response.json())
    print(response.status_code)


if __name__ == "__main__":
    file_path = sys.argv[1]
    #file_path = "samplelogs/CarbonBlackAuditLogs1_CL_Schema.csv"
    if "Schema" in file_path:
        print(f"Schema file found at {file_path}")
        schema_result = convert_schema_csv_to_json(file_path)
        table_name=file_path.split("/")[-1].split(".")[0].removesuffix("_Schema")

    elif "logs" in file_path:
        #data_result,table_name = convert_data_csv_to_json('file_path')
        pass
    else:
        #print("Provided file path does not contain schema or logs. Exiting...")
        #sys.exit(1)
        pass   

    log_ingestion_supported,table_type=check_for_custom_table(table_name)
    print(f"Log ingestion supported: {log_ingestion_supported}\n Table type: {table_type}")

    if log_ingestion_supported == True and table_type =="custom_log":
        # create DCR and table json.dumps(schema_result, indent=4)
        request_body, url_to_call , method_to_use = create_table(json.dumps(schema_result, indent=4),table_name)
        print("*****Printing request body*******\n")
        print(json.dumps(request_body, indent=4))
        hit_api(url_to_call,request_body,method_to_use)
