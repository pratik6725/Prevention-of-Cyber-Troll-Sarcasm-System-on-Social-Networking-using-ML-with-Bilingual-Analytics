import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import pandas as pd


def get_channel_videos(channel_id, youtube):
    r = youtube.channels().list(id=channel_id,
                                part='contentDetails').execute()
    playlist_id = r['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    videos = []
    next_page_token = None
    while 1:
        res = youtube.playlistItems().list(playlistId=playlist_id,
                                           part='snippet',
                                           maxResults=50,
                                           pageToken=next_page_token).execute()
        videos += res['items']
        next_page_token = res.get('nextPageToken')

        if next_page_token is None:
            return videos


def get_all_comments(video_id, youtube):
    comments = []
    next_page_token = None
    while 1:
        res = youtube.commentThreads().list(part='snippet', videoId=video_id,
                                            maxResults=100, pageToken=next_page_token).execute()
        comments += res['items']
        next_page_token = res.get('nextPageToken')

        if next_page_token is None:
            return comments


def get_comments_dataframe(video_id, youtube):
    com = get_all_comments(video_id, youtube)

    cols = ['threadID', 'videoID', 'topCommentID', 'authorDisplayName', 'authorChannelURL', 'textDisplay',
            'likes', 'publishDate', 'replyCount']
    comments_df = pd.DataFrame(columns=cols)

    total = len(com)

    for i in range(0, total):
        obj = com[i]['snippet']
        dic = {
            'threadID': com[i]['id'],
            'videoID': obj['videoId'],
            'topCommentID': obj['topLevelComment']['id'],
            'authorDisplayName': obj['topLevelComment']['snippet']['authorDisplayName'],
            'authorChannelURL': obj['topLevelComment']['snippet']['authorChannelUrl'],
            'textDisplay': obj['topLevelComment']['snippet']['textDisplay'],
            'likes': obj['topLevelComment']['snippet']['likeCount'],
            'publishDate': obj['topLevelComment']['snippet']['publishedAt'],
            'replyCount': obj['totalReplyCount']
        }
        comments_df = comments_df.append(dic, ignore_index=True)

    return comments_df


def get_channel_videos(youtube):
    r = youtube.channels().list(part='contentDetails', mine=True).execute()
    playlist_id = r['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    videos = []
    next_page_token = None
    while 1:
        res = youtube.playlistItems().list(playlistId=playlist_id,
                                           part='snippet',
                                           maxResults=50,
                                           pageToken=next_page_token).execute()
        videos += res['items']
        next_page_token = res.get('nextPageToken')

        if next_page_token is None:
            return videos


def hold_for_review(comment_id, youtube):
    request = youtube.comments().setModerationStatus(
        id=str(comment_id), moderationStatus="heldForReview")
    request.execute()
