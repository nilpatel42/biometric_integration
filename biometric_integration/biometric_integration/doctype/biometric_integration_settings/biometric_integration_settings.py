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


from datetime import datetime, timedelta
import frappe

def scheduled_attendance_sync():
    try:
        # Get the settings
        settings = frappe.get_doc('Biometric Integration Settings', 'Biometric Integration Settings')
        
        # Calculate yesterday's date
        today_date = datetime.now().date()
        yesterday_date = today_date - timedelta(days=1)
        
        # Initialize variables for start_time and end_time
        start_time = None
        end_time = None
        
        # Check if today is Thursday and the machine was off on Wednesday
        if today_date.weekday() == 3:  # 3 corresponds to Thursday
            # Fetch logs for Tuesday (two days ago)
            tuesday_date = yesterday_date - timedelta(days=1)
            start_time = datetime.combine(tuesday_date, datetime.strptime("00:00:00", "%H:%M:%S").time())
            end_time = datetime.combine(tuesday_date, datetime.strptime("23:59:59", "%H:%M:%S").time())
        else:
            # For all other days, fetch data for yesterday
            start_time = datetime.combine(yesterday_date, datetime.strptime("00:00:00", "%H:%M:%S").time())
            end_time = datetime.combine(yesterday_date, datetime.strptime("23:59:59", "%H:%M:%S").time())
        
        # Update the settings with the calculated date range
        settings.start_date_and_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
        settings.end_date_and_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
        settings.save()
        
        # Sync attendance
        sync_attendance()
        
        frappe.logger().info("Scheduled attendance sync started successfully")
        
        # Add manual punches for employee 105 - Maganbhai
        update_manual_punch_for_employee()
        frappe.logger().info("Manual punches added for employee 105 - Maganbhai")
    
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


@frappe.whitelist()
def update_manual_punch_for_employee():
    try:
        # Define employee details
        employee_id = "105"
        employee_no = "EMP250261"
        yesterday_date = (datetime.now() + timedelta(days=-1)).date()

        # Query to get system punches
        query = """
            SELECT name 
            FROM `tabBiometric Attendance Log`
            WHERE employee_no = %s AND event_date = %s
        """
        attendance_logs = frappe.db.sql(query, (employee_id, yesterday_date), as_dict=True)

        if not attendance_logs:
            return {'status': 'error', 'message': f"No attendance log found for employee {employee_no} on {yesterday_date}"}

        # Calculate total time from system punches
        total_minutes = 0
        for log in attendance_logs:
            attendance_doc = frappe.get_doc('Biometric Attendance Log', log['name'])
            if not attendance_doc.punch_table:
                continue

            sorted_punches = sorted(attendance_doc.punch_table, key=lambda p: p.punch_time)
            for i in range(0, len(sorted_punches) - 1, 2):
                punch_in = sorted_punches[i].punch_time
                punch_out = sorted_punches[i + 1].punch_time

                # Convert punch times to timedelta or datetime objects
                if isinstance(punch_in, str):
                    punch_in_dt = datetime.strptime(punch_in, '%H:%M:%S')
                elif isinstance(punch_in, timedelta):
                    punch_in_dt = datetime.min + punch_in
                else:
                    raise ValueError("Invalid punch_in format")

                if isinstance(punch_out, str):
                    punch_out_dt = datetime.strptime(punch_out, '%H:%M:%S')
                elif isinstance(punch_out, timedelta):
                    punch_out_dt = datetime.min + punch_out
                else:
                    raise ValueError("Invalid punch_out format")

                # Calculate duration in minutes (copied from report script)
                duration = int((punch_out_dt - punch_in_dt).total_seconds() / 60)
                total_minutes += duration

        # Query to get existing manual punches
        manual_query = """
            SELECT punch_time 
            FROM `tabBiometric Manual Punch`
            WHERE employee = %s AND punch_date = %s
        """
        manual_punches = frappe.db.sql(manual_query, (employee_no, yesterday_date), as_dict=True)

        # Add time from existing manual punches
        for i in range(0, len(manual_punches) - 1, 2):
            punch_in = manual_punches[i].punch_time
            punch_out = manual_punches[i + 1].punch_time

            # Convert punch times to timedelta or datetime objects
            if isinstance(punch_in, str):
                punch_in_dt = datetime.strptime(punch_in, '%H:%M:%S')
            elif isinstance(punch_in, timedelta):
                punch_in_dt = datetime.min + punch_in
            else:
                raise ValueError("Invalid punch_in format")

            if isinstance(punch_out, str):
                punch_out_dt = datetime.strptime(punch_out, '%H:%M:%S')
            elif isinstance(punch_out, timedelta):
                punch_out_dt = datetime.min + punch_out
            else:
                raise ValueError("Invalid punch_out format")

            # Calculate duration in minutes (copied from report script)
            duration = int((punch_out_dt - punch_in_dt).total_seconds() / 60)
            total_minutes += duration

        # Debugging: Print total minutes
        print(f"Total Minutes from Existing Punches: {total_minutes}")

        # If total time is less than 1 hour (60 minutes), add manual punches
        if total_minutes < 60:
            remaining_minutes = 60 - total_minutes

            # Fixed first punch at 08:00
            punch_in_time = "08:00:00"

            # Calculate second punch based on remaining minutes
            punch_in_dt = datetime.strptime(punch_in_time, '%H:%M:%S')
            punch_out_dt = punch_in_dt + timedelta(minutes=remaining_minutes)
            punch_out_time = punch_out_dt.strftime('%H:%M:%S')

            # Add first manual punch (fixed at 08:00)
            manual_punch_in_doc = frappe.get_doc({
                'doctype': 'Biometric Manual Punch',
                'employee': employee_no,
                'punch_date': yesterday_date,
                'punch_time': punch_in_time,
            })
            manual_punch_in_doc.insert(ignore_permissions=True)

            # Add second manual punch (calculated based on remaining minutes)
            manual_punch_out_doc = frappe.get_doc({
                'doctype': 'Biometric Manual Punch',
                'employee': employee_no,
                'punch_date': yesterday_date,
                'punch_time': punch_out_time,
            })
            manual_punch_out_doc.insert(ignore_permissions=True)

            frappe.db.commit()
            update_all_manual_punches()

            return {
                'status': 'success',
                'message': f"Manual punches added for employee {employee_no}: {punch_in_time} and {punch_out_time}"
            }

        return {
            'status': 'success',
            'message': f"No manual punch needed. Total time is already 1 hour."
        }

    except Exception as e:
        return {'status': 'error', 'message': f"Error updating manual punch: {str(e)}"}