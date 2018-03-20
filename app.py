import flask
from flask import Flask, render_template

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