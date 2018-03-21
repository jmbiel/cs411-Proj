import flask
from flask import Flask, render_template
from urllib.parse import quote
import requests

"""
Yelp -- RELEVANT INFORMATION
Client ID: iQaMQisiPaQkU7QSSkzG3A
API Key: H1ZaDuODlr5cjTjZ-yxUWt5us1U5VPdOXqB4f8We9-3Q1VQyt-jem1BTDCg4ZthQfLYsNF4TILRU6s2jQ8f93_tHrgEuKhoO5fatTBEdx6BrG-t9fM_3DotojmixWnYx
"""
app = Flask(__name__)

YELP_API_HOST = 'https://api.yelp.com'
YELP_SEARCH_PATH = '/v3/businesses/search'
YELP_API_KEY = 'H1ZaDuODlr5cjTjZ-yxUWt5us1U5VPdOXqB4f8We9-3Q1VQyt-jem1BTDCg4ZthQfLYsNF4TILRU6s2jQ8f93_tHrgEuKhoO5fatTBEdx6BrG-t9fM_3DotojmixWnYx'

@app.route("/")
def render_home():
    return render_template("index.html")

@app.route("/yelp_api_call", methods=['POST'])
def yelp_api_call():
    user_input = flask.request.form['search_input']
    business = getBusiness(user_input)
    reviews = getReview(business)

    return render_template('index.html', data=reviews)

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

    response = requests.request('GET', url, headers=headers, params=url_params).json()
    return response['businesses'][0]

def getReview(business):
    url = 'https://api.yelp.com/v3/businesses/' + business['id'] + '/reviews'
    headers = {
        'Authorization': 'Bearer %s' % YELP_API_KEY
    }

    response = requests.request('GET', url, headers=headers).json()
    reviews = response['reviews']
    formatted_reviews = [(x['rating'], x['text']) for x in reviews]
    return formatted_reviews

if __name__ == '__main__':
    app.run(port=8080, debug=True)