# Copyright (c) 2025, NDV and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document

class BiometricIntegrationSettings(Document):
	pass

import frappe
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime, timedelta
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



@frappe.whitelist()
def update_all_manual_punches():
    try:
        # Fetch all manual punches
        manual_punches = frappe.get_all('Biometric Manual Punch', fields=['employee', 'punch_date', 'punch_time'])

        # Loop through each manual punch document
        for manual_punch in manual_punches:
            employee = manual_punch['employee']
            punch_date = manual_punch['punch_date']
            punch_time = manual_punch['punch_time']

            # Fetch employee's attendance device ID
            attendance_device_id = frappe.db.get_value('Employee', employee, 'attendance_device_id')
            
            if not attendance_device_id:
                continue  # Skip if attendance device ID is not found

            # Handle punch_time if it's a string or timedelta object
            if isinstance(punch_time, str):
                punch_time = punch_time.split('.')[0]  # Remove fractional seconds if any
            elif isinstance(punch_time, timedelta):
                # Convert timedelta to time object
                punch_time = (datetime.min + punch_time).time()

            punch_datetime = datetime.strptime(f"{punch_date} {punch_time}", '%Y-%m-%d %H:%M:%S')

            # Query for the Biometric Attendance Log
            query = """
                SELECT name FROM `tabBiometric Attendance Log`
                WHERE employee_no = %s AND event_date = %s
            """
            attendance_log = frappe.db.sql(query, (attendance_device_id, punch_date), as_dict=True)

            if attendance_log:
                doc = frappe.get_doc('Biometric Attendance Log', attendance_log[0].name)
            else:
                doc = frappe.get_doc({'doctype': 'Biometric Attendance Log', 'employee_no': attendance_device_id, 'event_date': punch_date})

            punches = []
            for punch in doc.get('punch_table', []):
                punch_time_value = punch.punch_time
                if isinstance(punch_time_value, str):
                    punch_time_value = datetime.strptime(punch_time_value, '%H:%M:%S').time()
                elif isinstance(punch_time_value, timedelta):
                    punch_time_value = (datetime.min + punch_time_value).time()
                punches.append({'punch_time': punch_time_value, 'punch_type': punch.punch_type})

            # Check if the manual punch time already exists
            if not any(p['punch_time'] == punch_datetime.time() for p in punches):
                # If not, add the manual punch
                punches.append({'punch_time': punch_datetime.time(), 'punch_type': 'Manual'})
                punches.sort(key=lambda x: x['punch_time'])

                # Update the punch_table with the new punches
                doc.set('punch_table', [])
                for punch in punches:
                    doc.append('punch_table', punch)

                doc.save(ignore_permissions=True)
                frappe.db.commit()

        return {'status': 'success', 'message': "Manual punches updated successfully for all employees."}

    except frappe.ValidationError as e:
        return {'status': 'error', 'message': str(e)}
    except Exception as e:
        return {'status': 'error', 'message': f"Error updating manual punches: {str(e)}"}




from datetime import datetime, timedelta
import frappe

@frappe.whitelist()
def update_manual_punch_for_employee(employee_id):
    try:
        # Employee ID set as Magan (direct text input)
        employee_no = "EMP250261"

        # Get today's date
        yesterday_date = (datetime.now() + timedelta(days=-1)).date()

        # Fetch the Biometric Attendance Log for the employee for today's date
        query = """
            SELECT name FROM `tabBiometric Attendance Log`
            WHERE employee_no = %s AND event_date = %s
        """
        
        attendance_logs = frappe.db.sql(query, (employee_id, yesterday_date), as_dict=True)

        if not attendance_logs:
            return {'status': 'error', 'message': f"No attendance log found for employee {employee_no} on {yesterday_date}"}

        total_seconds = 0
        punch_in = None
        punch_out = None

        # Iterate through each attendance log to calculate total punch time from punch_table (child table)
        for log in attendance_logs:
            attendance_doc = frappe.get_doc('Biometric Attendance Log', log['name'])

            # Ensure punch_table exists and is not empty
            if not attendance_doc.punch_table:
                return {'status': 'error', 'message': f"No punches found in the attendance log for employee {employee_no} on {yesterday_date}"}

            # Sort punches by punch_time to ensure correct time calculation
            sorted_punches = sorted(attendance_doc.punch_table, key=lambda p: p.punch_time)

            # Process each punch, ensuring 'in' and 'out' punches are paired
            for i in range(1, len(sorted_punches)):
                punch_in = sorted_punches[i-1].punch_time
                punch_out = sorted_punches[i].punch_time

                # If punch_time is in timedelta, convert it to string
                if isinstance(punch_in, timedelta):
                    punch_in = str(datetime.min + punch_in).split(' ')[1]
                if isinstance(punch_out, timedelta):
                    punch_out = str(datetime.min + punch_out).split(' ')[1]

                # Convert both punch times to datetime objects
                punch_in = datetime.strptime(punch_in, '%H:%M:%S')
                punch_out = datetime.strptime(punch_out, '%H:%M:%S')

                # Add the difference to total_seconds
                total_seconds += (punch_out - punch_in).total_seconds()

        # If the total punch time is less than 1 hour (3600 seconds), calculate the remaining time
        remaining_seconds = 3600 - total_seconds

        if remaining_seconds > 0:
            # First (in) punch time is set to "08:00:00"
            punch_in_time = "08:00:00"  # Fixed punch-in time as 08:00:00
            
            # Calculate the punch out time based on the remaining seconds
            punch_in_datetime = datetime.strptime(punch_in_time, '%H:%M:%S')
            punch_out_datetime = punch_in_datetime + timedelta(seconds=remaining_seconds)
            punch_out_time = punch_out_datetime.strftime('%H:%M:%S')

            # Add the first (in) punch
            manual_punch_in_doc = frappe.get_doc({
                'doctype': 'Biometric Manual Punch',
                'employee': employee_no,  # Employee ID (105)
                'punch_date': yesterday_date,  # Today's date for the punch
                'punch_time': punch_in_time,  # Punch-in time set to 08:00:00
            })
            manual_punch_in_doc.insert(ignore_permissions=True)

            # Add the second (out) punch to complete the 1-hour total
            manual_punch_out_doc = frappe.get_doc({
                'doctype': 'Biometric Manual Punch',
                'employee': employee_no,  # Employee ID (105)
                'punch_date': yesterday_date,  # Today's date for the punch
                'punch_time': punch_out_time,  # Calculated punch out time
            })
            manual_punch_out_doc.insert(ignore_permissions=True)

            frappe.db.commit()

            # Run the update_all_manual_punches function after adding the manual punches
            update_all_manual_punches()

            return {'status': 'success', 'message': f"Manual punches added for employee {employee_no}: {punch_in_time} and {punch_out_time}"}

        return {'status': 'success', 'message': f"No manual punch needed for Maganbhai. Total time is already 1 hour."}

    except frappe.ValidationError as e:
        return {'status': 'error', 'message': str(e)}
    except Exception as e:
        return {'status': 'error', 'message': f"Error updating manual punch: {str(e)}"}