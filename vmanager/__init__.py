from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import vmanager.flask_dance_doppelganger
from vmanager.flask_dance_doppelganger.contrib.twitter import make_twitter_blueprint, twitter

# load_dotenv('.env')

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# twitter_blueprint = make_twitter_blueprint(api_key=os.environ.get(
#     'TWITTER_API_KEY'), api_secret=os.environ.get('TWITTER_API_SECRET'))
# app.register_blueprint(twitter_blueprint, url_prefix='/login')

twitter_blueprint = make_twitter_blueprint(
    api_key="xZtEltvZIQO3BhVr5tcxQmj1F", api_secret="P6y28UdkqT6wUPescbUfR03ZbtFXP6dmLBfBbVQw0Das1J4jEg")

app.register_blueprint(twitter_blueprint, url_prefix='/login')

# to avoid circular import
from vmanager import routes
