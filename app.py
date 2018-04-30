import flask
from flask import Flask
from flask import Flask, render_template, redirect, url_for, request
from urllib.parse import quote
import requests
from pymongo import MongoClient
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from uber_rides.session import Session
from uber_rides.client import UberRidesClient
from uber_rides.auth import AuthorizationCodeGrant
from uber_rides.errors import ClientError, ServerError, UberIllegalState
from yaml import safe_load

"""
Yelp -- RELEVANT INFORMATION
Client ID: iQaMQisiPaQkU7QSSkzG3A
API Key: H1ZaDuODlr5cjTjZ-yxUWt5us1U5VPdOXqB4f8We9-3Q1VQyt-jem1BTDCg4ZthQfLYsNF4TILRU6s2jQ8f93_tHrgEuKhoO5fatTBEdx6BrG-t9fM_3DotojmixWnYx
"""
app = Flask(__name__)
app.secret_key = "group5_secret_key"

YELP_API_HOST = 'https://api.yelp.com'
YELP_SEARCH_PATH = '/v3/businesses/search'
YELP_API_KEY = 'H1ZaDuODlr5cjTjZ-yxUWt5us1U5VPdOXqB4f8We9-3Q1VQyt-jem1BTDCg4ZthQfLYsNF4TILRU6s2jQ8f93_tHrgEuKhoO5fatTBEdx6BrG-t9fM_3DotojmixWnYx'
GOOGLE_API_KEY = 'AIzaSyCSZiUzLj08txto61StvlHBcAXOy2McoqU'


# Setup Mongo DB connection
client = MongoClient()
repo = client["Nightlife_Reccomendation"]
repo.authenticate('group5', 'group5')

# Setup Uber OAuth
with open('uber.rider.config.yaml', 'r') as config_file:
    config = safe_load(config_file)
    
credentials = {}
credentials['client_id'] = config['client_id']
credentials['client_secret'] = config['client_secret']
credentials['redirect_url'] = config['redirect_url']
credentials['scopes'] = set(config['scopes'])

auth_flow = AuthorizationCodeGrant(
    credentials['client_id'],
    credentials['scopes'],
    credentials['client_secret'],
    credentials['redirect_url']
    )

uber_client = None 

@app.route("/")
def authorize():
    """
    if not twitter.authorized:
        return redirect(url_for('twitter.login'))
    
    account_info = twitter.get('account/settings.json').json()
    """
    #return render_template("index.html", user_name=account_info['screen_name'])
    return redirect(auth_flow.get_authorization_url())

@app.route("/home")
def home():
    if type(uber_client) != None:
        rider_profile = uber_client.get_rider_profile().json
        return render_template('index.html', name=rider_profile['first_name'] + " " + rider_profile['last_name'])
    else:
        return render_template('index.html')



@app.route('/uber/connect')
def uber_login():
    session = auth_flow.get_session(request.url)
    global uber_client
    uber_client = UberRidesClient(session)
    return redirect(url_for('home'))

@app.route("/returnBusinessList", methods=['GET', 'POST'])
def returnBusinessList():
    zipcode = flask.request.form['location_input']
    radius = flask.request.form['radius_input']
    radius = float(radius) * 0.000621371 

    if "club" in flask.request.form:
        club = True 
    else:
        club = False 

    if "bar" in flask.request.form:
        bar = True 
    else:
        bar = False 

    url = '{0}{1}'.format(YELP_API_HOST, quote(YELP_SEARCH_PATH.encode('utf8')))
    headers = {
        'Authorization' : "Bearer %s" % YELP_API_KEY
    }

    url_params = {
        'location': zipcode,
        'radius': int(radius),
        'categories': "",
        'sort_by': 'distance',
        'limit': 10
    }

    if bar:
        url_params['categories'] += 'bars,'
    if club:
        url_params['categories'] += 'danceclubs,'


    response = requests.request('GET', url, headers=headers, params=url_params).json()

    businesses = []
    for b in response['businesses']:
        business = getBusiness(b['name'])
        businesses.append([business['name'], getReview(business), business['location']['display_address'], business['image_url'], ifclose(business['is_closed']), zipcode])

    return render_template('search.html', businesses=businesses)

@app.route("/yelp_api_call", methods=['POST'])
def yelp_api_call():
    user_input = flask.request.form['search_input']
    business = getBusiness(user_input)
    reviews = getReview(business)

    address = business['location']['display_address'][0] + business['location']['display_address'][1]
    pic = business['image_url']
    is_closed = business['is_closed']
    name = business['name']
    return render_template('reviews.html', reviews=reviews, address = address, pic = pic, hours = ifclose(is_closed), name = name)

@app.route("/call_uber", methods=['POST'])
def call_uber():
    business_name = flask.request.form['business_name']
    business = getBusiness(business_name)
    business_loc = business['coordinates']
    user_loc = flask.request.form['user_loc']
    user_lat_long = getLatLong(user_loc)
    response = uber_client.get_products(user_lat_long['lat'], user_lat_long['lng'])
    products = response.json.get('products')
    product_id = products[0].get('product_id')

    estimate = uber_client.estimate_ride(
        product_id=product_id,
        start_latitude=user_lat_long['lat'],
        start_longitude=user_lat_long['lng'],
        end_latitude=business_loc['latitude'],
        end_longitude=business_loc['longitude'],
        seat_count=2
    )

    fare=estimate.json.get('fare')
    
    return render_template('ride_request.html', request=True, fare=fare['display'], user_lat=user_lat_long['lat'], user_long=user_lat_long['lng'], business_lat=business_loc['latitude'], business_long=business_loc['longitude'], product_id=product_id, fare_id=fare['fare_id'])

@app.route("/confirm_uber", methods=['POST'])
def confirm_uber():
    user_lat = flask.request.form['user_lat']
    user_long = flask.request.form['user_long']
    business_lat = flask.request.form['business_lat']
    business_long = flask.request.form['business_long']
    product_id = flask.request.form['product_id']
    fare_id = flask.request.form['fare_id']
    response = uber_client.request_ride(
        product_id=product_id,
        start_latitude=float(user_lat),
        start_longitude=float(user_long),
        end_latitude=float(business_lat),
        end_longitude=float(business_long),
        seat_count=2,
        fare_id=fare_id
    )

    return "RIDE ORDERED"

def getBusiness(user_input):
    url = '{0}{1}'.format(YELP_API_HOST, quote(YELP_SEARCH_PATH.encode('utf8')))
    headers = {
        'Authorization': 'Bearer %s' % YELP_API_KEY
    }

    url_params = {
        'term': user_input,
        'location' : 'Boston, MA',
        'limit' : 1
    }
    
    if repo['Nightlife_Reccomendation.search_terms'].find({"term" : user_input}).count() == 0:
        response = requests.request('GET', url, headers=headers, params=url_params).json()
        db_insert = {}
        db_insert['term'] = user_input
        db_insert['response'] = response
        repo['Nightlife_Reccomendation.search_terms'].insert(db_insert)
        ret_val = response
    else:
        response = repo['Nightlife_Reccomendation.search_terms'].find({"term" : user_input})[0]
        ret_val = response['response']
    
    return ret_val['businesses'][0]

def getReview(business):
    url = 'https://api.yelp.com/v3/businesses/' + business['id'] + '/reviews'
    headers = {
        'Authorization': 'Bearer %s' % YELP_API_KEY
    }

    if repo['Nightlife_Reccomendation.reviews'].find({"business": business}).count() == 0:
        response = requests.request('GET', url, headers=headers).json()
        db_insert = {}
        db_insert['business'] = business
        db_insert['response'] = response
        repo['Nightlife_Reccomendation.reviews'].insert(db_insert)
        reviews = response['reviews']
    else:
        response = repo['Nightlife_Reccomendation.reviews'].find({'business': business})[0]
        reviews = response['response']['reviews']

    formatted_reviews = [(x['rating'], x['text']) for x in reviews]
    return formatted_reviews

def getLatLong(location):
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json?address={}".format(location)
    geocode_url += "&key={}".format(GOOGLE_API_KEY)
    response = requests.get(geocode_url).json()
    return response['results'][0]['geometry']['location']

def ifclose(x):
    if x:
        return "Closed"
    else:
        return "Open"

if __name__ == '__main__':
    app.run(port=8000, debug=True)
