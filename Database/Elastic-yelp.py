"""
Yelp Fusion API code sample.
This program demonstrates the capability of the Yelp Fusion API
by using the Search API to query for businesses by a search term and location,
and the Business API to query additional information about the top result
from the search query.
Please refer to http://www.yelp.com/developers/v3/documentation for the API
documentation.
This program requires the Python requests library, which you can install via:
`pip install -r requirements.txt`.
Sample usage of the program:
`python sample.py --term="bars" --location="San Francisco, CA"`
"""
from __future__ import print_function

import argparse
import json
import pprint
import requests
import sys
import urllib
import boto3
from decimal import Decimal
from datetime import datetime


# This client code can run on Python 2.x or 3.x.  Your imports can be
# simpler if you only need one of those.
try:
    # For Python 3.0 and later
    from urllib.error import HTTPError
    from urllib.parse import quote
    from urllib.parse import urlencode
except ImportError:
    # Fall back to Python 2's urllib2 and urllib
    from urllib2 import HTTPError
    from urllib import quote
    from urllib import urlencode




# It now uses private keys to authenticate requests (API Key)
# You can find it on
# https://www.yelp.com/developers/v3/manage_app
API_KEY= API_KEY



# API constants, you shouldn't have to change these.
API_HOST = 'https://api.yelp.com'
SEARCH_PATH = '/v3/businesses/search'
BUSINESS_PATH = '/v3/businesses/'  # Business ID will come after slash.


# Defaults for our simple example.
DEFAULT_TERM = 'dinner'
DEFAULT_LOCATION = 'manhattan'
SEARCH_LIMIT = 50


host = host

index = 'restaurants'
type = 'Restaurant'

url = host + '/' + index + '/' + type + '/'
headers = { "Content-Type": "application/json" }


def request(host, path, api_key, url_params=None):
    """Given your API_KEY, send a GET request to the API.
    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        API_KEY (str): Your API Key.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        dict: The JSON response from the request.
    Raises:
        HTTPError: An error occurs from the HTTP request.
    """
    url_params = url_params or {}
    url = '{0}{1}'.format(host, quote(path.encode('utf8')))
    headers = {
        'Authorization': 'Bearer %s' % api_key,
    }

    print(u'Querying {0} ...'.format(url))

    response = requests.request('GET', url, headers=headers, params=url_params)

    return response.json()


def search(api_key, term, location,offset):
    """Query the Search API by a search term and location.
    Args:
        term (str): The search term passed to the API.
        location (str): The search location passed to the API.
    Returns:
        dict: The JSON response from the request.
    """

    url_params = {
        'term': term.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        'limit': SEARCH_LIMIT,
        'offset': offset,
        'radius': 35000
    }
    return request(API_HOST, SEARCH_PATH, api_key, url_params=url_params)


def get_business(api_key, business_id):
    """Query the Business API by a business ID.
    Args:
        business_id (str): The ID of the business to query.
    Returns:
        dict: The JSON response from the request.
    """
    business_path = BUSINESS_PATH + business_id

    return request(API_HOST, business_path, api_key)


def query_api(term, location):
    """Queries the API by the input values from the user.
    Args:
        term (str): The search term to query.
        location (str): The location of the business to query.
    """
    response = search(API_KEY, term, location,50)

    businesses = response.get('businesses')

    if not businesses:
        print(u'No businesses for {0} in {1} found.'.format(term, location))
        return

    business_id = businesses[0]['id']

    print(u'{0} businesses found, querying business info ' \
        'for the top result "{1}" ...'.format(
            len(businesses), business_id))
    response = get_business(API_KEY, business_id)

    print(u'Result for business "{0}" found:'.format(business_id))
    pprint.pprint(response, indent=2)


# Push data to dynamoDB
def push_data(businesses):
    for business in businesses:
        payload = business
        my_es_id = payload["Business ID"]
        print("trying")
        r = requests.put(url+str(my_es_id), json=payload, headers=headers)
        print(r.text)


# # Select required fields for DB
def handle_response(businesses, cuisine):
    documents = []
    for item in businesses:
        restaurant = {
            "Business ID": item["id"],
            "cuisine": cuisine
        }
        documents.append(restaurant)
    return json.loads(json.dumps(documents), parse_float=Decimal)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-q', '--term', dest='term', default=DEFAULT_TERM,
                        type=str, help='Search term (default: %(default)s)')
    parser.add_argument('-l', '--location', dest='location',
                        default=DEFAULT_LOCATION, type=str,
                        help='Search location (default: %(default)s)')

    input_values = parser.parse_args()

    cuisines = ['indian', 'italian', 'chinese', 'French', 'Thai', 'vietnamese','mexican','Burmese', 'Japanese', 'Persian', 'Turkish','American']

    #cuisines = ['Burmese', 'Japanese', 'Persian', 'Turkish','American']

    Neighbourhood_list = ['Lower East Side, Manhattan',
                   'Upper East Side, Manhattan',
                   'Upper West Side, Manhattan',
                   'Washington Heights, Manhattan',
                   'Central Harlem, Manhattan',
                   'Chelsea, Manhattan',
                   'Manhattan',
                   'East Harlem, Manhattan',
                   'Gramercy Park, Manhattan',
                   'Greenwich, Manhattan',
                   'Lower Manhattan, Manhattan',
                   'Columbus Circle, Manhattan'
                   'Times Square, Manhattan',
                   'Hells Kitchen, Manhattan',
                   'Midtown, Manhattan',
                   'Union Square, Manhattan']

    cusine_counters = []
    
    for cuisine in cuisines:
        cuisine_counter = 0

        for neighbourhood in Neighbourhood_list:

            response = search(API_KEY, cuisine, neighbourhood, 100) 
            business_data = response['businesses']
            businesses = handle_response(business_data, cuisine)
            push_data(businesses)  
            cuisine_counter += len(businesses)

        cusine_counters.append({'cuisine':cuisine, 'count':cuisine_counter})

        print(cusine_counters)


if __name__ == '__main__':
    main()
