# Web Email Campaign Manager

Owner and Creator: Kamalie Shrie Rajendran
GitHub: github.com/Kamalieshrie
Created: 2026
All Rights Reserved. Copyright 2026 Kamalie Shrie Rajendran.

---

## What It Does

Web Email Campaign Manager is a full-stack application that connects
Google Sheets to a personalized email marketing platform. It allows
bulk email sending with personalization, scheduling, and tracking
directly from the browser.

---

## Key Features

- Connect to Google Sheets and pull contacts directly
- Personalize emails using each contact's name and purchase history
- Schedule emails using a Follow-up Date per contact
- Track sent status and record timestamps back to the sheet
- Clean web dashboard to manage everything without code

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python with FastAPI |
| Frontend | Vanilla JavaScript and HTML with Tailwind CSS |
| Email Templates | Jinja2 |
| Data Source | Google Sheets API |
| Email Delivery | SMTP (Gmail, Outlook, SendGrid) |

---

## Project Structure

web-email-campaign-manager/
    backend/
        main.py
        templates/
        requirements.txt
        .env.example
    frontend/
        index.html

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| /health | GET | Check backend server status |
| /drive/spreadsheets | GET | Fetch all available Google Sheets |
| /contacts/list | POST | Load contacts from a worksheet |
| /preview | POST | Preview personalized email for a contact |
| /send | POST | Send emails to selected contacts |
| /update_followup_dates | POST | Bulk update Follow-up Dates |

---

## Ownership and Licensing

This project, Web Email Campaign Manager, was independently conceived,
designed, built, and deployed by Kamalie Shrie Rajendran.

Original repository: github.com/Kamalieshrie/web-email-campaign-manager
Created: 2026

Copyright 2026 Kamalie Shrie Rajendran. All Rights Reserved.

Any use, integration, or deployment of this project by third parties
requires explicit written permission from the owner.

See LICENSE file for full terms.

---

Built independently by Kamalie Shrie Rajendran
github.com/Kamalieshrie
