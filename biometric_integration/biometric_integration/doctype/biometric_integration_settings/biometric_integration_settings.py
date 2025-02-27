# Copyright (c) 2025, NDV and contributors
# For license information, please see license.txt

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
        
        # Determine which day to process
        current_date = datetime.now().date()
        current_day = current_date.weekday()  # Monday is 0, Sunday is 6
        
        # If today is Thursday (3), process Tuesday's data (2 days ago)
        # Otherwise process yesterday's data
        if current_day == 3:  # Thursday
            target_date = (datetime.now() + timedelta(days=-2)).date()  # Tuesday (skip Wednesday)
        else:
            target_date = (datetime.now() + timedelta(days=-1)).date()  # Yesterday
        
        # First, check if employee 105 has any auto punches for the target date
        check_query = """
            SELECT COUNT(*) as punch_count
            FROM `tabBiometric Attendance Log`
            WHERE employee_no = %s AND event_date = %s
        """
        check_result = frappe.db.sql(check_query, (employee_id, target_date), as_dict=True)
        
        has_auto_punches = check_result[0]['punch_count'] > 0 if check_result else False
        
        if not has_auto_punches:
            # If no auto punches exist for employee 105, skip the 1-hour calculation
            update_all_manual_punches()
            return {
                'status': 'success',
                'message': f"No auto punches found for employee {employee_no} on {target_date}. Skipping 1-hour calculation."
            }
        
        # Lists to store punch times with their type (IN/OUT)
        punch_records = []
        
        # Get system punches
        query = """
            SELECT name 
            FROM `tabBiometric Attendance Log`
            WHERE employee_no = %s AND event_date = %s
        """
        attendance_logs = frappe.db.sql(query, (employee_id, target_date), as_dict=True)
        
        # Add system punches to the list
        for log in attendance_logs:
            attendance_doc = frappe.get_doc('Biometric Attendance Log', log['name'])
            if not attendance_doc.punch_table:
                continue
            for idx, punch in enumerate(attendance_doc.punch_table):
                punch_time = parse_time(punch.punch_time).replace(second=0, microsecond=0)
                punch_type = 'IN' if idx % 2 == 0 else 'OUT'  # Alternate IN/OUT
                punch_records.append((punch_time, punch_type, 'system'))
                
        # Get manual punches
        manual_query = """
            SELECT punch_time 
            FROM `tabBiometric Manual Punch`
            WHERE employee = %s AND punch_date = %s
        """
        manual_punches = frappe.db.sql(manual_query, (employee_no, target_date), as_dict=True)
        
        # Add manual punches to the list
        for idx, punch in enumerate(manual_punches):
            punch_time = parse_time(punch.punch_time).replace(second=0, microsecond=0)
            punch_type = 'IN' if idx % 2 == 0 else 'OUT'  # Alternate IN/OUT
            punch_records.append((punch_time, punch_type, 'manual'))
            
        # Sort all punches by time
        punch_records.sort(key=lambda x: x[0])
        
        # Debug print all punch times with their types
        print("\nAll punch records in order:")
        for time, type_, source in punch_records:
            print(f"{time.strftime('%H:%M:%S')} ({type_}) - {source}")
            
        # Calculate total time and store punch pairs
        total_minutes = 0
        punch_pairs = []
        current_in = None
        
        for time, type_, source in punch_records:
            if type_ == 'IN':
                current_in = time
            elif type_ == 'OUT' and current_in is not None:
                duration = int((time - current_in).total_seconds() / 60)
                total_minutes += duration
                punch_pairs.append((current_in, time))
                print(f"Duration: {current_in.strftime('%H:%M:%S')} - {time.strftime('%H:%M:%S')} = {duration} minutes")
                current_in = None
                
        print(f"\nTotal Minutes: {total_minutes}")
        
        # If total time is exactly 60 minutes, just update and exit
        if total_minutes == 60:
            update_all_manual_punches()
            return {
                'status': 'success',
                'message': f"No manual punch needed. Total working time is already 60 minutes."
            }
            
        # If total time is less than 1 hour (60 minutes), add manual punches
        if total_minutes < 60:
            remaining_minutes = 60 - total_minutes
            
            # Fixed first punch at 08:00
            punch_in_time = "08:00:00"
            punch_in_dt = datetime.strptime(punch_in_time, '%H:%M:%S').replace(second=0, microsecond=0)
            punch_out_dt = punch_in_dt + timedelta(minutes=remaining_minutes)
            punch_out_time = punch_out_dt.strftime('%H:%M:%S')
            
            # Add manual punches
            manual_punch_in_doc = frappe.get_doc({
                'doctype': 'Biometric Manual Punch',
                'employee': employee_no,
                'punch_date': target_date,
                'punch_time': punch_in_time,
            })
            manual_punch_in_doc.insert(ignore_permissions=True)
            
            manual_punch_out_doc = frappe.get_doc({
                'doctype': 'Biometric Manual Punch',
                'employee': employee_no,
                'punch_date': target_date,
                'punch_time': punch_out_time,
            })
            manual_punch_out_doc.insert(ignore_permissions=True)
            
            frappe.db.commit()
            update_all_manual_punches()
            
            return {
                'status': 'success',
                'message': f"Manual punches added for employee {employee_no}: {punch_in_time} and {punch_out_time}"
            }
            
        # If total time is more than 1 hour, find longest duration to break
        elif total_minutes > 60:
            excess_minutes = total_minutes - 60
            
            # Find the longest punch pair
            longest_punch = max(punch_pairs, key=lambda x: (x[1] - x[0]).total_seconds())
            punch_in_dt, punch_out_dt = longest_punch
            punch_duration = int((punch_out_dt - punch_in_dt).total_seconds() / 60)
            
            print(f"\nLongest punch: {punch_in_dt.strftime('%H:%M:%S')} - {punch_out_dt.strftime('%H:%M:%S')} = {punch_duration} minutes")
            
            if punch_duration > excess_minutes:
                # Calculate break duration to achieve 60 minutes total
                break_duration = excess_minutes
                
                # Create manual punch in the middle of the longest punch
                mid_point = punch_in_dt + (punch_out_dt - punch_in_dt) / 2
                manual_punch_in_dt = mid_point - timedelta(minutes=break_duration // 2)
                manual_punch_out_dt = manual_punch_in_dt + timedelta(minutes=break_duration)
                
                print(f"Adding break: {manual_punch_in_dt.strftime('%H:%M:%S')} - {manual_punch_out_dt.strftime('%H:%M:%S')}")
                
                # Add manual punches
                manual_punch_in_doc = frappe.get_doc({
                    'doctype': 'Biometric Manual Punch',
                    'employee': employee_no,
                    'punch_date': target_date,
                    'punch_time': manual_punch_in_dt.strftime('%H:%M:%S'),
                })
                manual_punch_in_doc.insert(ignore_permissions=True)
                
                manual_punch_out_doc = frappe.get_doc({
                    'doctype': 'Biometric Manual Punch',
                    'employee': employee_no,
                    'punch_date': target_date,
                    'punch_time': manual_punch_out_dt.strftime('%H:%M:%S'),
                })
                manual_punch_out_doc.insert(ignore_permissions=True)
                
                frappe.db.commit()
                update_all_manual_punches()
                
                return {
                    'status': 'success',
                    'message': f"Manual punches added at {manual_punch_in_dt.strftime('%H:%M')} and {manual_punch_out_dt.strftime('%H:%M')}, reducing time to 60 minutes."
                }
                
        update_all_manual_punches()
        return {
            'status': 'success',
            'message': f"No manual punch needed. Total working time is {total_minutes} minutes."
        }
        
    except Exception as e:
        return {'status': 'error', 'message': f"Error updating manual punch: {str(e)}"}
        
def parse_time(time_value):
    """Helper function to parse time strings or timedelta objects into datetime objects."""
    if isinstance(time_value, str):
        return datetime.strptime(time_value, '%H:%M:%S')
    elif isinstance(time_value, timedelta):
        return datetime.min + time_value
    else:
        raise ValueError(f"Invalid time format: {time_value}")