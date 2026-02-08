import os
import re
import requests
import smtplib
import dns.resolver
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from mailer import validate_email_dns

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from loguru import logger
import logging
from email_validator import validate_email, EmailNotValidError

# Add these imports for scheduling
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import atexit
import json

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.info("App started successfully")

from jinja2 import Environment, FileSystemLoader, select_autoescape

# === IMPORTS FOR SHEETS AND MAILER ===
from sheets import get_ws, sheet_to_df, ensure_cols, update_status, list_spreadsheets, update_cell
from mailer import send_email_smtp

import time
from functools import lru_cache

# Add this function
def rate_limit_delay(seconds=2.5):
    """Add delay to avoid Google Sheets API quota limits"""
    time.sleep(seconds)

# Cache worksheet access
@lru_cache(maxsize=32)
def get_ws_cached(service_account_json: str, spreadsheet_id: str, worksheet_name: str):
    """Cached version of get_ws to reduce API calls"""
    return get_ws(service_account_json, spreadsheet_id, worksheet_name)

load_dotenv()

# SCOPES configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "webemailapp-backend-258b8739233a.json")
BRAND_NAME = os.getenv("BRAND_NAME", "Your Brand")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)
SEND_WINDOW_START_HOUR = int(os.getenv("SEND_WINDOW_START_HOUR", "9"))
SEND_WINDOW_END_HOUR = int(os.getenv("SEND_WINDOW_END_HOUR", "20"))

# Get allowed origins from environment variable
allow_origins_list = os.getenv("ALLOW_ORIGINS", "http://localhost:3000, http://127.0.0.1:3000").split(",")

app = FastAPI(title="Sheets → Email")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now to fix CORS issues
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# Jinja2 env
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR),
                  autoescape=select_autoescape(["html","xml"]),
                  trim_blocks=True, lstrip_blocks=True)
subject_t = env.get_template("subject.j2")
body_t = env.get_template("body.html.j2")

class ListReq(BaseModel):
    spreadsheet_id: str
    worksheet_name: str
    a1_range: Optional[str] = None

class PreviewReq(BaseModel):
    spreadsheet_id: str
    worksheet_name: str
    row_index: int
    brand_name: Optional[str] = None

class SendReq(BaseModel):
    spreadsheet_id: str
    worksheet_name: str
    row_indices: List[int]
    brand_name: Optional[str] = None

class UpdateFollowUpDateReq(BaseModel):
    spreadsheet_id: str
    worksheet_name: str
    row_indices: List[int]
    follow_up_date: str

class UpdateFollowUpTimeReq(BaseModel):
    spreadsheet_id: str
    worksheet_name: str
    row_indices: List[int]
    follow_up_time: str

class ScheduleReq(BaseModel):
    spreadsheet_id: str
    worksheet_name: str
    row_indices: List[int]
    brand_name: Optional[str] = None

def get_email_from_row(row, headers):
    """Try to find email in various possible columns"""
    # Common email column names
    email_columns = ['Email', 'email', 'E-Mail', 'e-mail', 'Email Address', 'Mail', 'Name']
    
    for col in email_columns:
        if col in row:
            email = (row.get(col) or "").strip()
            if email and '@' in email and '.' in email:
                return email
    
    # If no standard email column found, try to find any column that looks like email
    for key, value in row.items():
        if value and '@' in str(value) and '.' in str(value):
            potential_email = str(value).strip()
            # Basic email validation
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', potential_email):
                return potential_email
    
    return ""

def validate_email_address(email):
    """Comprehensive email validation with better error reporting"""
    try:
        # Basic format validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return False, "Invalid email format"
        
        # Use email-validator library for more thorough validation
        try:
            valid = validate_email(email)
            email = valid.email  # Normalized email
            return True, "Valid email format"
        except EmailNotValidError as e:
            return False, f"Invalid email: {str(e)}"
            
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def send_scheduled_email(scheduled_data: Dict):
    """Function to send scheduled emails"""
    try:
        # Extract data
        spreadsheet_id = scheduled_data['spreadsheet_id']
        worksheet_name = scheduled_data['worksheet_name']
        row_index = scheduled_data['row_index']
        email = scheduled_data['email']
        subject = scheduled_data['subject']
        html = scheduled_data['html']
        
        # Send the email
        send_email_smtp(SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL, email, subject, html)
        
        # Update status in the sheet - USE CACHED VERSION
        ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, spreadsheet_id, worksheet_name)
        rate_limit_delay()  # Add delay here too
        update_status(ws, row_index, "SENT", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        logger.info(f"Successfully sent scheduled email to {email}")
    except Exception as e:
        logger.error(f"Failed to send scheduled email: {e}")
        # Update status to indicate failure
        try:
            ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, spreadsheet_id, worksheet_name)
            rate_limit_delay()  # Add delay here too
            update_status(ws, row_index, f"FAILED: {str(e)}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as update_error:
            logger.error(f"Failed to update status for scheduled email: {update_error}")

@app.get("/health")
def health():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}

@app.get("/drive/spreadsheets")
def get_drive_spreadsheets():
    """Get list of all spreadsheets in Drive"""
    try:
        spreadsheets = list_spreadsheets(GOOGLE_SERVICE_ACCOUNT_JSON)
        return {"spreadsheets": spreadsheets}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(400, f"Drive error: {e}")

@app.post("/contacts/list")
def contacts_list(req: ListReq):
    try:
        ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, req.spreadsheet_id, req.worksheet_name)
        rate_limit_delay()
        ensure_cols(ws, ("Status", "Last Sent", "Follow-up Date", "Follow-up Time"))
        df = sheet_to_df(ws, req.a1_range)
        return {"headers": list(df.columns), "rows": df.fillna("").to_dict(orient="records")}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(400, f"Sheets error: {e}")

@app.post("/update_followup_dates")
def update_followup_dates(req: UpdateFollowUpDateReq):
    try:
        ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, req.spreadsheet_id, req.worksheet_name)
        rate_limit_delay()
        ensure_cols(ws, ("Follow-up Date",))
        
        # Get header row to find column index
        header = ws.row_values(1)
        if "Follow-up Date" not in header:
            # Add the column if it doesn't exist
            header.append("Follow-up Date")
            ws.update("1:1", [header])
            # Refresh header after adding the column
            header = ws.row_values(1)
        
        follow_up_col = header.index("Follow-up Date") + 1  # +1 because sheets are 1-indexed
        
        # Update the cells for all selected rows
        updated_count = 0
        for row_index in req.row_indices:
            # The row_index from frontend is the actual row number in the sheet
            update_cell(ws, row_index, follow_up_col, req.follow_up_date)
            updated_count += 1
        
        return {"success": True, "updated": updated_count, "message": "Follow-up dates updated successfully"}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(400, f"Error updating follow-up dates: {e}")

@app.post("/update_followup_time")
def update_followup_time(req: UpdateFollowUpTimeReq):
    try:
        ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, req.spreadsheet_id, req.worksheet_name)
        rate_limit_delay()
        ensure_cols(ws, ("Follow-up Time",))
        
        # Get header row to find column index
        header = ws.row_values(1)
        if "Follow-up Time" not in header:
            # Add the column if it doesn't exist
            header.append("Follow-up Time")
            ws.update("1:1", [header])
            # Refresh header after adding the column
            header = ws.row_values(1)
        
        follow_up_time_col = header.index("Follow-up Time") + 1  # +1 because sheets are 1-indexed
        
        # Update the cells for all selected rows
        updated_count = 0
        for row_index in req.row_indices:
            # The row_index from frontend is the actual row number in the sheet
            update_cell(ws, row_index, follow_up_time_col, req.follow_up_time)
            updated_count += 1
        
        return {"success": True, "updated": updated_count, "message": "Follow-up times updated successfully"}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(400, f"Error updating follow-up times: {e}")

@app.post("/ensure_time_column")
def ensure_time_column(req: ListReq):
    try:
        ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, req.spreadsheet_id, req.worksheet_name)
        rate_limit_delay()
        ensure_cols(ws, ("Follow-up Time",))
        return {"success": True, "message": "Follow-up Time column ensured"}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(400, f"Error ensuring time column: {e}")

def ctx_from_row(row: Dict[str,Any], brand_name: str):
    email = get_email_from_row(row, list(row.keys()))
    name = (row.get("Name") or "").strip()
    first = name.split(" ")[0] if name else ""
    last_purchase = (row.get("Last Purchase") or "").strip() or None
    follow_up_date = (row.get("Follow-up Date") or "").strip() or None
    
    return {
        "first_name": first or "there",
        "name": name or "there",
        "last_purchase": last_purchase,
        "follow_up_date": follow_up_date,
        "brand_name": brand_name,
    }

@app.post("/preview")
def preview(req: PreviewReq):
    try:
        ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, req.spreadsheet_id, req.worksheet_name)
        rate_limit_delay()
        df = sheet_to_df(ws)
        row = next((r for r in df.to_dict(orient="records") if r.get("_row_index")==req.row_index), None)
        if not row: raise ValueError("Row not found")
        brand = req.brand_name or BRAND_NAME
        ctx = ctx_from_row(row, brand)
        subject = subject_t.render(**ctx)
        html = body_t.render(**ctx)
        return {"subject": subject, "html": html, "ctx": ctx}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(400, f"Preview error: {e}")

@app.post("/schedule")
def schedule_emails(req: ScheduleReq):
    """Schedule emails for future delivery at specified time"""
    try:
        ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, req.spreadsheet_id, req.worksheet_name)
        rate_limit_delay()
        ensure_cols(ws, ("Status", "Last Sent", "Follow-up Date", "Follow-up Time"))
        df = sheet_to_df(ws)
        brand = req.brand_name or BRAND_NAME

        # Maps rows by index for quick lookup
        by_idx = {r["_row_index"]: r for r in df.to_dict(orient="records")}

        scheduled_count = 0
        for idx in req.row_indices:
            row = by_idx.get(idx)
            if not row: continue
            
            email = get_email_from_row(row, list(row.keys()))
            
            if not email:
                update_status(ws, int(idx), "FAILED: No email address found", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                continue
                
            # Basic format validation only
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                update_status(ws, int(idx), "FAILED: Invalid email format", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                continue
                
            status = (row.get("Status") or "").strip().upper()
            if status and status not in ("QUEUE",""):
                # already processed
                continue

            # Check if this is a future date
            fud = (row.get("Follow-up Date") or "").strip()
            fut = (row.get("Follow-up Time") or "09:00").strip()  # Default to 9:00 AM if not specified
            
            if not fud:
                continue
                
            try:
                # Parse the date and time
                if "-" in fud:
                    day, month, year = fud.split("-")
                    if len(day) == 2 and len(month) == 2 and len(year) == 4:
                        # dd-mm-yyyy format
                        scheduled_datetime = datetime.strptime(f"{fud} {fut}", "%d-%m-%Y %H:%M")
                    else:
                        # yyyy-mm-dd format
                        scheduled_datetime = datetime.strptime(f"{fud} {fut}", "%Y-%m-%d %H:%M")
                elif "/" in fud:
                    # mm/dd/yyyy format
                    scheduled_datetime = datetime.strptime(f"{fud} {fut}", "%m/%d/%Y %H:%M")
                else:
                    # Try to parse as is
                    scheduled_datetime = datetime.strptime(f"{fud} {fut}", "%Y-%m-%d %H:%M")
                
                # If it's a future date, schedule it
                if scheduled_datetime > datetime.now():
                    ctx = ctx_from_row(row, brand)
                    subject = subject_t.render(**ctx)
                    html = body_t.render(**ctx)
                    
                    # Schedule the email
                    scheduled_data = {
                        "spreadsheet_id": req.spreadsheet_id,
                        "worksheet_name": req.worksheet_name,
                        "row_index": int(idx),
                        "brand_name": brand,
                        "email": email,
                        "subject": subject,
                        "html": html,
                        "scheduled_time": scheduled_datetime.isoformat()
                    }
                    
                    # Add to scheduler
                    scheduler.add_job(
                        send_scheduled_email,
                        trigger=DateTrigger(run_date=scheduled_datetime),
                        args=[scheduled_data],
                        id=f"email_{req.spreadsheet_id}_{idx}_{scheduled_datetime.timestamp()}"
                    )
                    
                    # Update status to Pending with scheduled date and time
                    update_status(ws, int(idx), f"PENDING: {scheduled_datetime.strftime('%d-%m-%Y %H:%M')}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    scheduled_count += 1
                    
            except Exception as e:
                logger.warning(f"Could not parse or schedule email for row {idx}: {e}")
                continue

        return {"scheduled": scheduled_count}
    except Exception as e:
        logger.exception(e)
        raise HTTPException(400, f"Scheduling error: {e}")

@app.post("/send")
def send(req: SendReq):
    try:
        # Use cached version instead of get_ws
        ws = get_ws_cached(GOOGLE_SERVICE_ACCOUNT_JSON, req.spreadsheet_id, req.worksheet_name)
        
        # Add delay to avoid quota issues
        rate_limit_delay()
        
        ensure_cols(ws, ("Status", "Last Sent", "Follow-up Date", "Follow-up Time"))
        df = sheet_to_df(ws)
        brand = req.brand_name or BRAND_NAME

        # Maps rows by index for quick lookup
        by_idx = {r["_row_index"]: r for r in df.to_dict(orient="records")}

        count = 0
        for idx in req.row_indices:
            row = by_idx.get(idx)
            if not row: continue
            
            email = get_email_from_row(row, list(row.keys()))
            
            if not email:
                update_status(ws, int(idx), "FAILED: No email address found", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                continue
                
            # Basic format validation only
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                update_status(ws, int(idx), "FAILED: Invalid email format", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                continue
                
            status = (row.get("Status") or "").strip().upper()
            if status and status not in ("QUEUE",""):
                # already processed
                continue

            # Follow-Up Date and Time gating - skip if it's a future datetime
            fud = (row.get("Follow-up Date") or "").strip()
            fut = (row.get("Follow-up Time") or "09:00").strip()
            
            if fud:
                try:
                    # Parse date and time
                    if "-" in fud:
                        day, month, year = fud.split("-")
                        if len(day) == 2 and len(month) == 2 and len(year) == 4:
                            # dd-mm-yyyy format
                            scheduled_datetime = datetime.strptime(f"{fud} {fut}", "%d-%m-%Y %H:%M")
                        else:
                            # yyyy-mm-dd format
                            scheduled_datetime = datetime.strptime(f"{fud} {fut}", "%Y-%m-%d %H:%M")
                    elif "/" in fud:
                        # mm/dd/yyyy format
                        scheduled_datetime = datetime.strptime(f"{fud} {fut}", "%m/%d/%Y %H:%M")
                    else:
                        # Try to parse as is
                        scheduled_datetime = datetime.strptime(f"{fud} {fut}", "%Y-%m-%d %H:%M")
                    
                    if scheduled_datetime > datetime.now():
                        continue
                except Exception as e:
                    logger.warning(f"Could not parse follow-up date/time '{fud} {fut}': {e}")
                    # Continue with sending if date parsing fails

            ctx = ctx_from_row(row, brand)
            subject = subject_t.render(**ctx)
            html = body_t.render(**ctx)

            # send email with comprehensive error handling
            try:
                # First validate the email thoroughly
                is_valid, validation_msg = validate_email_address(email)
                
                if not is_valid:
                    # Invalid format
                    update_status(ws, int(idx), "FAILED: invalid mail id", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    continue
                
                # Additional DNS validation for deliverability
                domain_valid, domain_msg = validate_email_dns(email)
                
                if not domain_valid:
                    # Valid format but address not found
                    update_status(ws, int(idx), f"FAILED: valid(address not found - {domain_msg})", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    continue
                
                # Email is valid and deliverable - send it
                send_email_smtp(SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL, email, subject, html)
                update_status(ws, int(idx), "SENT", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                count += 1
                
            except smtplib.SMTPRecipientsRefused as e:
                # Handle specific recipient refusal
                error_msg = str(e).lower()
                if 'address not found' in error_msg or 'user unknown' in error_msg:
                    update_status(ws, int(idx), "FAILED: valid(address not found)", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    update_status(ws, int(idx), f"FAILED: SMTP error - {str(e)}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            except smtplib.SMTPResponseException as e:
                update_status(ws, int(idx), f"FAILED: SMTP error - {str(e)}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            except smtplib.SMTPException as e:
                update_status(ws, int(idx), f"FAILED: SMTP error - {str(e)}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                update_status(ws, int(idx), f"FAILED: unexpected error - {str(e)}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return {"sent": count}
        
    except Exception as e:
        logger.exception(e)
        raise HTTPException(400, f"Send error: {e}")

# Endpoint to view scheduled jobs
@app.get("/scheduler/jobs")
def get_scheduled_jobs():
    """Get list of all scheduled jobs"""
    jobs = scheduler.get_jobs()
    job_list = []
    for job in jobs:
        job_list.append({
            "id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "args": job.args
        })
    return {"jobs": job_list}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
