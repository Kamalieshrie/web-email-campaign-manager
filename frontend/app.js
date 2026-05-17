const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : window.location.origin;
const API = (path) => `${API_BASE}${path}`;

const q = (sel) => document.querySelector(sel);
const qa = (sel) => document.querySelectorAll(sel);
let rows = [];
let headers = [];

// Add this for status checking
let statusCheckInterval = null;

// Show loading state
function showLoading(button, text = 'Loading...') {
    const originalText = button.textContent;
    button.textContent = text;
    button.disabled = true;
    return () => {
        button.textContent = originalText;
        button.disabled = false;
    };
}

// Error handler
function handleError(error, defaultMessage = 'An error occurred') {
    console.error('Error:', error);
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        alert('Cannot connect to server. Please try again.');
    } else if (error.detail) {
        alert(error.detail);
    } else {
        alert(defaultMessage);
    }
}

// Load spreadsheets from Drive
async function loadDriveSpreadsheets() {
    const resetButton = showLoading(q('#drive-access-btn'), 'Loading...');
    
    try {
        const res = await fetch(API('/drive/spreadsheets'));
        const data = await res.json();
        
        if (!res.ok) {
            throw { detail: data.detail || 'Failed to load spreadsheets' };
        }

        const spreadsheetList = q('#spreadsheet-list');
        if (data.spreadsheets && data.spreadsheets.length > 0) {
            spreadsheetList.innerHTML = data.spreadsheets.map(sheet => `
                <div class="drive-item p-3 border-b flex items-center cursor-pointer" data-id="${sheet.id}" data-name="${sheet.name}">
                    <svg class="w-5 h-5 mr-2 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/>
                    </svg>
                    <span class="truncate">${sheet.name}</span>
                </div>
            `).join('');

            // Add click event listeners to drive items
            qa('.drive-item').forEach(item => {
                item.addEventListener('click', function() {
                    const sheetId = this.getAttribute('data-id');
                    const sheetName = this.getAttribute('data-name');
                    q('#sheetId').value = sheetId;
                    q('#wsName').value = 'Sheet1'; // Default worksheet name
                    
                    // Update URL
                    const newUrl = new URL(window.location);
                    newUrl.searchParams.set('spreadsheetId', sheetId);
                    newUrl.searchParams.set('worksheetName', 'Sheet1');
                    window.history.pushState({}, '', newUrl);
                    
                    // Load the data
                    q('#loadBtn').click();
                });
            });
        } else {
            spreadsheetList.innerHTML = '<div class="p-4 text-center text-gray-500">No spreadsheets found in your Drive</div>';
        }

        q('#access-status').textContent = 'Connected to Google Drive';
        q('#connection-status').textContent = 'Connected';
        q('#drive-access-btn').innerHTML = `
            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            Access Granted
        `;
        q('#drive-access-btn').classList.remove('bg-blue-600', 'hover:bg-blue-700');
        q('#drive-access-btn').classList.add('bg-green-600', 'hover:bg-green-700');
        
    } catch (error) {
        handleError(error, 'Failed to load spreadsheets from Drive');
    } finally {
        resetButton();
    }
}

q('#drive-access-btn').addEventListener('click', loadDriveSpreadsheets);

q('#loadBtn').addEventListener('click', async () => {
    const spreadsheet_id = q('#sheetId').value.trim();
    const worksheet_name = q('#wsName').value.trim();
    
    if (!spreadsheet_id) {
        alert('Please enter a Spreadsheet ID');
        return;
    }

    const resetButton = showLoading(q('#loadBtn'), 'Loading...');
    
    try {
        const res = await fetch(API('/contacts/list'), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({spreadsheet_id, worksheet_name})
        });

        const data = await res.json();
        
        if (!res.ok) {
            throw { detail: data.detail || 'Failed to load contacts' };
        }

        headers = data.headers || [];
        rows = data.rows || [];
        renderTable();
        
    } catch (error) {
        handleError(error, 'Failed to load contacts');
    } finally {
        resetButton();
    }
});

// ... existing code ...

// Render contacts table - MODIFIED VERSION
function renderTable() {
    const div = q('#contacts');
    if (!rows.length) {
        div.innerHTML = '<p class="text-gray-500 text-center py-4">No contacts found or spreadsheet is empty.</p>';
        return;
    }
   
    // Filter out internal columns for display
    const displayHeaders = headers.filter(h => !['_row_index', 'Status', 'Last Sent', 'Follow-up Time'].includes(h));
   
    const thead = displayHeaders.map(header =>
        `<th class="px-4 py-2 border bg-gray-100 font-medium">${header}</th>`
    ).join('');
   
    const body = rows.map(row => {
        const status = row['Status'] || '';
        const isSent = status === 'SINT' || status === 'SENT';
        const statusClass = status.startsWith('PENDING') ? 'status-pending' :
                          isSent ? 'status-sent' :
                          status.includes('FAILED') ? 'status-error' :
                          status === 'QUEUE' ? 'status-queue' : 'status-queue';
        
        // Check if this row has a date set
        const hasDate = row['Follow-up Date'] && row['Follow-up Date'] !== 'dd-mm-yyyy';
        const rowClass = hasDate ? 'has-date' : '';
       
        const cells = displayHeaders.map(header => {
            if (header === 'Follow-up Date') {
                // Hide date input for sent emails
                if (isSent) {
                    return `<td class="px-4 py-2 border date-cell text-gray-400">
                        ${(row[header] || '').toString()}
                    </td>`;
                }
                return `<td class="px-4 py-2 border date-cell">
                    <input type="text" class="date-input flatpickr-input"
                           data-idx="${row._row_index}"
                           value="${(row[header] || '').toString()}"
                           placeholder="dd-mm-yyyy">
                </td>`;
            }
            return `<td class="px-4 py-2 border">${(row[header] || '').toString()}</td>`;
        }).join('');
       
        // MODIFIED: Time picker using Flatpickr instead of native time input
        // Hide time input for sent emails
        const timeCell = isSent ? 
            `<td class="px-4 py-2 border time-cell text-gray-400">
                ${(row['Follow-up Time'] || '09:00').toString()}
            </td>` :
            `<td class="px-4 py-2 border time-cell">
                <input type="text" class="time-input flatpickr-input"
                       data-idx="${row._row_index}"
                       value="${(row['Follow-up Time'] || '09:00').toString()}"
                       placeholder="HH:MM">
            </td>`;
       
        return `<tr class="sheet-row ${rowClass}">
            <td class="px-4 py-2 border">
                <input type="checkbox" class="sel" data-idx="${row._row_index}" ${isSent ? 'disabled' : ''}>
            </td>
            ${cells}
            ${timeCell}
            <td class="px-4 py-2 border">
                <span class="px-2 py-1 rounded text-xs ${statusClass}">${status || 'QUEUE'}</span>
            </td>
        </tr>`;
    }).join('');

    div.innerHTML = `
        <div class="overflow-x-auto">
            <table class="min-w-full border-collapse border">
                <thead>
                    <tr>
                        <th class="px-4 py-2 border bg-gray-100 font-medium">Select</th>
                        ${thead}
                        <th class="px-4 py-2 border bg-gray-100 font-medium">Time</th>
                        <th class="px-4 py-2 border bg-gray-100 font-medium">Status</th>
                    </tr>
                </thead>
                <tbody>${body}</tbody>
            </table>
        </div>
        <div class="mt-2 text-sm text-gray-600">
            <p>Found ${rows.length} contacts.</p>
            <p>${rows.filter(r => r['Status'] === 'SINT' || r['Status'] === 'SENT').length} already sent.</p>
            <p>${rows.filter(r => r['Status']?.startsWith('PENDING')).length} scheduled.</p>
            <p>${rows.filter(r => r['Follow-up Date'] && r['Follow-up Date'] !== 'dd-mm-yyyy').length} have dates set.</p>
        </div>
    `;
   
    // Initialize date pickers for each row (only for non-sent emails)
    document.querySelectorAll('.date-input').forEach(input => {
        flatpickr(input, {
            dateFormat: "d-m-Y",
            allowInput: true,
            onChange: function(selectedDates, dateStr, instance) {
                const rowIndex = parseInt(instance.input.dataset.idx, 10);
                const newDate = dateStr;
                console.log(`Date changed for row ${rowIndex}: ${newDate}`);
                
                // Update the row styling based on whether a date is set
                const row = document.querySelector(`tr input[data-idx="${rowIndex}"]`).closest('tr');
                if (newDate && newDate !== 'dd-mm-yyyy') {
                    row.classList.add('has-date');
                } else {
                    row.classList.remove('has-date');
                }
                
                updateFollowUpDateForRow(rowIndex, newDate);
            }
        });
    });
   
    // MODIFIED: Initialize time pickers for each row using Flatpickr (only for non-sent emails)
    document.querySelectorAll('.time-input').forEach(input => {
        flatpickr(input, {
            enableTime: true,
            noCalendar: true,
            dateFormat: "H:i",
            time_24hr: true,
            allowInput: true,
            minuteIncrement: 5,
            onChange: function(selectedDates, dateStr, instance) {
                const rowIndex = parseInt(instance.input.dataset.idx, 10);
                const newTime = dateStr;
                console.log(`Time changed for row ${rowIndex}: ${newTime}`);
                updateFollowUpTimeForRow(rowIndex, newTime);
            }
        });
    });
}

// ... rest of the code remains the same ...
   
    // MODIFIED: Initialize time pickers for each row using Flatpickr
    document.querySelectorAll('.time-input').forEach(input => {
        flatpickr(input, {
            enableTime: true,
            noCalendar: true,
            dateFormat: "H:i",
            time_24hr: true,
            allowInput: true,
            minuteIncrement: 5,
            onChange: function(selectedDates, dateStr, instance) {
                const rowIndex = parseInt(instance.input.dataset.idx, 10);
                const newTime = dateStr;
                console.log(`Time changed for row ${rowIndex}: ${newTime}`);
                updateFollowUpTimeForRow(rowIndex, newTime);
            }
        });
    });
    // Initialize time pickers for each row using Flatpickr
    document.querySelectorAll('.time-input').forEach(input => {
        flatpickr(input, {
            enableTime: true,
            noCalendar: true,
            dateFormat: "H:i", 
            time_24hr: true,
            allowInput: true,
            minuteIncrement: 5,
            onChange: function(selectedDates, dateStr, instance) {
                const rowIndex = parseInt(instance.input.dataset.idx, 10);
                const newTime = dateStr;
                console.log(`Time changed for row ${rowIndex}: ${newTime}`);
                updateFollowUpTimeForRow(rowIndex, newTime);
            }
        });
    });

// Update follow-up date for a single row
async function updateFollowUpDateForRow(rowIndex, followUpDate) {
    const spreadsheet_id = q('#sheetId').value.trim();
    const worksheet_name = q('#wsName').value.trim();
   
    if (!followUpDate) {
        console.log("No date provided for update");
        return;
    }

    console.log(`Updating date for row ${rowIndex} to ${followUpDate}`);
   
    try {
        const res = await fetch(`${API_BASE}/update_followup_dates`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                spreadsheet_id,
                worksheet_name,
                row_indices: [rowIndex],
                follow_up_date: followUpDate
            })
        });

        if (!res.ok) {
            const errorData = await res.json();
            throw { detail: errorData.detail || 'Failed to update follow-up date' };
        }

        const data = await res.json();
        console.log(`Date updated successfully: ${JSON.stringify(data)}`);

        // Update the local data to reflect the change
        const row = rows.find(r => r._row_index === rowIndex);
        if (row) {
            row['Follow-up Date'] = followUpDate;
        }
       
    } catch (error) {
        console.error('Update error:', error);
        handleError(error, 'Failed to update follow-up date');
    }
}

// Update follow-up time for a single row
async function updateFollowUpTimeForRow(rowIndex, followUpTime) {
    const spreadsheet_id = q('#sheetId').value.trim();
    const worksheet_name = q('#wsName').value.trim();
   
    if (!followUpTime) {
        console.log("No time provided for update");
        return;
    }

    console.log(`Updating time for row ${rowIndex} to ${followUpTime}`);
   
    try {
        // First, ensure the Follow-up Time column exists
        await ensureTimeColumnExists(spreadsheet_id, worksheet_name);
       
        // Then update the time value
        const res = await fetch(`${API_BASE}/update_followup_time`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                spreadsheet_id,
                worksheet_name,
                row_indices: [rowIndex],
                follow_up_time: followUpTime
            })
        });

        if (!res.ok) {
            const errorData = await res.json();
            throw { detail: errorData.detail || 'Failed to update follow-up time' };
        }

        const data = await res.json();
        console.log(`Time updated successfully: ${JSON.stringify(data)}`);

        // Update the local data to reflect the change
        const row = rows.find(r => r._row_index === rowIndex);
        if (row) {
            row['Follow-up Time'] = followUpTime;
        }
       
    } catch (error) {
        console.error('Update error:', error);
        handleError(error, 'Failed to update follow-up time');
    }
}

// Ensure the Follow-up Time column exists in the sheet
async function ensureTimeColumnExists(spreadsheet_id, worksheet_name) {
    try {
        const res = await fetch(`${API_BASE}/ensure_time_column`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                spreadsheet_id,
                worksheet_name
            })
        });

        if (!res.ok) {
            const errorData = await res.json();
            throw { detail: errorData.detail || 'Failed to ensure time column exists' };
        }

        return true;
    } catch (error) {
        console.error('Ensure column error:', error);
        throw error;
    }
}

q('#previewBtn').addEventListener('click', async () => {
    const spreadsheet_id = q('#sheetId').value.trim();
    const worksheet_name = q('#wsName').value.trim();
    const brand_name = q('#brand').value.trim();
    const sel = [...document.querySelectorAll('.sel:checked')];
    
    if (!sel.length) {
        alert('Please select at least one row to preview');
        return;
    }

    const resetButton = showLoading(q('#previewBtn'), 'Generating Preview...');
    
    try {
        const row_index = parseInt(sel[0].dataset.idx, 10);
        const res = await fetch(API('/preview'), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({spreadsheet_id, worksheet_name, row_index, brand_name})
        });

        const data = await res.json();
        
        if (!res.ok) {
            throw { detail: data.detail || 'Preview generation failed' };
        }

        q('#preview').innerHTML = `
            <div class="bg-white p-4 rounded-lg shadow">
                <div class="font-semibold mb-2 text-gray-700">Subject:</div>
                <div class="p-3 border border-gray-300 rounded bg-gray-50 mb-4 font-mono text-sm">${data.subject}</div>
                <div class="font-semibold mb-2 text-gray-700">Body Preview:</div>
                <div id="email-preview-container" class="w-full h-96 border border-gray-300 rounded bg-white overflow-auto" style="min-height: 400px;"></div>
            </div>
        `;
        
        // Insert the HTML content directly into the div
        const previewContainer = document.getElementById('email-preview-container');
        previewContainer.innerHTML = data.html;
        
        resetButton();
        
    } catch (error) {
        console.error("Preview Error:", error);
        handleError(error, 'Failed to generate preview');
        resetButton();
    }
});

q('#sendBtn').addEventListener('click', async () => {
    const spreadsheet_id = q('#sheetId').value.trim();
    const worksheet_name = q('#wsName').value.trim();
    const brand_name = q('#brand').value.trim();
    const sel = [...document.querySelectorAll('.sel:checked')].map(x => parseInt(x.dataset.idx, 10));
    
    if (!sel.length) {
        alert('Please select at least one row to send');
        return;
    }

    // Filter out already sent emails
    const unsentRows = sel.filter(idx => {
        const row = rows.find(r => r._row_index === idx);
        return row && row['Status'] !== 'SENT';
    });

    if (unsentRows.length === 0) {
        alert('All selected emails have already been sent');
        return;
    }

    if (!confirm(`Send emails to ${unsentRows.length} selected contacts?`)) return;

    const resetButton = showLoading(q('#sendBtn'), 'Sending...');
    
    try {
        const res = await fetch(API('/send'), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                spreadsheet_id,
                worksheet_name,
                row_indices: unsentRows,
                brand_name
            })
        });

        const data = await res.json();
        
        if (!res.ok) {
            throw { detail: data.detail || 'Failed to send emails' };
        }

        alert(` Successfully sent ${data.sent} emails!`);
        
        // Reload the table to show updated status
        q('#loadBtn').click();
        
    } catch (error) {
        handleError(error, 'Failed to send emails');
    } finally {
        resetButton();
    }
});

// Add some initial help text
document.addEventListener('DOMContentLoaded', function() {
    const helpText = `
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h3 class="font-semibold text-blue-800 mb-2">How to use:</h3>
            <ol class="list-decimal list-inside text-sm text-blue-700 space-y-1">
                <li>Enter your Google Sheet ID</li>
                <li>Click "Load Contacts" to fetch data</li>
                <li>Select rows and preview emails</li>
                <li>Click "Send Selected" to send emails</li>
            </ol>
        </div>
    `;
    q('#contacts').insertAdjacentHTML('beforebegin', helpText);
    
    // Check for URL parameters on page load
    const urlParams = new URLSearchParams(window.location.search);
    const spreadsheetId = urlParams.get('spreadsheetId');
    const worksheetName = urlParams.get('worksheetName');
    
    if (spreadsheetId) {
        q('#sheetId').value = spreadsheetId;
        if (worksheetName) {
            q('#wsName').value = worksheetName;
        }
        // Auto-load the data after a short delay
        setTimeout(() => {
            q('#loadBtn').click();
        }, 500);
    }
});
