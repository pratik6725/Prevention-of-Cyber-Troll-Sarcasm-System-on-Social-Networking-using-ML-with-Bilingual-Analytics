from flask import Flask, redirect, url_for, render_template, request
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
import requests
import os
import sarcasm_model
import troll_model

app = Flask(__name__)
app.config['SECRET_KEY'] = "priyamane"

twitter_blueprint = make_twitter_blueprint(
    api_key=os.environ.get('API_KEY'), api_secret=os.environ.get('API_SECRET'))

app.register_blueprint(twitter_blueprint, url_prefix='/login')


@app.route('/')
def index():
    # dashboard
    return render_template('index.html')


@app.route('/twitter')
def twitter_login():
    # If the user is not authorized, redirect to the twitter login page

    if not twitter.authorized:
        return redirect(url_for('twitter.login'))

    account_info = twitter.get('account/settings.json')

    user_tweets = twitter.get(
        "statuses/user_timeline.json")

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

        mentions = twitter.get("statuses/mentions_timeline.json").json()
        responses = []
        tweet_id_for_response = []
        responder_screen_name = []

        dic = {}

        for i in range(0, len(tweet_id)):
            dic[tweet_id[i]] = {
                "tweet": all_tweets[i],
                "user": [],
                "comment": [],
                "sarcasm": [],
                "troll": []
            }

        for response in mentions:
            response_text = response['text']
            responses.append(response_text)
            reply_to = response['in_reply_to_status_id_str']
            tweet_id_for_response.append(reply_to)
            name = response['user']['screen_name']
            responder_screen_name.append(name)

        responses = [r.replace("@"+user_screen_name, "") for r in responses]

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

        # troll classification
        for i in range(0, len(responses)):
            if tweet_id_for_response[i] in dic.keys():
                dic[tweet_id_for_response[i]]["comment"].append(responses[i])
                dic[tweet_id_for_response[i]]["user"].append(
                    responder_screen_name[i])
                dic[tweet_id_for_response[i]]["sarcasm"].append(
                    sarcasm_classified[i])
                dic[tweet_id_for_response[i]]["troll"].append(
                    troll_classified[i])

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


if __name__ == '__main__':
    app.run(debug=True)
