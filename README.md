# Web App MVP: Google Sheets → Email

A minimal full‑stack web application to load contacts from Google Sheets, preview templated emails, and send them via SMTP — with status written back to the sheet.

## Structure
- `backend/` FastAPI API
- `frontend/` Static HTML/JS (Tailwind)

## Backend Setup
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit values
# place your Google service account key as service_account.json in this folder
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend
Open `frontend/index.html` in the browser. It assumes backend at `http://localhost:8000`.

## Using the App
1. Enter your Spreadsheet ID and Worksheet Name.
2. Click **Load Contacts**.
3. Select rows, click **Preview Selected** to see subject/body.
4. Click **Send Selected** to send emails. Status & timestamp update in your sheet.

## Notes
- Configure SMTP in `backend/.env`.
- Service account must have Editor access to the sheet.
- Extend templates in `backend/templates/`.
- Add auth & rate limiting before production.


# google spread sheet url 
 - https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit










# Google Sheets Email Campaign Manager

A full-stack application that turns a Google Sheet into a powerful, personalized email marketing platform. Send bulk emails with personalization, scheduling, and tracking—all from your browser.

##  What It Does

- **Connect to Google Sheets:** Pull contacts directly from your spreadsheet.
- **Personalize at Scale:** Automatically generates emails using each contact's name and past purchase history.
- **Schedule Emails:** Set a "Follow-up Date" for each contact to control when they receive emails.
- **Track Everything:** Automatically marks contacts as "SENT" and records the date in your sheet.
- **Simple Dashboard:** A clean web interface to manage everything without writing a single line of code.

##  Tech Stack

*   **Backend (API):** Python, FastAPI
*   **Frontend (UI):** Vanilla JavaScript, HTML, Tailwind CSS
*   **Email Templates:** Jinja2
*   **Data Source:** Google Sheets API
*   **Email Delivery:** SMTP (works with Gmail, Outlook, SendGrid, etc.)

##  Prerequisites

Before you begin, ensure you have the following:

1.  **Python 3.8+** installed on your system.
2.  A Google Cloud Platform (GCP) project with the **Google Sheets API** and **Google Drive API** enabled.
3.  A **Service Account Key** (JSON file) from your GCP project to allow the app to access your spreadsheets.
4.  An email account (Gmail, Outlook, etc.) and its **SMTP credentials** (app password for Gmail).

##  Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd sheets-email-app
    ```

2.  **Create a Virtual Environment and Install Dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Environment Configuration:**
    Create a `.env` file in the root directory and add your configuration:

    ```ini
    # Google Service Account Credentials
    GOOGLE_SERVICE_ACCOUNT_JSON="path/to/your-service-account-key.json"

    # Email SMTP Settings (Example for Gmail)
    SMTP_HOST="smtp.gmail.com"
    SMTP_PORT="587"
    SMTP_USERNAME="your.email@gmail.com"
    SMTP_PASSWORD="your-app-password" # NOT your regular Gmail password
    FROM_EMAIL="Your Brand Name <your.email@gmail.com>"

    # App Configuration
    BRAND_NAME="Your Awesome Brand"
    ```

4.  **Prepare Your Google Sheet:**
    *   Create a sheet with columns like `Email`, `Name`, `Last Purchase`, etc.
    *   Share your Google Sheet with the **client email** found inside your Service Account JSON file. Grant **Editor** access.

##  How to Run

1.  **Start the Backend Server:**
    ```bash
    python main.py
    ```
    The API will start on `http://localhost:8000`.

2.  **Open the Frontend:**
    *   Simply open the `index.html` file in your web browser.
    *   *or* Serve it with a local server (e.g., `python -m http.server 3000`) and go to `http://localhost:3000`.

3.  **Use the Application:**
    *   Click **"Access Google Drive"** to see your spreadsheets.
    *   Click on a spreadsheet to load it.
    *   Select contacts, preview emails, and hit **"Send Selected"**.

##  How to Use

1.  **Load Contacts:** Enter your Sheet ID and Worksheet name, then click "Load Contacts."
2.  **Preview:** Select a row and click "Preview Selected" to see the personalized email.
3.  **Schedule (Optional):** Use the date picker to set a "Follow-up Date" for selected contacts. Emails will only be sent *on or after* this date.
4.  **Send:** Select the contacts you want to email and click "Send Selected." The app will filter out already-sent contacts and ask for confirmation.

##  API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | GET | Check if the backend server is running. |
| `/drive/spreadsheets` | GET | Fetch a list of all available Google Sheets. |
| `/contacts/list` | POST | Load contact data from a specified worksheet. |
| `/preview` | POST | Generate a preview of a personalized email for a given contact. |
| `/send` | POST | Send emails to a list of selected contacts. |
| `/update_followup_dates`| POST | Bulk update the "Follow-up Date" for selected contacts. |
