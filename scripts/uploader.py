import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# The SCOPES for the YouTube Data API v3
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeUploader:
    def __init__(self, client_secrets_file="client_secret.json", token_file="token.pickle"):
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.youtube = self.get_authenticated_service()

    def get_authenticated_service(self):
        credentials = None
        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists(self.token_file):
            with open(self.token_file, "rb") as token:
                credentials = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
            else:
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file, SCOPES)
                credentials = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_file, "wb") as token:
                pickle.dump(credentials, token)

        return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    def set_thumbnail(self, video_id, thumbnail_path):
        """
        Sets a custom thumbnail for a video.
        """
        if not os.path.exists(thumbnail_path):
            logger.error(f"Thumbnail not found: {thumbnail_path}")
            return False

        logger.info(f"Uploading thumbnail for video {video_id}...")
        request = self.youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        )
        response = request.execute()
        logger.success(f"Thumbnail uploaded successfully for video {video_id}!")
        return response

    def upload_video(self, file_path, title, description, tags=None, category_id="24", privacy_status="public"):
        """
        Uploads a video to YouTube.
        Category 24 = Entertainment.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        body = {
            "snippet": {
                "title": title[:100],  # YouTube title limit
                "description": description,
                "tags": tags or ["horror", "scary stories", "shorts"],
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        # Call the API's videos().insert method to create and upload the video.
        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        
        logger.info(f"Uploading video: {title}...")
        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Uploaded {int(status.progress() * 100)}%")

        logger.success(f"Video uploaded successfully! Video ID: {response['id']}")
        return response['id']

if __name__ == "__main__":
    # Test uploader
    # uploader = YouTubeUploader()
    # uploader.upload_video("path/to/video.mp4", "Test Video", "Test Description")
    pass
