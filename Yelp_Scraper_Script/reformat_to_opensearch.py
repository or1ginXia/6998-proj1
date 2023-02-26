import csv
import json

csv_file = ['burgers.csv', 'chinese.csv', 'italian.csv', 'japanese.csv', 'mexican.csv', 'salad.csv']
cuisine = ['burgers', 'chinese', 'italian', 'japanese', 'mexican', 'salad']

result_data = []
for i in range(len(csv_file)):
    with open(csv_file[i], 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row = dict(row)
            dict1 = {"index": {"_index": "restaurants", "_id": row['Business ID']}}
            dict1 = json.dumps(dict1)
            result_data.append(dict1)
            dict2 = {"cuisine": cuisine[i], "Business ID": row['Business ID']}
            dict2 = json.dumps(dict2)
            result_data.append(dict2)

with open('opensearch_info.json', 'w') as f:
    for value in result_data:
        f.write(value)
        f.write('\n')