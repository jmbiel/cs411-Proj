import flask
from flask import Flask
from flask import Flask, render_template, redirect, url_for
from urllib.parse import quote
import requests
from pymongo import MongoClient
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter

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
TWITTER_CLIENT_KEY = 'KGChrFAYY8eDwYuM2a0GmW85w'
TWITTER_API_SECRET = 'UIAbnB0QF20eG2d0SFjVNET9Tu5emnrqi1rUz8lGy6eNTus8mP'
TWITTER_ACCESS_TOKEN = '1223478032-PlhjfvY3Hg7b61xQeS7cWqdzgWb1hkzeMxgXU3I'
TWITTER_ACCESS_SECRET = 'WDx05fPXl4h84u4D9UDlFdWHCdS8g1HqPkxoQbPIqffgs'

# Setup Mongo DB connection
client = MongoClient()
repo = client["Nightlife_Reccomendation"]
repo.authenticate('group5', 'group5')

# Setup twitter OAuth
twitter_blueprint = make_twitter_blueprint(api_key=TWITTER_CLIENT_KEY, api_secret=TWITTER_API_SECRET)
app.register_blueprint(twitter_blueprint, url_prefix='/twitter_login')

@app.route("/")
def render_home():
    if not twitter.authorized:
        return redirect(url_for('twitter.login'))
    
    account_info = twitter.get('account/settings.json').json()
    return render_template("index.html", user_name=account_info['screen_name'])

@app.route("/twitter")
def twitter_login():
    if not twitter.authorized:
        return redirect(url_for('twitter.login'))
    account_info = twitter.get('account/settings.json')

    if account_info.ok:
        account_info_json = account_info.json()

        return '<h1>Your twitter name is @{}</h1>'.format(account_info_json['screen_name'])
    
    return "<h1>Request Failed</h1>"


@app.route("/yelp_api_call", methods=['POST'])
def yelp_api_call():
    user_input = flask.request.form['search_input']
    business = getBusiness(user_input)
    reviews = getReview(business)

    address = business['location']['display_address'][0] + business['location']['display_address'][1]
    pic = business['image_url']
    is_closed = business['is_closed']
    name = business['name']
    #print(business)
    # # print(business['if_closed'])
    # print(business)
    # print(type(business['is_closed']))
    return render_template('reviews.html', reviews=reviews, address = address, pic = pic, hours = ifclose(is_closed), name = name)

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

def ifclose(x):
    if x:
        return "Closed"
    else:
        return "Open"

if __name__ == '__main__':
    app.run(port=8000, debug=True)
