import flask
from flask import Flask, render_template

"""
yelp

Client ID
iQaMQisiPaQkU7QSSkzG3A


API Key
H1ZaDuODlr5cjTjZ-yxUWt5us1U5VPdOXqB4f8We9-3Q1VQyt-jem1BTDCg4ZthQfLYsNF4TILRU6s2jQ8f93_tHrgEuKhoO5fatTBEdx6BrG-t9fM_3DotojmixWnYx

"""
app = Flask(__name__)

@app.route("/")
def render_home():
    return render_template("index.html")

@app.route("/yelp_api_call", methods=['POST'])
def yelp_api_call():
    user_input = flask.request.form['search_input']
    print(user_input)
    return "temporary"

if __name__ == '__main__':
    app.run(port=8080, debug=True)