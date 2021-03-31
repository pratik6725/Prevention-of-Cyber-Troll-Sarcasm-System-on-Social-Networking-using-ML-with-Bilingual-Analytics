from vmanager import db
from vmanager import bilingual_analytics, sarcasm_model, troll_model, youtube_utilities
import pandas as pd


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


def hinglish_sentiment_analysis(responses):
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

    return hinglish_detection_lst, hinglish_sentiment_lst


def sarcasm_classification(responses):
    sarcasm_obj = sarcasm_model.run_model(responses)
    sarcasm_classified = sarcasm_obj.classify()
    sarcasm_classified = ['Yes' if x ==
                          1 else 'No' for x in sarcasm_classified]

    return sarcasm_classified


def troll_classification(responses):
    troll_obj = troll_model.run_model(responses)
    troll_classified = troll_obj.classify()
    troll_classified = ['Yes' if x ==
                        1 else 'No' for x in troll_classified]

    return troll_classified


def get_twitter_data(user_tweets_json, mentions):

    all_tweets = []
    tweet_id = []

    for tweet in user_tweets_json:
        tweet_text = tweet['text']
        t_id = tweet['id_str']
        all_tweets.append(tweet_text)
        tweet_id.append(t_id)

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

    for response in mentions:
        response_text = response['text']
        responses.append(response_text)

        reply_to = response['in_reply_to_status_id_str']
        tweet_id_for_response.append(reply_to)

        name = response['user']['screen_name']
        responder_screen_name.append(name)

        r_id = response['id_str']
        reply_ids.append(r_id)

    return responses, tweet_id_for_response, responder_screen_name, reply_ids, dic


def get_youtube_data(yt):
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

    return responses, video_id_for_response, responder_screen_name, comment_ids, dic


def hide_comments_twitter(reply_ids, twitter, responses, dic, responder_screen_name, hinglish_detection_lst, tweet_id_for_response, troll_classified, sarcasm_classified, hinglish_sentiment_lst):

    payload = "{\n    \"hidden\": true\n}"
    headers = {
        'Content-Type': 'application/json'
    }

    for i in range(0, len(responses)):
        if tweet_id_for_response[i] in dic.keys():
            if ((troll_classified[i] == 'Yes' and sarcasm_classified[i] == "No") or (hinglish_sentiment_lst[i] == 'negative')):
                # hide reply if it is a troll and not sarcastic
                op_res = twitter.put(
                    "2/tweets/" + reply_ids[i] + "/hidden", headers=headers, data=payload).json()
            else:
                dic[tweet_id_for_response[i]]['reply_id'].append(reply_ids[i])
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
    return dic


def hide_comments_youtube(responses, video_id_for_response, dic, troll_classified, sarcasm_classified, hinglish_detection_lst, hinglish_sentiment_lst, comment_ids, responder_screen_name):
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

    return dic


def count_total_sarcasm_and_troll(dic):
    troll_total = 0
    sarcastic_total = 0

    for k in dic.keys():
        troll_lst = dic[k]["troll"]
        troll_total += troll_lst.count('Yes')

        sarcastic_lst = dic[k]["sarcasm"]
        sarcastic_total += sarcastic_lst.count('Yes')

    return sarcastic_total, troll_total
