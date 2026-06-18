from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_PATH = "token.json"
TIMEZONE = "Asia/Tashkent"


def _get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def create_event(title, task_date, task_time):
    service = _get_service()

    if task_time:
        start = datetime.strptime(f"{task_date} {task_time}", "%Y-%m-%d %H:%M")
        end = start + timedelta(hours=1)
        body = {
            "summary": title,
            "start": {"dateTime": start.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end.isoformat(), "timeZone": TIMEZONE},
        }
    else:
        body = {
            "summary": title,
            "start": {"date": task_date},
            "end": {"date": task_date},
        }

    event = service.events().insert(calendarId="primary", body=body).execute()
    return event["id"], event.get("htmlLink")
