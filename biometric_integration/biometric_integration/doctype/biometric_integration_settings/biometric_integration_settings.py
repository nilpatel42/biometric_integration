# Copyright (c) 2025, NDV and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document

class BiometricIntegrationSettings(Document):
	pass

import frappe
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime
import json

@frappe.whitelist()
def sync_attendance():
    try:
        # Fetch settings
        settings = frappe.get_doc('Biometric Integration Settings', 'Biometric Integration Settings')
        url = f"http://{settings.ip}/ISAPI/AccessControl/AcsEvent?format=json"
        decrypted_password = settings.get_password('password')

        # Convert Frappe datetime to device format (YYYY-MM-DDThh:mm:ss+08:00)
        start_time = datetime.strptime(settings.start_date_and_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S+08:00')
        end_time = datetime.strptime(settings.end_date_and_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S+08:00')

        headers = {"Content-Type": "application/json"}

        # Initial fetch to determine total records
        payload = {
            "AcsEventCond": {
                "searchID": "123456789",
                "searchResultPosition": 0,
                "maxResults": 1,
                "major": 5,
                "minor": 75,
                "startTime": start_time,
                "endTime": end_time
            }
        }

        response = requests.post(
            url,
            auth=HTTPDigestAuth(settings.username, decrypted_password),
            headers=headers,
            json=payload,
            verify=False,
            timeout=600  # Set a higher timeout value (e.g., 600 seconds)
        )

        if response.status_code != 200:
            frappe.throw(f"Failed to fetch attendance logs. Status: {response.status_code}, Response: {response.text}")

        data = response.json()
        total_records = data.get("AcsEvent", {}).get("totalMatches", 0)

        if total_records == 0:
            return "No attendance records found for the given time period."
        
        if total_records > 1500:
            return "Too many records to process. Please reduce the date range and try again."

        count = 0  # To count successfully synced records
        skipped = 0  # To count skipped duplicates
        position = 0
        batch_size = 30
        frappe.publish_progress(0, title='Attendance Sync', description='Starting attendance sync...')

        while True:
            payload["AcsEventCond"]["searchResultPosition"] = position
            payload["AcsEventCond"]["maxResults"] = batch_size

            response = requests.post(
                url,
                auth=HTTPDigestAuth(settings.username, decrypted_password),
                headers=headers,
                json=payload,
                verify=False,
                timeout=600  # Set a higher timeout value (e.g., 600 seconds)
            )

            if response.status_code != 200:
                frappe.publish_progress(100, title='Attendance Sync', description=f"Failed to fetch attendance logs. Status: {response.status_code}")
                frappe.throw(f"Failed to fetch attendance logs. Status: {response.status_code}, Response: {response.text}")

            data = response.json()
            events = data.get("AcsEvent", {}).get("InfoList", [])

            if not events:
                break

            for log in events:
                emp_no = log.get('employeeNoString')
                event_timestamp = log.get('time', '')
                if not emp_no or not event_timestamp:
                    continue
                # Convert device time format to Frappe format
                event_datetime = datetime.strptime(event_timestamp[:19], '%Y-%m-%dT%H:%M:%S')
                # Create or get Attendance Log doc for employee and date
                attendance_log = frappe.get_all('Biometric Attendance Log', filters={
                    'employee_no': emp_no,
                    'event_date': event_datetime.date()
                }, limit_page_length=1)
                if attendance_log:
                    doc = frappe.get_doc('Biometric Attendance Log', attendance_log[0].name)
                else:
                    doc = frappe.new_doc("Biometric Attendance Log")
                    doc.employee_no = emp_no
                    doc.event_date = event_datetime.date()
                # Check if the punch time already exists in the child table (punch_table) for the same employee and date
                existing_punch = frappe.db.sql("""
                    SELECT COUNT(*) 
                    FROM `tabBiometric Attendance Punch Table`
                    WHERE parent = %(parent)s
                    AND punch_time = %(punch_time)s
                """, {
                    "parent": doc.name,
                    "punch_time": event_datetime.time()
                })[0][0] > 0
                if not existing_punch:
                    # Create a new punch entry in the child table with punch_type set to "Auto"
                    doc.append('punch_table', {
                        'punch_time': event_datetime.time(),  # Only time part
                        'punch_type': 'Auto'  # Set punch type as Auto for device punches
                    })
                    try:
                        doc.save(ignore_permissions=True)
                        count += 1
                    except Exception as e:
                        print(f"Insert failed for employee {emp_no}: {str(e)}")
                        continue
                else:
                    skipped += 1
                    print(f"Punch for employee {emp_no} at {event_datetime.time()} already exists.")
            position += len(events)

            progress = (position / total_records) * 100
            frappe.publish_progress(progress, title='Attendance Sync', description=f"Processed {position} of {total_records} records so far...")

            if len(events) < batch_size:
                break

        frappe.db.commit()
        frappe.publish_progress(100, title='Attendance Sync', description=f"{count} attendance records synced successfully. {skipped} duplicate punches skipped.")
        return f"{count} attendance records synced successfully. {skipped} duplicate punches skipped."
    except Exception as e:
        frappe.publish_progress(100, title='Attendance Sync', description=f"Error syncing attendance: {str(e)}")
        frappe.throw(f"Error syncing attendance: {str(e)}")


def scheduled_attendance_sync():
    try:
        # Get the settings
        settings = frappe.get_doc('Biometric Integration Settings', 'Biometric Integration Settings')
        
        # Set the time range for today
        today = datetime.now().date()
        start_time = datetime.combine(today, datetime.strptime("00:00:00", "%H:%M:%S").time())
        end_time = datetime.combine(today, datetime.strptime("23:59:59", "%H:%M:%S").time())
        
        # Update the settings with today's date range
        settings.start_date_and_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
        settings.end_date_and_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
        settings.save()
        
        # Call the sync function
        frappe.enqueue(
            'biometric_attendance_sync.biometric_attendance_sync.doctype.biometric_attendance_log.biometric_attendance_sync.sync_attendance',
            queue='long',
            timeout=1500
        )
        
        frappe.logger().info("Scheduled attendance sync started successfully")
        
    except Exception as e:
        frappe.logger().error(f"Scheduled attendance sync failed: {str(e)}")
        frappe.log_error(f"Scheduled attendance sync failed: {str(e)}", "Daily Attendance Sync Error")
