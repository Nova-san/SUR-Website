import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

def export_runners_to_google_sheet(runners, sheet_id):
    SERVICE_ACCOUNT_FILE = os.path.join('credentials', 'sheets-key.json')  # adjust this path
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    data = [['Name', 'Email', 'Distance', 'Age', 'Gender', 'Shirt Size']]

    for runner in runners:
        data.append([
            runner.name,
            runner.email,
            runner.distance.label,
            runner.age,
            runner.get_gender_display(),
            runner.shirt_size
        ])

    sheet.values().update(
        spreadsheetId=sheet_id,
        range='Sheet1!A1',
        valueInputOption='RAW',
        body={'values': data}
    ).execute()
