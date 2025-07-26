# youtube_search.py
from googleapiclient.discovery import build

class YouTubeSearch:
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def search_video(self, query, max_results=1):
        try:
            request = self.youtube.search().list(
                q=query,
                part='snippet',
                maxResults=max_results,
                type='video'
            )
            response = request.execute()
            if response['items']:
                video_id = response['items'][0]['id']['videoId']
                return video_id
            else:
                return None
        except Exception as e:
            print(f"Error during YouTube search: {e}")
            return None
