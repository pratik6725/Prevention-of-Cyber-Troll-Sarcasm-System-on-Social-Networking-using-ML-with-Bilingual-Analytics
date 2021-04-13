import requests
import os
import flask
from flask import Flask, redirect, url_for, render_template, request, session, flash

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

from vmanager.models import User, hinglish_sentiment_analysis, count_total_sarcasm_and_troll
from vmanager.models import sarcasm_classification, get_twitter_data, credentials_to_dict, get_youtube_data
from vmanager.models import hide_comments_twitter, troll_classification, hide_comments_youtube, reply_to_comments_youtube


from vmanager.forms import RegistrationForm, LoginForm
from vmanager import app
import vmanager.sarcasm_model
import vmanager.troll_model
import vmanager.youtube_utilities
from vmanager import db
from flask_dance.contrib.twitter import twitter

from flask_dance.contrib.twitter import make_twitter_blueprint, twitter


CLIENT_SECRETS_FILE = "vmanager\client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


@ app.route('/', methods=['GET', 'POST'])
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


@ app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(email=form.email.data, password=form.password.data)
        db.session.add(new_user)
        db.session.commit()
        # print(form.email.data)
        # print(form.password.data)
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

        # User's screen name
        user_screen_name = account_info_json['screen_name']

        # Retrieve user mentions for getting replies to user's tweets
        mentions = twitter.get("1.1/statuses/mentions_timeline.json").json()

        # Extract all information regarding replies from raw data
        responses, tweet_id_for_response, responder_screen_name, reply_ids, dic, replies_not_responded = get_twitter_data(
            user_tweets_json, mentions)

        # replies_not_responded is a list of replies to which the user must respond or reply

        responses = [r.replace("@" + user_screen_name, "") for r in responses]

        # Hinglish Sentiment Analysis
        hinglish_detection_lst, hinglish_sentiment_lst = hinglish_sentiment_analysis(
            responses)

        # sarcasm classification
        sarcasm_classified = sarcasm_classification(
            responses)

        # troll classfication
        troll_classified = troll_classification(
            responses)

        for i in range(len(sarcasm_classified)):
            if (hinglish_detection_lst[i] == True):
                sarcasm_classified[i] = "NA"
                troll_classified[i] = "NA"

        # hide comments
        dic, responses_to_be_replied, reply_to = hide_comments_twitter(reply_ids, twitter, responses, dic, responder_screen_name,
                                                                       hinglish_detection_lst, tweet_id_for_response, troll_classified, sarcasm_classified,
                                                                       hinglish_sentiment_lst)

        sarcastic_total, troll_total = count_total_sarcasm_and_troll(dic)

        # responsed_to_be_replied contains filtered replies which are good and must be responded

        for i in range(len(responses_to_be_replied)):
            if (responses_to_be_replied[i] in replies_not_responded):
                respond_to = reply_to[i]
                k = twitter.post(
                    "1.1/statuses/update.json",
                    params={
                        "status": "@" + respond_to + " Thank you 😄",
                        "in_reply_to_status_id": responses_to_be_replied[i]}).json()
                # print(k)

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

    # Extract data from user's youtube account
    responses, video_id_for_response, responder_screen_name, comment_ids, dic, unreplied_id, video_thumbnails = get_youtube_data(
        yt)

    # unreplied_id = all unreplied

    # Hinglish Sentiment Analysis
    hinglish_detection_lst, hinglish_sentiment_lst = hinglish_sentiment_analysis(
        responses)

    # sarcasm classification
    sarcasm_classified = sarcasm_classification(
        responses)

    # troll classfication
    troll_classified = troll_classification(
        responses)

    for i in range(len(sarcasm_classified)):
        if (hinglish_detection_lst[i] == True):
            sarcasm_classified[i] = "NA"
            troll_classified[i] = "NA"

    dic, hidden_comments = hide_comments_youtube(yt, responses, video_id_for_response, dic, troll_classified, sarcasm_classified,
                                                 hinglish_detection_lst, hinglish_sentiment_lst, comment_ids, responder_screen_name)

    sarcastic_total, troll_total = count_total_sarcasm_and_troll(dic)

    data = {
        "dict": dic,
        "sarcastic_total": sarcastic_total,
        "troll_total": troll_total
    }

    # reply to all unreplied comments except for the ones those are hidden

    for i in range(len(unreplied_id)):
        if (unreplied_id[i] not in hidden_comments):
            # reply to this comment
            reply_to_comments_youtube(unreplied_id[i], yt)

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
