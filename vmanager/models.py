from vmanager import db
from vmanager import bilingual_analytics, sarcasm_model, troll_model, youtube_utilities
import pandas as pd
import numpy as np


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

    replied_tweets = []

    for tweet in user_tweets_json:
        if (tweet['in_reply_to_status_id_str'] is None):
            # normal tweet
            tweet_text = tweet['text']
            t_id = tweet['id_str']
            all_tweets.append(tweet_text)
            tweet_id.append(t_id)
        else:
            # its a reply
            replied_tweets.append(
                tweet['in_reply_to_status_id_str'])

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

    replies_not_responded = np.setdiff1d(reply_ids, replied_tweets)
    # print("replied tweets : ")
    # print(replied_tweets)

    return responses, tweet_id_for_response, responder_screen_name, reply_ids, dic, replies_not_responded


def get_youtube_data(yt):
    videos = youtube_utilities.get_channel_videos(yt)

    video_ids = []
    video_titles = []
    video_thumbnails = []

    channel_id = 'None'

    for vid in videos:
        channel_id = vid['snippet']['channelId']
        v_id = vid['snippet']['resourceId']['videoId']
        v_title = vid['snippet']['title']
        v_thumbnail = vid['snippet']['thumbnails']['medium']['url']
        video_ids.append(v_id)
        video_titles.append(v_title)
        video_thumbnails.append(v_thumbnail)

    all_comments_dfs = []

    for v_id, v_title in zip(video_ids, video_titles):
        df, unreplied_id = youtube_utilities.get_comments_dataframe(
            v_id, channel_id, yt)
        df['video_title'] = v_title
        all_comments_dfs.append(df)

    comments_df = pd.concat(all_comments_dfs)

    dic = {}

    for i in range(0, len(video_ids)):
        dic[video_ids[i]] = {
            "video_title": video_titles[i],
            "video_thumbnail": video_thumbnails[i],
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

    return responses, video_id_for_response, responder_screen_name, comment_ids, dic, unreplied_id, video_thumbnails


def hide_comments_twitter(reply_ids, twitter, responses, dic, responder_screen_name, hinglish_detection_lst, tweet_id_for_response, troll_classified, sarcasm_classified, hinglish_sentiment_lst):

    payload = "{\n    \"hidden\": true\n}"
    headers = {
        'Content-Type': 'application/json'
    }

    responsed_to_be_replied = []
    reply_to = []

    for i in range(0, len(responses)):
        if tweet_id_for_response[i] in dic.keys():
            if ((troll_classified[i] == 'Yes' and sarcasm_classified[i] == "No") or (hinglish_sentiment_lst[i] == 'negative')):
                # hide reply if it is a troll and not sarcastic
                op_res = twitter.put(
                    "2/tweets/" + reply_ids[i] + "/hidden", headers=headers, data=payload).json()
            else:
                responsed_to_be_replied.append(reply_ids[i])
                reply_to.append(responder_screen_name[i])

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
    return dic, responsed_to_be_replied, reply_to


def hide_comments_youtube(yt, responses, video_id_for_response, dic, troll_classified, sarcasm_classified, hinglish_detection_lst, hinglish_sentiment_lst, comment_ids, responder_screen_name):
    hidden_comments = []
    for i in range(0, len(responses)):
        if video_id_for_response[i] in dic.keys():
            if ((troll_classified[i] == 'Yes' and sarcasm_classified[i] == 'No') or (hinglish_detection_lst[i] == True and hinglish_sentiment_lst[i] == 'negative')):
                hide_comment_id = comment_ids[i]
                hold_for_review(hide_comment_id, yt)
                hidden_comments.append(hide_comment_id)

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

    return dic, hidden_comments


def count_total_sarcasm_and_troll(dic):
    troll_total = 0
    sarcastic_total = 0

    for k in dic.keys():
        troll_lst = dic[k]["troll"]
        troll_total += troll_lst.count('Yes')

        sarcastic_lst = dic[k]["sarcasm"]
        sarcastic_total += sarcastic_lst.count('Yes')

    return sarcastic_total, troll_total


def reply_to_comments_youtube(comment_id, youtube):
    reply = "Thank you 🤟"

    insert_reply = youtube.comments().insert(
        part="snippet",
        body=dict(
            snippet=dict(
                parentId=comment_id,
                textOriginal=reply
            )
        )
    ).execute()


def hold_for_review(comment_id, youtube):
    request = youtube.comments().setModerationStatus(
        id=str(comment_id), moderationStatus="heldForReview")
    request.execute()
