import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def authenticate(client_secret_file, scopes):
    creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.

    script_dir_path = os.path.dirname(__file__)
    token_file = os.path.join(script_dir_path, "token.json")
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return creds


def retrieve_playlist_ids(youtube, playlist_name):
    next_page_token = None
    ids = []

    while(True):
        playlists = youtube.playlists().list(
            part="id, snippet",
            mine=True,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        items = playlists["items"]
        for item in items:
            if item["snippet"]["title"] == playlist_name:
                ids.append(item["id"])

        next_page_token = playlists.get("nextPageToken", None)
        if(not next_page_token): break

    return ids


def retrieve_duplicate_videos(youtube, play_list_id):
    # key: 動画のタイトル．
    # value: 動画のidのリスト．タイトルが同じ動画があった場合は複数になる．
    title_id_table = {}

    # 動画のタイトルとidをtitle_id_tableに整理する
    next_page_token = None
    while(True):
        playlist = youtube.playlistItems().list(
            part="id, snippet",
            playlistId=play_list_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        items = playlist["items"]

        for item in items:
            if not item["snippet"]["title"] in title_id_table:
                title_id_table[item["snippet"]["title"]] = []

            title_id_table[item["snippet"]["title"]].append(item["id"])

        next_page_token = playlist.get("nextPageToken", None)
        if(not next_page_token): break

    # 重複している動画をリスト化する
    duplicate_videos = {}
    for title, ids in title_id_table.items():
        if len(ids) >= 2:
            duplicate_videos[title] = ids[0]

    return duplicate_videos


def delete_playlist_item(youtube, id):
    youtube.playlistItems().delete(
        id=id
    ).execute()


def main():
    if len(sys.argv) < 2:
        print("usage: python delete_duplicate_videos.py <my_playlist_name>")
        exit(1)
    else:
        play_list_name = sys.argv[1]

    CLIENT_SECRETS_FILE = "client_secrets.json"
    # このOAuth 2.0のスコープは，ログインしたアカウントのあらゆる操作を許可する
    YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    # 証明書の取得 (ログイン)
    creds = authenticate(CLIENT_SECRETS_FILE, YOUTUBE_SCOPE)

    # YouTubeリソースの作成
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    credentials=creds)

    # プレイリスト名から，playlistIdを取得する
    playlist_ids = retrieve_playlist_ids(youtube, play_list_name)
    print(f"playlist_ids: {playlist_ids}")
    print()

    if (len(playlist_ids) == 0):
        print("無効なプレイリスト名です")
        sys.exit(1)

    # 重複するビデオとそのidを取得する
    duplicate_videos = retrieve_duplicate_videos(youtube, playlist_ids[0])

    for title, id in duplicate_videos.items():
        print(f"{title}: {id}")

    # 重複するビデオを削除する
    for title, id in duplicate_videos.items():
        print(f"Delete {title}")
        delete_playlist_item(youtube, id)


if __name__ == '__main__':
    main()
