import datetime as dt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import os
import json

SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarManager:
    def __init__(self):
        self.service = self.authenticate()
        self.calendar_id = '4c7be1a48e4f6449a2e1ee189c4596235a6181e9851c71721d357ca2d8281936@group.calendar.google.com'  

    def authenticate(self):
        credentials_info = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if credentials_info is None:
            raise Exception("No se encontró la variable de entorno GOOGLE_CREDENTIALS_JSON")
        credentials_dict = json.loads(credentials_info)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        return self.build_service(credentials)

    def build_service(self, credentials):
        service = build('calendar', 'v3', credentials=credentials)
        return service

    def list_upcoming_events(self, fecha, max_results=22):

        
        date_format = f"%Y-%m-%d"
        hours = []

        date_object = dt.datetime.strptime(fecha, date_format)

        now = dt.datetime(date_object.year, date_object.month, date_object.day, 8, 0, 0, 0)
        after = dt.datetime(date_object.year, date_object.month, date_object.day, 19, 0, 0, 0)
        formated_date_time_now = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        formated_date_time_after = after.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


        events_result = self.service.events().list(
            calendarId="4c7be1a48e4f6449a2e1ee189c4596235a6181e9851c71721d357ca2d8281936@group.calendar.google.com",
            timeMin=formated_date_time_now,
            timeMax=formated_date_time_after,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            print('No hay eventos en el calendario')
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                date_time_object = datetime.strptime(start, f"%Y-%m-%dT%H:%M:%S.%z")
                horas = date_time_object.hour
                minutos = date_time_object.minute
                if str(minutos)=="0" :
                    hora = str(horas)+ ":" + str(minutos)+"0"
                else:
                    hora = str(horas)+ ":" + str(minutos)
                hours.append(hora)
                    #print(start, event['summary'], event['id'], start.hour)


        return hours    

    def create_event(self, summary, description, start_time, end_time, timezone, attendees=None):
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                 'timeZone': timezone
            },
            'end': {
                'dateTime': end_time,
                 'timeZone': timezone
            },
        }
        if attendees:
            event['attendees'] = [{"email": email} for email in attendees]

        try:
            event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            return event.get('htmlLink', '')
        except HttpError as error:
            print(f"Error al crear el evento: {error}")
            return None


    def update_event(self, event_id, summary, description, start_time, end_time, timezone, attendees=None):
        event = self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()
        
        if summary:
            event['summary'] = summary

        if start_time:
            event['start']['dateTime'] = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        if end_time:
            event['end']['dateTime'] = end_time.strftime("%Y-%m-%dT%H:%M:%S")

        updated_event = self.service.events().update(
            calendarId=self.calendar_id, eventId=event_id, body=event).execute()
        return updated_event
