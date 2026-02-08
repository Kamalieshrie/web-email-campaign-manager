import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# SCOPES definition
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

def get_drive_service(service_account_json: str):
    """Get Google Drive service instance with proper scopes"""
    creds = Credentials.from_service_account_file(service_account_json)
    drive_service = build('drive', 'v3', credentials=creds)
    return drive_service

def list_spreadsheets(service_account_json: str):
    """List all spreadsheets in Google Drive"""
    try:
        drive_service = get_drive_service(service_account_json)
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            fields="files(id, name)",
            orderBy="name"
        ).execute()
        return results.get('files', [])
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def get_ws(service_account_json: str, spreadsheet_id: str, worksheet_name: str):
    # Use the filename passed from main.py
    creds = Credentials.from_service_account_file(service_account_json, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(worksheet_name)
    return ws

def sheet_to_df(ws, a1_range: str | None = None) -> pd.DataFrame:
    values = ws.get(a1_range) if a1_range else ws.get_all_values()
    if not values:
        return pd.DataFrame()
    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)
    df["_row_index"] = range(2, 2+len(rows))  # sheet row index
    return df

def ensure_cols(ws, needed=("Status", "Last Sent", "Follow-up Date", "Follow-up Time")):
    header = ws.row_values(1)
    changed = False
    for col in needed:
        if col not in header:
            header.append(col)
            changed = True
    if changed:
        ws.update("1:1", [header])
    return header

def update_status(ws, row_idx: int, status: str, ts: str):
    header = ws.row_values(1)
    
    # Ensure Status column exists and get its index
    if "Status" not in header: 
        header.append("Status")
        ws.update("1:1", [header])
        # Refresh header after update
        header = ws.row_values(1)
    
    status_col = header.index("Status") + 1
    
    # Ensure Last Sent column exists and get its index
    if "Last Sent" not in header: 
        header.append("Last Sent")
        ws.update("1:1", [header])
        # Refresh header after update
        header = ws.row_values(1)
    
    last_col = header.index("Last Sent") + 1
    
    # Update the cells
    ws.update_cell(row_idx, status_col, status)
    ws.update_cell(row_idx, last_col, ts)

def update_cell(ws, row_idx: int, col_idx: int, value: str):
    """Update a specific cell in the worksheet"""
    try:
        ws.update_cell(row_idx, col_idx, value)
        return True
    except Exception as e:
        print(f"Error updating cell at row {row_idx}, col {col_idx}: {e}")
        return False

def batch_update_cells(ws, updates):
    """Batch update multiple cells in the worksheet"""
    if not updates:
        return
    
    # Group updates by row to minimize API calls
    from collections import defaultdict
    row_updates = defaultdict(list)
    
    for row_idx, col_idx, value in updates:
        row_updates[row_idx].append((col_idx, value))
    
    # Prepare batch update
    batch_data = []
    for row_idx, cells in row_updates.items():
        for col_idx, value in cells:
            batch_data.append({
                'range': gspread.utils.rowcol_to_a1(row_idx, col_idx),
                'values': [[value]]
            })
    
    # Update in batches of 100 to avoid API limits
    for i in range(0, len(batch_data), 100):
        ws.batch_update(batch_data[i:i+100])
