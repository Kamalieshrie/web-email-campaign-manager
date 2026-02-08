import os
import requests
import json
import time
from datetime import datetime, timedelta

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_scheduling():
    """Test the scheduling functionality"""
    print("Testing scheduling functionality...")
    
    # Test data - replace with your actual spreadsheet and worksheet
    test_data = {
        "spreadsheet_id": "1lVtnLkaZ4hk6u7VzY1fKTOLsMHJUxlYx2DwTnfEQeVY",
        "worksheet_name": "Sheet1",
        "row_indices": [10],  # Replace with actual row indices from your sheet
        "brand_name": "Nobel_Nest"
    }
    
    try:
        # First, check if the server is running
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print("❌ Server is not running")
            return False
        
        print("✅ Server is running")
        
        # Test scheduling endpoint
        print("\n1. Testing scheduling endpoint...")
        
        # For testing, we'll use the /schedule endpoint directly
        schedule_response = requests.post(
            f"{BASE_URL}/schedule",
            headers={"Content-Type": "application/json"},
            data=json.dumps(test_data)
        )
        
        if schedule_response.status_code == 200:
            schedule_result = schedule_response.json()
            print(f"✅ Scheduling test successful: {schedule_result['scheduled']} emails scheduled")
        else:
            print(f"❌ Scheduling test failed: {schedule_response.text}")
            return False
        
        # Check scheduled jobs
        print("\n2. Checking scheduled jobs...")
        jobs_response = requests.get(f"{BASE_URL}/scheduler/jobs")
        if jobs_response.status_code == 200:
            jobs_result = jobs_response.json()
            print(f"✅ Found {len(jobs_result['jobs'])} scheduled jobs")
            for job in jobs_result['jobs']:
                print(f"   - Job ID: {job['id']}")
                print(f"   - Next run: {job['next_run_time']}")
        else:
            print(f"❌ Failed to get scheduled jobs: {jobs_response.text}")
        
        # Test triggering scheduled emails immediately
        print("\n3. Testing immediate trigger of scheduled emails...")
        trigger_response = requests.post(f"{BASE_URL}/test_scheduled_emails")
        if trigger_response.status_code == 200:
            trigger_result = trigger_response.json()
            print(f"✅ Trigger test successful: {trigger_result['message']}")
        else:
            print(f"❌ Trigger test failed: {trigger_response.text}")
        
        # Wait a moment for jobs to execute
        print("\n4. Waiting for jobs to execute...")
        time.sleep(3)
        
        # Check jobs again to see if they were executed
        jobs_response2 = requests.get(f"{BASE_URL}/scheduler/jobs")
        if jobs_response2.status_code == 200:
            jobs_result2 = jobs_response2.json()
            print(f"✅ After execution: {len(jobs_result2['jobs'])} scheduled jobs remaining")
        else:
            print(f"❌ Failed to get scheduled jobs after execution: {jobs_response2.text}")
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        return False

def test_email_sending():
    """Test the email sending functionality"""
    print("\nTesting email sending functionality...")
    
    # Test data - replace with your actual spreadsheet and worksheet
    test_data = {
        "spreadsheet_id": "1lVtnLkaZ4hk6u7VzY1fKTOLsMHJUxlYx2DwTnfEQeVY",
        "worksheet_name": "Sheet1",
        "row_indices": [2, 3],  # Replace with actual row indices from your sheet
        "brand_name": "Test Brand"
    }
    
    try:
        # Test sending endpoint
        send_response = requests.post(
            f"{BASE_URL}/send",
            headers={"Content-Type": "application/json"},
            data=json.dumps(test_data)
        )
        
        if send_response.status_code == 200:
            send_result = send_response.json()
            print(f"✅ Email sending test successful: {send_result['sent']} emails sent")
            return True
        else:
            print(f"❌ Email sending test failed: {send_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        return False

def test_preview():
    """Test the email preview functionality"""
    print("\nTesting email preview functionality...")
    
    # Test data - replace with your actual spreadsheet and worksheet
    test_data = {
        "spreadsheet_id": "1lVtnLkaZ4hk6u7VzY1fKTOLsMHJUxlYx2DwTnfEQeVY",
        "worksheet_name": "Sheet1",
        "row_index": 2,  # Replace with actual row index from your sheet
        "brand_name": "Test Brand"
    }
    
    try:
        # Test preview endpoint
        preview_response = requests.post(
            f"{BASE_URL}/preview",
            headers={"Content-Type": "application/json"},
            data=json.dumps(test_data)
        )
        
        if preview_response.status_code == 200:
            preview_result = preview_response.json()
            print(f"✅ Email preview test successful")
            print(f"   - Subject: {preview_result['subject']}")
            print(f"   - HTML length: {len(preview_result['html'])} characters")
            return True
        else:
            print(f"❌ Email preview test failed: {preview_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        return False

def test_contacts_list():
    """Test the contacts list functionality"""
    print("\nTesting contacts list functionality...")
    
    # Test data - replace with your actual spreadsheet and worksheet
    test_data = {
        "spreadsheet_id": "1lVtnLkaZ4hk6u7VzY1fKTOLsMHJUxlYx2DwTnfEQeVY",
        "worksheet_name": "Sheet1"
    }
    
    try:
        # Test contacts list endpoint
        contacts_response = requests.post(
            f"{BASE_URL}/contacts/list",
            headers={"Content-Type": "application/json"},
            data=json.dumps(test_data)
        )
        
        if contacts_response.status_code == 200:
            contacts_result = contacts_response.json()
            print(f"✅ Contacts list test successful")
            print(f"   - Headers: {contacts_result['headers']}")
            print(f"   - Rows: {len(contacts_result['rows'])}")
            return True
        else:
            print(f"❌ Contacts list test failed: {contacts_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting comprehensive test of the email scheduling system...")
    
    # Run all tests
    tests = [
        test_contacts_list,
        test_preview,
        test_email_sending,
        test_scheduling
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY:")
    print("="*50)
    
    for i, test in enumerate(tests):
        status = "✅ PASSED" if results[i] else "❌ FAILED"
        print(f"{test.__name__}: {status}")
    
    if all(results):
        print("\n🎉 All tests passed! The system is working correctly.")
    else:
        print(f"\n⚠️  {sum(results)}/{len(results)} tests passed. Some functionality may not be working.")
