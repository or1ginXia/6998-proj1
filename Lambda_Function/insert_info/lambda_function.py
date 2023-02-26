import json
import boto3
import csv
import datetime


def lambda_handler(event, context):
    csv_file = ['burgers.csv', 'chinese.csv', 'italian.csv', 'japanese.csv', 'mexican.csv', 'salad.csv']
    
    for csv_file_data in csv_file:
        yelp_data = []
        # read the data
        with open(csv_file_data,'r',encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                row = dict(row)
                row['insertedAtTimestamp'] = str(datetime.datetime.now())
                yelp_data.append(dict(row))
        
        insert_data(yelp_data)
    

def insert_data(data_list, db=None, table='yelp-restaurants'):
    if not db:
        db = boto3.resource('dynamodb')
    table = db.Table(table)
    
    # overwrite if the same index is provided
    for data in data_list:
        print(data)
        response = table.put_item(Item=data)
    return response
    
        

