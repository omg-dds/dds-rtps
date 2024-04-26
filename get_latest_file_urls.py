#!/usr/bin/python
#################################################################
# Use and redistribution is source and binary forms is permitted
# subject to the OMG-DDS INTEROPERABILITY TESTING LICENSE found
# at the following URL:
#
# https://github.com/omg-dds/dds-rtps/blob/master/LICENSE.md
#
#################################################################

import os
import sys
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleDriveClient:
    def __init__(self):
        # Load Google Drive credentials from environment variable
        self.credentials_str = os.getenv('GCP_CREDENTIAL_STR')

        # Load folder ID from environment variable
        self.folder_id = os.getenv('DRIVE_FOLDER_ID')

        # Create credentials object
        self.credentials = service_account.Credentials.from_service_account_info(
            json.loads(self.credentials_str),
            scopes=['https://www.googleapis.com/auth/drive']
        )

        # Create Google Drive service
        self.drive_service = build('drive', 'v3', credentials=self.credentials)


    def get_latest_files_url(self):
        # List to store XLSX files
        xlsx_files, zip_files = self.get_subfolder_files(self.folder_id)

        # Find the latest XLSX and ZIP files URL
        xlsx_url = None
        zip_url = None
        if xlsx_files:
            # Find the latest XLSX file based on modification time
            latest_file = max(xlsx_files, key=lambda x: x['modifiedTime'])
            xlsx_url = latest_file.get('webViewLink')
        if zip_files:
            # Find the latest zip file based on modification time
            latest_file = max(zip_files, key=lambda x: x['modifiedTime'])
            zip_url = latest_file.get('webViewLink')

        return xlsx_url, zip_url

    def get_subfolder_files(self, folder_id):
        page_token = None

        # Retrieve all files and folders within the subfolder
        while True:
            response = self.drive_service.files().list(
                q=f"'{folder_id}' in parents",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields='nextPageToken, files(id, name, webViewLink, mimeType, modifiedTime)',
                pageToken=page_token
            ).execute()

            # Extract files and folders from response
            items = response.get('files', [])

            # Check if there are more pages of results
            page_token = response.get('nextPageToken')
            if not page_token:
                break

        # List to store XLSX or ZIP files within subfolder
        xlsx_files = []
        zip_files = []

        # Iterate through files and folders
        for item in items:
            # Check if current item is a folder
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                # Recursively search for XLSX files within sub-subfolder
                subfolder_xlsx_files, subfolder_zip_files = self.get_subfolder_files(item['id'])
                if subfolder_xlsx_files:
                    xlsx_files.extend(subfolder_xlsx_files)
                if subfolder_zip_files:
                    zip_files.extend(subfolder_zip_files)
            # Check if current item is an XLSX file
            elif item['mimeType'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                # Add XLSX file to list
                xlsx_files.append(item)
            elif item['mimeType'] == 'application/zip':
                # Add ZIP file to list
                zip_files.append(item)

        # Return list of XLSX files within subfolder
        return xlsx_files, zip_files

def main():
    """This requires a filename to save the URL of the XLSX and ZIP files"""
    # Check if the file name is provided as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python get_latest_files.py <output_file>")
        sys.exit(1)

    # Get the file name from the command-line arguments
    file_name = sys.argv[1]

    if not file_name.endswith('.py'):
        print("Error: File must have .py extension")
        sys.exit(1)

    client = GoogleDriveClient()

    xlsx_file_url, zip_file_url = client.get_latest_files_url()

    with open(file_name, 'w') as file:
        if xlsx_file_url is not None:
            file.write(f'xlsx_url = \'{xlsx_file_url}\'\n')
        if zip_file_url is not None:
            file.write(f'zip_url = \'{zip_file_url}\'\n')

if __name__ == '__main__':
    main()
