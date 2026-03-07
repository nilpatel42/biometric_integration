# Copyright (c) 2025, NDV and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    columns = [
        {"fieldname": "employee_name", "label": _("Name"), "fieldtype": "Data", "width": 200, "align": "left"},
        {"fieldname": "employee_id", "label": _("ID"), "fieldtype": "Data", "width": 65, "align": "center"},
    ]
    
    if not filters or not filters.get('date'):
        frappe.throw(_("Please select a date."))
        
    selected_date = filters.get('date')
    formatted_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d-%b-%Y')
    
    columns[0]["label"] = formatted_date
    
    # Get employees who had manual punches that day
    present_employees = frappe.db.sql("""
        SELECT DISTINCT 
            bal.employee_no, 
            e.employee_name,
            e.attendance_device_id
        FROM `tabBiometric Attendance Log` bal
        LEFT JOIN `tabEmployee` e ON e.attendance_device_id = bal.employee_no
        WHERE bal.event_date = %(selected_date)s
        AND EXISTS (
            SELECT 1 
            FROM `tabBiometric Attendance Punch Table` at
            WHERE at.parent = bal.name
            AND at.punch_type = 'Manual'
        )
    """, {"selected_date": selected_date}, as_dict=True)
    
    def natural_sort_key(emp):
        try:
            return int(emp["attendance_device_id"])
        except ValueError:
            return emp["attendance_device_id"]
    
    # Sort employees by attendance_device_id (numeric)
    present_employees.sort(key=natural_sort_key)
    
    data = []
    max_punches = 0
    
    # Process employees with manual punches
    for employee in present_employees:
        attendance_logs = frappe.db.sql("""
            SELECT al.name, al.event_date
            FROM `tabBiometric Attendance Log` al
            WHERE al.employee_no = %(employee_no)s 
            AND al.event_date = %(selected_date)s
            ORDER BY al.event_date
        """, {"employee_no": employee.attendance_device_id, "selected_date": selected_date}, as_dict=True)
        
        for log in attendance_logs:
            # Get only manual punches
            manual_punches = frappe.db.sql("""
                SELECT at.punch_time, at.punch_type
                FROM `tabBiometric Attendance Punch Table` at
                WHERE at.parent = %(log_name)s
                AND at.punch_type = 'Manual'
                ORDER BY at.punch_time
            """, {"log_name": log.name}, as_dict=True)
            
            if not manual_punches:
                continue
                
            row_data = {
                "employee_name": employee.employee_name,
                "employee_id": employee.attendance_device_id,
            }
            
            # Format manual punches
            for i, punch in enumerate(manual_punches, 1):
                punch_field = f"punch_{i}"
                formatted_time = format_punch_with_type(punch)
                row_data[punch_field] = formatted_time
            
            max_punches = max(max_punches, len(manual_punches))
            data.append({"data": row_data})
    
    # Add punch columns
    punch_column_width = 95
    for i in range(1, max_punches + 1):
        columns.append({
            "fieldname": f"punch_{i}",
            "label": _("Manual Punch " + str(i)),
            "fieldtype": "Data",
            "width": punch_column_width,
            "align": "center"
        })
    
    # Format data for report
    formatted_data = []
    for row in data:
        row_data = row["data"].copy()
        
        for i in range(1, max_punches + 1):
            field = f"punch_{i}"
            if field not in row_data:
                row_data[field] = None
        
        formatted_data.append(row_data)
    
    # Add total row if there's data
    if formatted_data:
        total_row = {
            "employee_name": "Total Employees",
            "employee_id": len(set(row["employee_id"] for row in formatted_data)),
        }
        
        for i in range(1, max_punches + 1):
            total_row[f"punch_{i}"] = None
        
        formatted_data.append(total_row)
    
    return columns, formatted_data

def format_timedelta_to_hhmm(td):
    if not td:
        return None
    
    total_minutes = int(td.total_seconds() / 60)
    hours, mins = divmod(total_minutes, 60)
    return f"{hours:02}:{mins:02}"

def format_punch_with_type(punch):
    if not punch.get("punch_time"):
        return None
    
    time_str = format_timedelta_to_hhmm(punch["punch_time"])
    return f"{time_str} (MA)"