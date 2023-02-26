import requests
import pandas as pd

# search businesses
url = 'https://api.yelp.com/v3/businesses/search'
# set api key
key = 'WR-rF4G1zcA06MAUOgQizIvpQHeMfK75Z7XBhABokXUeC5G0OguLQgk4WoIXcCcHvHuFVkZ3eiTkw2uud9LWXBJXQucwdkU3X3ZbKqeZ_59otncs2NHu7MvFsbr5Y3Yx'
# verify with bearer model
headers = {'Authorization': 'Bearer' + ' ' + key}

# set category
category = ['burgers', 'chinese', 'italian', 'japanese', 'mexican', 'salad']
# csv file
csv_file = ['burgers.csv', 'chinese.csv', 'italian.csv', 'japanese.csv', 'mexican.csv', 'salad.csv']


# set search parameter
parameter = {"location": "manhattan", "limit": 50}

offset = 50

id_collection = []
for i in range(len(category)):
    # new category
    parameter['categories'] = category[i]
    parameter['offset'] = 0
    result_data = []
    # first 1000 data
    response = requests.get(url, headers=headers, params=parameter)
    data = response.json()
    # when there is still data
    while 'businesses' in data.keys():
        # store these value
        temp = []
        for detail in data['businesses']:
            # no duplication
            if detail['id'] not in id_collection:
                id_collection.append(detail['id'])
                temp.append(detail)
        # store data
        result_data += temp
        # update offset
        parameter['offset'] += offset
        # new request
        response = requests.get(url, headers=headers, params=parameter)
        data = response.json()


    # get needed data
    result = []
    for info in result_data:
        temp = dict()
        temp['Business ID'] = info["id"]
        temp['Name'] = info["name"]
        temp['Address'] = ", ".join(info['location']['display_address'][0:len(info['location']['display_address']) - 1])
        temp['Coordinates'] = info["coordinates"]
        temp['Number of Reviews'] = info["review_count"]
        temp['Rating'] = info["rating"]
        temp['Zip Code'] = info['location']['zip_code']
        result.append(temp)

    df = pd.DataFrame(result)
    df.to_csv(csv_file[i], index=False)
