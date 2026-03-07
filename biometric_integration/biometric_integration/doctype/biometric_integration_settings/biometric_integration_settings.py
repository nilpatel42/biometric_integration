# Copyright (c) 2025, NDV and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BiometricIntegrationSettings(Document):
    pass


import frappe
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime, timedelta


@frappe.whitelist()
def check_machine_connection():
    try:
        settings = frappe.get_doc("Biometric Integration Settings", "Biometric Integration Settings")

        if not settings.ip or not settings.username:
            return {
                "status": "error",
                "message": "Please set IP and Username first.",
                "details": "Machine credentials are incomplete.",
            }

        password = settings.get_password("password")
        if not password:
            return {
                "status": "error",
                "message": "Please set Password first.",
                "details": "Machine password is missing.",
            }

        url = f"http://{settings.ip}/ISAPI/AccessControl/AcsEvent?format=json"
        headers = {"Content-Type": "application/json"}
        now = datetime.now().strftime("%Y-%m-%d")

        payload = {
            "AcsEventCond": {
                "searchID": "connection-check",
                "searchResultPosition": 0,
                "maxResults": 1,
                "major": 5,
                "minor": 75,
                "startTime": f"{now}T00:00:00+08:00",
                "endTime": f"{now}T23:59:59+08:00",
            }
        }

        response = requests.post(
            url,
            auth=HTTPDigestAuth(settings.username, password),
            headers=headers,
            json=payload,
            verify=False,
            timeout=30,
        )

        if response.status_code == 200:
            return {
                "status": "success",
                "message": "Connection successful.",
                "details": f"Connected to {settings.ip}. Device response status: 200.",
            }

        return {
            "status": "error",
            "message": "Connection failed.",
            "details": f"HTTP {response.status_code}: {response.text}",
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": "Connection failed due to network/timeout issue.",
            "details": str(e),
        }
    except Exception as e:
        frappe.log_error(f"Machine connection check failed: {str(e)}", "Biometric Machine Connection Check")
        return {
            "status": "error",
            "message": "Connection check failed.",
            "details": str(e),
        }


def _get_employee_name_from_device(settings, password, emp_no):
    url = f"http://{settings.ip}/ISAPI/AccessControl/UserInfo/Search?format=json"
    headers = {"Content-Type": "application/json"}

    payloads = [
        {
            "UserInfoSearchCond": {
                "searchID": "1",
                "searchResultPosition": 0,
                "maxResults": 1,
                "EmployeeNoList": [{"employeeNo": str(emp_no)}],
            }
        },
        {
            "UserInfoSearchCond": {
                "searchID": "1",
                "searchResultPosition": 0,
                "maxResults": 1,
                "employeeNoList": [{"employeeNo": str(emp_no)}],
            }
        },
    ]

    for payload in payloads:
        try:
            response = requests.post(
                url,
                auth=HTTPDigestAuth(settings.username, password),
                headers=headers,
                json=payload,
                verify=False,
                timeout=30,
            )
            if response.status_code != 200:
                continue

            data = response.json()
            user_info = data.get("UserInfoSearch", {}).get("UserInfo", [])
            if user_info and user_info[0].get("name"):
                return user_info[0].get("name")
        except Exception:
            continue

    return ""


def _get_employee_name(settings, password, emp_no, name_cache=None):
    cache = name_cache if isinstance(name_cache, dict) else {}
    cache_key = str(emp_no)

    if cache_key in cache:
        return cache[cache_key]

    employee_name = frappe.db.get_value("Employee", {"attendance_device_id": emp_no}, "employee_name")
    if not employee_name and str(emp_no).isdigit():
        employee_name = frappe.db.get_value("Employee", {"attendance_device_id": int(emp_no)}, "employee_name")

    if not employee_name:
        employee_name = frappe.db.get_value("Employee", str(emp_no), "employee_name")

    if not employee_name:
        employee_name = _get_employee_name_from_device(settings, password, emp_no)

    employee_name = employee_name or ""
    cache[cache_key] = employee_name
    return employee_name


@frappe.whitelist()
def sync_attendance():
    try:
        settings = frappe.get_doc("Biometric Integration Settings", "Biometric Integration Settings")
        url = f"http://{settings.ip}/ISAPI/AccessControl/AcsEvent?format=json"
        decrypted_password = settings.get_password("password")

        start_time = datetime.strptime(settings.start_date_and_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S+08:00")
        end_time = datetime.strptime(settings.end_date_and_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S+08:00")

        headers = {"Content-Type": "application/json"}

        payload = {
            "AcsEventCond": {
                "searchID": "123456789",
                "searchResultPosition": 0,
                "maxResults": 1,
                "major": 5,
                "minor": 75,
                "startTime": start_time,
                "endTime": end_time,
            }
        }

        response = requests.post(
            url,
            auth=HTTPDigestAuth(settings.username, decrypted_password),
            headers=headers,
            json=payload,
            verify=False,
            timeout=600,
        )

        if response.status_code != 200:
            frappe.throw(f"Failed to fetch attendance logs. Status: {response.status_code}, Response: {response.text}")

        data = response.json()
        total_records = data.get("AcsEvent", {}).get("totalMatches", 0)

        if total_records == 0:
            return "No attendance records found for the given time period."

        if total_records > 1500:
            return "Too many records to process. Please reduce the date range and try again."

        count = 0
        skipped = 0
        employee_name_cache = {}
        position = 0
        batch_size = 30
        frappe.publish_progress(0, title="Attendance Sync", description="Starting attendance sync...")

        while True:
            payload["AcsEventCond"]["searchResultPosition"] = position
            payload["AcsEventCond"]["maxResults"] = batch_size

            response = requests.post(
                url,
                auth=HTTPDigestAuth(settings.username, decrypted_password),
                headers=headers,
                json=payload,
                verify=False,
                timeout=600,
            )

            if response.status_code != 200:
                frappe.publish_progress(100, title="Attendance Sync", description=f"Failed to fetch attendance logs. Status: {response.status_code}")
                frappe.throw(f"Failed to fetch attendance logs. Status: {response.status_code}, Response: {response.text}")

            data = response.json()
            events = data.get("AcsEvent", {}).get("InfoList", [])

            if not events:
                break

            for log in events:
                emp_no = log.get("employeeNoString")
                event_timestamp = log.get("time", "")
                if not emp_no or not event_timestamp:
                    continue

                event_datetime = datetime.strptime(event_timestamp[:19], "%Y-%m-%dT%H:%M:%S")
                employee_name = _get_employee_name(settings, decrypted_password, emp_no, employee_name_cache)

                attendance_log = frappe.get_all(
                    "Biometric Attendance Log",
                    filters={"employee_no": emp_no, "event_date": event_datetime.date()},
                    limit_page_length=1,
                )

                if attendance_log:
                    doc = frappe.get_doc("Biometric Attendance Log", attendance_log[0].name)
                else:
                    doc = frappe.new_doc("Biometric Attendance Log")
                    doc.employee_no = emp_no
                    doc.event_date = event_datetime.date()

                if employee_name:
                    doc.employee_name = employee_name

                existing_punch = frappe.db.sql(
                    """
                    SELECT COUNT(*)
                    FROM `tabBiometric Attendance Punch Table`
                    WHERE parent = %(parent)s
                    AND punch_time = %(punch_time)s
                    """,
                    {"parent": doc.name, "punch_time": event_datetime.time()},
                )[0][0] > 0

                if not existing_punch:
                    doc.append(
                        "punch_table",
                        {
                            "punch_time": event_datetime.time(),
                            "punch_type": "Auto",
                        },
                    )
                    try:
                        doc.save(ignore_permissions=True)
                        count += 1
                    except Exception as e:
                        print(f"Insert failed for employee {emp_no}: {str(e)}")
                        continue
                else:
                    skipped += 1

            position += len(events)
            if len(events) < batch_size:
                break

        frappe.db.commit()
        return f"{count} attendance records synced successfully. {skipped} duplicate punches skipped."
    except Exception as e:
        frappe.throw(f"Error syncing attendance: {str(e)}")


def scheduled_attendance_sync():
    try:
        settings = frappe.get_doc("Biometric Integration Settings", "Biometric Integration Settings")

        today_date = datetime.now().date()
        yesterday_date = today_date - timedelta(days=1)
        day_before_yesterday_date = today_date - timedelta(days=2)

        start_time = datetime.combine(day_before_yesterday_date, datetime.strptime("00:00:00", "%H:%M:%S").time())
        end_time = datetime.combine(yesterday_date, datetime.strptime("23:59:59", "%H:%M:%S").time())

        settings.start_date_and_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
        settings.end_date_and_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
        settings.save()

        sync_attendance()

        frappe.logger().info("Scheduled attendance sync started successfully")

        update_manual_punch_for_employee(yesterday_date)
        update_manual_punch_for_employee(day_before_yesterday_date)
        frappe.logger().info("Manual punches added for employee 105 - Maganbhai")

    except Exception as e:
        frappe.logger().error(f"Scheduled attendance sync failed: {str(e)}")
        frappe.log_error(f"Scheduled attendance sync failed: {str(e)}", "Daily Attendance Sync Error")


@frappe.whitelist()
def update_all_manual_punches():
    try:
        manual_punches = frappe.get_all("Biometric Manual Punch", fields=["employee", "punch_date", "punch_time"])

        for manual_punch in manual_punches:
            employee = manual_punch["employee"]
            punch_date = manual_punch["punch_date"]
            punch_time = manual_punch["punch_time"]

            attendance_device_id = frappe.db.get_value("Employee", employee, "attendance_device_id")
            employee_name = frappe.db.get_value("Employee", employee, "employee_name")

            if not attendance_device_id:
                continue

            if isinstance(punch_time, str):
                punch_time = punch_time.split(".")[0]
            elif isinstance(punch_time, timedelta):
                punch_time = (datetime.min + punch_time).time()

            punch_datetime = datetime.strptime(f"{punch_date} {punch_time}", "%Y-%m-%d %H:%M:%S")

            query = """
                SELECT name FROM `tabBiometric Attendance Log`
                WHERE employee_no = %s AND event_date = %s
            """
            attendance_log = frappe.db.sql(query, (attendance_device_id, punch_date), as_dict=True)

            if attendance_log:
                doc = frappe.get_doc("Biometric Attendance Log", attendance_log[0].name)
            else:
                doc = frappe.get_doc({"doctype": "Biometric Attendance Log", "employee_no": attendance_device_id, "event_date": punch_date})

            if employee_name:
                doc.employee_name = employee_name

            punches = []
            for punch in doc.get("punch_table", []):
                punch_time_value = punch.punch_time
                if isinstance(punch_time_value, str):
                    punch_time_value = datetime.strptime(punch_time_value, "%H:%M:%S").time()
                elif isinstance(punch_time_value, timedelta):
                    punch_time_value = (datetime.min + punch_time_value).time()
                punches.append({"punch_time": punch_time_value, "punch_type": punch.punch_type})

            if not any(p["punch_time"] == punch_datetime.time() for p in punches):
                punches.append({"punch_time": punch_datetime.time(), "punch_type": "Manual"})
                punches.sort(key=lambda x: x["punch_time"])

                doc.set("punch_table", [])
                for punch in punches:
                    doc.append("punch_table", punch)

                doc.save(ignore_permissions=True)
                frappe.db.commit()

        return {"status": "success", "message": "Manual punches updated successfully for all employees."}

    except frappe.ValidationError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Error updating manual punches: {str(e)}"}


@frappe.whitelist()
def update_manual_punch_for_employee(target_date):
    try:
        employee_id = "105"
        employee_no = "EMP250261"

        existing_manual_punches_query = """
            SELECT COUNT(*) as manual_punch_count
            FROM `tabBiometric Manual Punch`
            WHERE employee = %s AND punch_date = %s
        """
        existing_manual_punches = frappe.db.sql(existing_manual_punches_query, (employee_no, target_date), as_dict=True)

        if existing_manual_punches[0]["manual_punch_count"] > 0:
            return {
                "status": "skipped",
                "message": f"Manual punches already exist for employee {employee_no} on {target_date}. Skipping duplicate entry.",
            }

        query = """
            SELECT name
            FROM `tabBiometric Attendance Log`
            WHERE employee_no = %s AND event_date = %s
        """
        attendance_logs = frappe.db.sql(query, (employee_id, target_date), as_dict=True)

        punch_records = []
        for log in attendance_logs:
            attendance_doc = frappe.get_doc("Biometric Attendance Log", log["name"])
            if not attendance_doc.punch_table:
                continue
            for idx, punch in enumerate(attendance_doc.punch_table):
                punch_time = parse_time(punch.punch_time).replace(second=0, microsecond=0)
                punch_type = "IN" if idx % 2 == 0 else "OUT"
                punch_records.append((punch_time, punch_type, "system"))

        punch_records.sort(key=lambda x: x[0])

        if len(punch_records) < 2:
            return {
                "status": "skipped",
                "message": f"Not enough auto punches for employee {employee_no} on {target_date}. Need at least 2 auto punches.",
            }

        total_minutes = 0
        punch_pairs = []
        current_in = None

        for time, type_, source in punch_records:
            if type_ == "IN":
                current_in = time
            elif type_ == "OUT" and current_in is not None:
                duration = int((time - current_in).total_seconds() / 60)
                total_minutes += duration
                punch_pairs.append((current_in, time))
                current_in = None

        if total_minutes > 60:
            remaining_minutes = total_minutes - 60
            last_auto_punch_in, _last_auto_punch_out = punch_pairs[-1]
            first_manual_punch_time = last_auto_punch_in + timedelta(minutes=10)
            second_manual_punch_time = first_manual_punch_time + timedelta(minutes=remaining_minutes)

            manual_punch_1_doc = frappe.get_doc(
                {
                    "doctype": "Biometric Manual Punch",
                    "employee": employee_no,
                    "punch_date": target_date,
                    "punch_time": first_manual_punch_time.strftime("%H:%M:%S"),
                }
            )
            manual_punch_1_doc.insert(ignore_permissions=True)

            manual_punch_2_doc = frappe.get_doc(
                {
                    "doctype": "Biometric Manual Punch",
                    "employee": employee_no,
                    "punch_date": target_date,
                    "punch_time": second_manual_punch_time.strftime("%H:%M:%S"),
                }
            )
            manual_punch_2_doc.insert(ignore_permissions=True)

            frappe.db.commit()
            update_all_manual_punches()

            return {
                "status": "success",
                "message": f"Manual punches added for employee {employee_no}: {first_manual_punch_time.strftime('%H:%M:%S')} and {second_manual_punch_time.strftime('%H:%M:%S')}",
            }
        elif total_minutes == 60:
            update_all_manual_punches()
            return {
                "status": "success",
                "message": "No manual punch needed. Total working time is already 60 minutes.",
            }
        elif total_minutes < 60:
            remaining_minutes = 60 - total_minutes
            punch_in_time = "06:00:00"
            punch_in_dt = datetime.strptime(punch_in_time, "%H:%M:%S").replace(second=0, microsecond=0)
            punch_out_dt = punch_in_dt + timedelta(minutes=remaining_minutes)
            punch_out_time = punch_out_dt.strftime("%H:%M:%S")

            manual_punch_in_doc = frappe.get_doc(
                {
                    "doctype": "Biometric Manual Punch",
                    "employee": employee_no,
                    "punch_date": target_date,
                    "punch_time": punch_in_time,
                }
            )
            manual_punch_in_doc.insert(ignore_permissions=True)

            manual_punch_out_doc = frappe.get_doc(
                {
                    "doctype": "Biometric Manual Punch",
                    "employee": employee_no,
                    "punch_date": target_date,
                    "punch_time": punch_out_time,
                }
            )
            manual_punch_out_doc.insert(ignore_permissions=True)

            frappe.db.commit()
            update_all_manual_punches()

            return {
                "status": "success",
                "message": f"Manual punches added for employee {employee_no}: {punch_in_time} and {punch_out_time}",
            }
        else:
            update_all_manual_punches()
            return {
                "status": "success",
                "message": f"Cannot adjust time. Total working time is {total_minutes} minutes.",
            }

    except Exception as e:
        return {"status": "error", "message": f"Error updating manual punch: {str(e)}"}


def parse_time(time_value):
    if isinstance(time_value, str):
        return datetime.strptime(time_value, "%H:%M:%S")
    elif isinstance(time_value, timedelta):
        return datetime.min + time_value
    else:
        raise ValueError(f"Invalid time format: {time_value}")
