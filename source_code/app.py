import flask
from flask import Flask, redirect, url_for, render_template, request, session, flash
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
import requests
import os
import sarcasm_model
import troll_model
import youtube_utilities
import pandas as pd

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import bilingual_analytics

from flask_sqlalchemy import SQLAlchemy
from forms import RegistrationForm, LoginForm

import os
from dotenv import load_dotenv

load_dotenv('.env')


app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

twitter_blueprint = make_twitter_blueprint(
    api_key=os.environ.get('TWITTER_API_KEY'), api_secret=os.environ.get('TWITTER_API_SECRET'))

app.register_blueprint(twitter_blueprint, url_prefix='/login')

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


class User(db.Model):
    email = db.Column(db.String(120), unique=True,
                      nullable=False, primary_key=True)
    password = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return f"User('{self.email}')"


def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}


@app.route('/',  methods=['GET', 'POST'])
def index():
    if 'email' in session:
        login = True
        return render_template('index.html')

    form = LoginForm()
    if form.validate_on_submit():
        user_email = form.email.data
        user_password = form.password.data
        user_db = User.query.filter_by(email=user_email).first()
        if user_db != None:
            if user_db.password == user_password:
                session['email'] = user_email
                flash('You have been logged in!', 'success')
                return render_template('index.html')
        else:
            return render_template('login.html', title='Login', form=form)

    return render_template('login.html', title='Login', form=form)


@ app.route("/register",  methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(email=form.email.data, password=form.password.data)
        db.session.add(new_user)
        db.session.commit()
        print(form.email.data)
        print(form.password.data)
        flash(f'Account created for {form.email.data}!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html', title='Register', form=form)


@ app.route('/twitter')
def twitter_login():
    # If the user is not authorized, redirect to the twitter login page

    if not twitter.authorized:
        return redirect(url_for('twitter.login'))

    account_info = twitter.get('1.1/account/settings.json')

    user_tweets = twitter.get(
        "1.1/statuses/user_timeline.json")

    # If account information is successfully retrieved, proceed to analyse and display it
    if account_info.ok:
        # Convert retrieved info to json format
        user_tweets_json = user_tweets.json()
        account_info_json = account_info.json()

        user_screen_name = account_info_json['screen_name']

        all_tweets = []
        tweet_id = []

        for tweet in user_tweets_json:
            tweet_text = tweet['text']
            t_id = tweet['id_str']
            all_tweets.append(tweet_text)
            tweet_id.append(t_id)

        mentions = twitter.get("1.1/statuses/mentions_timeline.json").json()
        responses = []
        tweet_id_for_response = []
        responder_screen_name = []
        reply_ids = []

        dic = {}

        for i in range(0, len(tweet_id)):
            dic[tweet_id[i]] = {
                "reply_id": [],
                "tweet": all_tweets[i],
                "user": [],
                "comment": [],
                "sarcasm": [],
                "troll": [],
                "is_hinglish": [],
                "hinglish_sentiment": []
            }

        payload = "{\n    \"hidden\": true\n}"
        headers = {
            'Content-Type': 'application/json'
        }

        # op_res = twitter.put(
        #     "2/tweets/" + mentions[0]['id_str'] + "/hidden", headers=headers, data=payload).json()
        # print(op_res)

        for response in mentions:
            response_text = response['text']
            responses.append(response_text)

            reply_to = response['in_reply_to_status_id_str']
            tweet_id_for_response.append(reply_to)

            name = response['user']['screen_name']
            responder_screen_name.append(name)

            r_id = response['id_str']
            reply_ids.append(r_id)

        responses = [r.replace("@"+user_screen_name, "") for r in responses]
        print(responses)

        # hinglish detection
        hinglish_detection_lst = [
            bilingual_analytics.detect_hinglish(s) for s in responses]
        print(hinglish_detection_lst)

        # hinglish sentiment
        hinglish_sentiment_lst = []
        for i in range(0, len(hinglish_detection_lst)):
            if (hinglish_detection_lst[i] == True):
                hinglish_sentiment_lst.append(
                    bilingual_analytics.hinglish_sentiment([responses[i]]))
            else:
                hinglish_sentiment_lst.append("NA")
        print(hinglish_sentiment_lst)

        # sarcasm classification
        sarcasm_obj = sarcasm_model.run_model(responses)
        sarcasm_classified = sarcasm_obj.classify()
        sarcasm_classified = ['Yes' if x ==
                              1 else 'No' for x in sarcasm_classified]

        # troll classfication
        troll_obj = troll_model.run_model(responses)
        troll_classified = troll_obj.classify()
        troll_classified = ['Yes' if x ==
                            1 else 'No' for x in troll_classified]

        #
        for i in range(len(sarcasm_classified)):
            if (hinglish_detection_lst[i] == True):
                sarcasm_classified[i] = "NA"
                troll_classified[i] = "NA"

        for i in range(0, len(responses)):
            if tweet_id_for_response[i] in dic.keys():

                if ((troll_classified[i] == 'Yes' and sarcasm_classified[i] == "No") or (hinglish_detection_lst[i] == True and hinglish_sentiment_lst[i] == 'negative')):
                    # hide reply if it is a troll and not sarcastic
                    op_res = twitter.put(
                        "2/tweets/" + reply_ids[i] + "/hidden", headers=headers, data=payload).json()

                else:
                    dic[tweet_id_for_response[i]
                        ]['reply_id'].append(reply_ids[i])
                    dic[tweet_id_for_response[i]
                        ]["comment"].append(responses[i])
                    dic[tweet_id_for_response[i]]["user"].append(
                        responder_screen_name[i])
                    dic[tweet_id_for_response[i]]["sarcasm"].append(
                        sarcasm_classified[i])
                    dic[tweet_id_for_response[i]]["troll"].append(
                        troll_classified[i])
                    dic[tweet_id_for_response[i]]["is_hinglish"].append(
                        hinglish_detection_lst[i])
                    dic[tweet_id_for_response[i]]["hinglish_sentiment"].append(
                        hinglish_sentiment_lst[i])

        sarcastic_total = 0
        troll_total = 0

        for k in dic.keys():
            troll_lst = dic[k]["troll"]
            troll_total += troll_lst.count('Yes')

            sarcastic_lst = dic[k]["sarcasm"]
            sarcastic_total += sarcastic_lst.count('Yes')

        data = {
            "dict": dic,
            "sarcastic_total": sarcastic_total,
            "troll_total": troll_total
        }
        # Render template with user data
        return render_template("twitter_home.html", data=data)

    # If account info is not retrieved successfully return an error message.
    return '<h2>Error</h2>'


@app.route('/youtube_login')
def youtube_login():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

    yt = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    # Save credentials back to session in case access token was refreshed.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.

    videos = youtube_utilities.get_channel_videos(yt)

    video_ids = []
    video_titles = []

    for vid in videos:
        v_id = vid['snippet']['resourceId']['videoId']
        v_title = vid['snippet']['title']
        video_ids.append(v_id)
        video_titles.append(v_title)

    all_comments_dfs = []

    for v_id, v_title in zip(video_ids, video_titles):
        df = youtube_utilities.get_comments_dataframe(v_id, yt)
        df['video_title'] = v_title
        all_comments_dfs.append(df)

    comments_df = pd.concat(all_comments_dfs)

    ####################
    dic = {}

    for i in range(0, len(video_ids)):
        dic[video_ids[i]] = {
            "video_title": video_titles[i],
            "user": [],
            "comment": [],
            "comment_id": [],
            "sarcasm": [],
            "troll": [],
            "is_hinglish": [],
            "hinglish_sentiment": []
        }

    responses = comments_df['textDisplay'].tolist()
    video_id_for_response = comments_df['videoID'].tolist()
    responder_screen_name = comments_df['authorDisplayName'].tolist()
    comment_ids = comments_df['topCommentID'].tolist()

    # hinglish detection
    hinglish_detection_lst = [
        bilingual_analytics.detect_hinglish(s) for s in responses]

    # hinglish sentiment
    hinglish_sentiment_lst = []
    for i in range(0, len(hinglish_detection_lst)):
        if (hinglish_detection_lst[i] == True):
            hinglish_sentiment_lst.append(
                bilingual_analytics.hinglish_sentiment([responses[i]]))
        else:
            hinglish_sentiment_lst.append("NA")

    # sarcasm classification
    sarcasm_obj = sarcasm_model.run_model(responses)
    sarcasm_classified = sarcasm_obj.classify()
    sarcasm_classified = ['Yes' if x ==
                          1 else 'No' for x in sarcasm_classified]

    # troll classfication
    troll_obj = troll_model.run_model(responses)
    troll_classified = troll_obj.classify()
    troll_classified = ['Yes' if x ==
                        1 else 'No' for x in troll_classified]

    #
    for i in range(len(sarcasm_classified)):
        if (hinglish_detection_lst[i] == True):
            sarcasm_classified[i] = "NA"
            troll_classified[i] = "NA"

    for i in range(0, len(responses)):
        if video_id_for_response[i] in dic.keys():
            if ((troll_classified[i] == 'Yes' and sarcasm_classified[i] == 'No') or (hinglish_detection_lst[i] == True and hinglish_sentiment_lst[i] == 'negative')):
                hide_comment_id = comment_ids[i]
                youtube_utilities.hold_for_review(hide_comment_id, yt)

            else:
                dic[video_id_for_response[i]]["comment"].append(responses[i])
                dic[video_id_for_response[i]]["user"].append(
                    responder_screen_name[i])
                dic[video_id_for_response[i]]["sarcasm"].append(
                    sarcasm_classified[i])
                dic[video_id_for_response[i]]["troll"].append(
                    troll_classified[i])
                dic[video_id_for_response[i]]["is_hinglish"].append(
                    hinglish_detection_lst[i])
                dic[video_id_for_response[i]]["hinglish_sentiment"].append(
                    hinglish_sentiment_lst[i])

    sarcastic_total = 0
    troll_total = 0

    for k in dic.keys():
        troll_lst = dic[k]["troll"]
        troll_total += troll_lst.count('Yes')

        sarcastic_lst = dic[k]["sarcasm"]
        sarcastic_total += sarcastic_lst.count('Yes')

    data = {
        "dict": dic,
        "sarcastic_total": sarcastic_total,
        "troll_total": troll_total
    }

    flask.session['credentials'] = credentials_to_dict(credentials)

    # Render template with user data
    return render_template("youtube_home.html", data=data)


@app.route('/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    flask.session['state'] = state

    return flask.redirect(authorization_url)


@app.route('/youtube')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)

    return flask.redirect(flask.url_for('youtube_login'))


@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    app.run(debug=True)
