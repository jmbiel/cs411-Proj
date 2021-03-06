import flask
from flask import Flask
from flask import Flask, render_template, redirect, url_for, request
from urllib.parse import quote
import requests
from pymongo import MongoClient
from uber_rides.session import Session
from uber_rides.client import UberRidesClient
from uber_rides.auth import AuthorizationCodeGrant
from uber_rides.errors import ClientError, ServerError, UberIllegalState
from yaml import safe_load

app = Flask(__name__)
app.secret_key = "group5_secret_key, ITS SUPER SECRET"



# Setup Mongo DB connection
client = MongoClient()
repo = client["Nightlife_Reccomendation"]
repo.authenticate('group5', 'group5')

# Setup Uber OAuth
with open('uber.rider.config.yaml', 'r') as config_file:
    uber_config = safe_load(config_file)
    
credentials = {}
credentials['client_id'] = uber_config['client_id']
credentials['client_secret'] = uber_config['client_secret']
credentials['redirect_url'] = uber_config['redirect_url']
credentials['scopes'] = set(uber_config['scopes'])

auth_flow = AuthorizationCodeGrant(
    credentials['client_id'],
    credentials['scopes'],
    credentials['client_secret'],
    credentials['redirect_url']
    )

uber_client = None

@app.route("/")
def authorize():
    """ Immediately authorize user with uber as soon as they enter the site
        Relatively integral to the entire use of the application             """
    return redirect(auth_flow.get_authorization_url())

@app.route("/home")
def home():
    """ Render the home page with the users information from Uber           """
    if type(uber_client) != None:
        rider_profile = uber_client.get_rider_profile().json
        return render_template('index.html',
                                name=rider_profile['first_name'] + " " + rider_profile['last_name']
                                )
    
    # If the uber_client is null, we need to reauthorize the user
    else:
        return redirect('/')



@app.route('/uber/connect')
def uber_login():
    """  Call back URI for uber oauth -- sets up the uber_client object and initializes a session """
    session = auth_flow.get_session(request.url)
    global uber_client
    uber_client = UberRidesClient(session)
    return redirect(url_for('home'))

@app.route("/returnBusinessList", methods=['GET', 'POST'])
def returnBusinessList():
    """     Logic for returning all businesses based on user preferences
            Performs Yelp API call to get list, then hits functions below
                    for more information on each business.                 """

    # If uber_client is null, need to reauthorize the user
    if type(uber_client) == None:
        return redirect('/')

    with open ('yelpAPI.config.yaml', 'r') as config_file:
        yelp_config = safe_load(config_file)

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

    url = '{0}{1}'.format(yelp_config['api_host'], quote(yelp_config['search_path'].encode('utf8')))
    headers = {
        'Authorization' : "Bearer %s" % yelp_config['api_key']
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
        businesses.append([business['name'],
                            getReview(business),
                            business['location']['display_address'],
                            business['image_url'],
                            ifclose(business['is_closed']),
                            zipcode])

    return render_template('search.html', businesses=businesses)

@app.route("/yelp_api_call", methods=['POST'])
def yelp_api_call():
    """     Deprecated endpoint -- used for testing     """
    user_input = flask.request.form['search_input']
    business = getBusiness(user_input)
    reviews = getReview(business)

    address = business['location']['display_address'][0] + business['location']['display_address'][1]
    pic = business['image_url']
    is_closed = business['is_closed']
    name = business['name']
    return render_template('reviews.html',
                            reviews=reviews,
                            address = address,
                            pic = pic,
                            hours = ifclose(is_closed), name = name)

@app.route("/call_uber", methods=['POST'])
def call_uber():
    """    Endpoint for calling uber -- grabs all necessary location information
            which is passed from the front-end, and makes API call to get an 
                            estimate of the fare charge.                           """

    if type(uber_client) == None:
        redirect('/')

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
    
    return render_template('ride_request.html',
                            request=True, confirmed=False,
                            fare=fare['display'],
                            user_lat=user_lat_long['lat'],
                            user_long=user_lat_long['lng'],
                            business_lat=business_loc['latitude'],
                            business_long=business_loc['longitude'],
                            product_id=product_id,
                            fare_id=fare['fare_id'])

@app.route("/confirm_uber", methods=['POST'])
def confirm_uber():
    """     Endpoint for when the user confirms the uber based on fare estimate.
                    Makes another API request that confirms the uber.           """
    if type(uber_client) == None:
        redirect('/')

    user_lat = flask.request.form['user_lat']
    user_long = flask.request.form['user_long']
    business_lat = flask.request.form['business_lat']
    business_long = flask.request.form['business_long']
    product_id = flask.request.form['product_id']
    fare_id = flask.request.form['fare_id']
    try:
        response = uber_client.request_ride(
            product_id=product_id,
            start_latitude=float(user_lat),
            start_longitude=float(user_long),
            end_latitude=float(business_lat),
            end_longitude=float(business_long),
            seat_count=2,
            fare_id=fare_id
        )
    except ClientError as error:
        return "Uber Error: {0}, {1}".format(error.errors, error.message)
        
    request = response.json 
    request_id = request.get('request_id')

    return render_template('ride_request.html',
                            request=False,
                            confirmed=True,
                            request_id=request_id)

@app.route("/cancel_uber", methods=['POST'])
def cancel_uber():
    """     API endpoint for if user decides to cancel uber.  Makes an
            API call to uber to cancel ride based on the request_id.        """

    request_id = flask.request.form['request_id']
    response = uber_client.cancel_ride(request_id)
    return render_template("ride_cancelled.html")

def getBusiness(user_input):
    with open('yelpAPI.config.yaml', 'r') as config_file:
        yelp_config = safe_load(config_file)

    url = '{0}{1}'.format(yelp_config['api_host'], quote(yelp_config['search_path'].encode('utf8')))
    headers = {
        'Authorization': 'Bearer %s' % yelp_config['api_key']
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

@app.route('/update_uber', methods=['POST'])
def update_uber():
    if type(uber_client) == None:
        redirect('/')
    
    request_id = flask.request.form['request_id']
    response = uber_client.get_ride_details(request_id)
    ride = response.json
    status = ride['status']
    status_str = ""

    if status == 'processing':
        status_str = "Processing"
    elif status == 'no_drivers_available':
        status_str = "No Drivers Available"
    elif status == 'accepted':
        status_str = "Accepted"
    elif status == 'arriving':
        status_str = "Arriving"
    elif status == 'in_progress':
        status_str = "In Progress"
    elif status == 'driver_canceled':
        status_str = "Drive Canceled"
    elif status == 'rider_canceled':
        status_str = "Rider Canceled"
    elif status == 'completed':
        status_str = "Completed"
    else:
        status_str = "Error: " + status
    
    return render_template('ride_request.html', confirmed=True, request=False, request_id=request_id, update=status_str)

def getReview(business):
    with open('yelpAPI.config.yaml', 'r') as config_file:
        yelp_config = safe_load(config_file)

    url = 'https://api.yelp.com/v3/businesses/' + business['id'] + '/reviews'
    headers = {
        'Authorization': 'Bearer %s' % yelp_config['api_key']
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
    with open('googleAPI.config.yaml', 'r') as config_file:
        google_config = safe_load(config_file)

    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json?address={}".format(location)
    geocode_url += "&key={}".format(google_config['api_key'])
    response = requests.get(geocode_url).json()
    print("RESPONSE: ", response)
    return response['results'][0]['geometry']['location']

def ifclose(x):
    if x:
        return "Closed"
    else:
        return "Open"

if __name__ == '__main__':
    app.run(port=8000, debug=True)
