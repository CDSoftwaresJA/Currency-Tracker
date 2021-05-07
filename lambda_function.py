import urllib3
import boto3
from botocore.exceptions import ClientError
import json
import uuid
from decimal import Decimal

def lambda_handler(event, context):
    if (event["task"]==1):
        subscribe(event["email"],event["from"],event["to"])
    if (event["task"]==2):
        compare()
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            "body":"Comparison successfully completed"
        }
        
    if (event["task"]==3):
        daily()
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            "body":"Daily Update successfully completed"
        } 
    
    return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json',   
            "Access-Control-Allow-Origin" : "*", 
            "Access-Control-Allow-Credentials" : True
            },
            "body":"Subscription successfully completed"
        }
    


def subscribe(EMAIL,FROM,TO):
    http = urllib3.PoolManager()
    url = 'http://api.exchangeratesapi.io/v1/latest?access_key=85d30cf5aaa9e89025dc47df626e8d64&format=1'
    resp = http.request('GET', url)
    resp_json=json.loads(resp.data.decode('utf8'))
    print(f'{FROM}: {resp_json["rates"][FROM]}')
    print(f'{TO}: {resp_json["rates"][TO]}')
    rate = resp_json["rates"][TO]/resp_json["rates"][FROM]
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('users')
    user_id = str(uuid.uuid1())
    response = table.put_item(
      Item={
            'id': user_id,
            'email': EMAIL,
        }
    )
    
    table = dynamodb.Table('rate')
    response = table.put_item(
      Item={
            'id': str(uuid.uuid1()),
            'from': FROM,
            'to' : TO,
            'userId': user_id,
            'value' : Decimal(str(rate)),
        }
    )
    sendEmail(EMAIL,FROM,TO,1,rate)
    
    
def daily():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('rate')
    http = urllib3.PoolManager()
    url = 'http://api.exchangeratesapi.io/v1/latest?access_key=85d30cf5aaa9e89025dc47df626e8d64&format=1'
    resp = http.request('GET', url)
    resp_json=json.loads(resp.data.decode('utf8'))
    
    rates = table.scan()["Items"]
    for x in rates:
        rate = resp_json["rates"][x["to"]]/resp_json["rates"][x["from"]]
        table = dynamodb.Table('users')
        response = table.get_item(Key={'id': x["userId"]})
        print(response)
        sendEmail(response['Item']["email"],x["from"],x["to"],1,rate)

def compare():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('rate')
    http = urllib3.PoolManager()
    url = 'http://api.exchangeratesapi.io/v1/latest?access_key=85d30cf5aaa9e89025dc47df626e8d64&format=1'
    resp = http.request('GET', url)
    resp_json=json.loads(resp.data.decode('utf8'))
    
    rates = table.scan()["Items"]
    for x in rates:
        print(x["value"])
        rate = resp_json["rates"][x["to"]]/resp_json["rates"][x["from"]]
        if (int(x["value"])!=int(rate)):
            print(f"Current Rate {rate} , Previous Rate {x['value']} ")
            table = dynamodb.Table('users')
            response = table.get_item(Key={'id': x["userId"]})
            print(response)
            sendEmail(response['Item']["email"],x["from"],x["to"],1,rate)
            # Save this new value to the database

def sendEmail(RECIPIENT,FROM,TO,FROM_VAL,TO_VAL):
    SENDER = "Khylia Clarke <khyliaclarke3@gmail.com>"
    AWS_REGION = "us-east-2"
    SUBJECT = "Currency Tracker Notification"
    BODY_TEXT = ("USD to JMD = 1 to 151"
                )
    BODY_HTML = f"""
    <html>
    <head></head>
    <body>
      <h1>{FROM} to {TO}</h1>
      <p>{FROM_VAL} to {TO_VAL}</p>
    </body>
    </html>
    """            
    CHARSET = "UTF-8"
    client = boto3.client('ses',region_name=AWS_REGION)
    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
    
