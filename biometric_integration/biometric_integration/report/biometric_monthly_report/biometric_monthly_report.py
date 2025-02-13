import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    if not filters or not filters.get('date_range'):
        frappe.throw(_('Please select Date Range'))
    
    from_date = datetime.strptime(filters.get('date_range')[0], '%Y-%m-%d')
    to_date = datetime.strptime(filters.get('date_range')[1], '%Y-%m-%d')
    
    # Create columns for employee details
    columns = [
        {"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 200, "align": "left"},
        {"fieldname": "employee_id", "label": _("Employee ID"), "fieldtype": "Data", "width": 75, "align": "center"},
        {"fieldname": "employee_department", "label": _("Department"), "fieldtype": "Data", "width": 75, "align": "center"},
    ]
    
    # Generate date columns
    date_list = []
    current_date = from_date
    while current_date <= to_date:
        date_str = current_date.strftime('%d-%b')
        columns.append({
            "fieldname": f"duration_{current_date.strftime('%Y%m%d')}",
            "label": date_str,
            "fieldtype": "Data",
            "width": 75,
            "align": "center"
        })
        date_list.append(current_date)
        current_date += timedelta(days=1)
    
    # Add total column
    columns.append({
        "fieldname": "total_duration",
        "label": _("Total"),
        "fieldtype": "Data",
        "width": 100,
        "align": "center"
    })
    
    # Get all employees within date range with employee details based on attendance_device_id match
    employees = frappe.db.sql("""
        SELECT DISTINCT 
            bal.employee_no,
            e.name as employee,
            e.employee_name,
            e.department,
            e.attendance_device_id,
            d.name,
            d.department_name
        FROM `tabBiometric Attendance Log` bal
        LEFT JOIN `tabEmployee` e ON e.attendance_device_id = bal.employee_no
        LEFT JOIN `tabDepartment` d ON e.department = d.name        
        WHERE bal.event_date BETWEEN %(from_date)s AND %(to_date)s
    """, {
        "from_date": filters.get('date_range')[0],
        "to_date": filters.get('date_range')[1]
    }, as_dict=True)
    
    # Sort employees by their employee number
    def natural_sort_key(emp):
        try:
            return int(emp["employee_no"])
        except ValueError:
            return emp["employee_no"]
    
    employees.sort(key=natural_sort_key)
    
    data = []
    
    # Process each employee's attendance
    for employee in employees:
        row = {
            "employee_name": employee.employee_name,  # Fetching the name of the employee from Employee Doctype
            "employee_department": employee.department_name,
            "employee_id": employee.employee_no,            
        }
        total_employee_duration = timedelta()
        
        # Loop through each date in the selected range
        for date in date_list:
            date_str = date.strftime('%Y-%m-%d')
            
            # Get attendance logs for the given date
            attendance_logs = frappe.db.sql("""
                SELECT al.name
                FROM `tabBiometric Attendance Log` al
                WHERE al.employee_no = %(employee_no)s 
                AND al.event_date = %(date)s
            """, {
                "employee_no": employee.employee_no,
                "date": date_str
            }, as_dict=True)
            
            valid_durations = []
            
            for log in attendance_logs:
                punches = frappe.db.sql("""
                    SELECT at.punch_time
                    FROM `tabBiometric Attendance Punch Table` at
                    WHERE at.parent = %(log_name)s
                    ORDER BY at.punch_time
                """, {"log_name": log.name}, as_dict=True)
                
                if len(punches) % 2 == 0 and punches:
                    duration = calculate_total_duration(punches)
                    if duration.total_seconds() > 0:
                        valid_durations.append(duration)
            
            # Calculate the total duration for the day
            if valid_durations:
                total_duration = sum(valid_durations, timedelta())
                formatted_duration = format_duration(total_duration)
                total_employee_duration += total_duration
            else:
                formatted_duration = "00:00"
            
            row[f"duration_{date.strftime('%Y%m%d')}"] = formatted_duration
        
        # Format total duration for the employee
        row["total_duration"] = format_duration(total_employee_duration)
        data.append(row)
    
    # Calculate totals for each date and overall
    total_row = {
        "employee_name": "Total",
        "employee_id": len(employees),
    }
    total_minutes_all = 0
    
    for date in date_list:
        date_key = f"duration_{date.strftime('%Y%m%d')}"
        total_minutes = 0
        
        for row in data:
            if row[date_key] != "00:00":
                hours, minutes = map(int, row[date_key].split(':'))
                total_minutes += hours * 60 + minutes
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        total_row[date_key] = f"{hours:02d}:{minutes:02d}"
        total_minutes_all += total_minutes
    
    # Calculate overall total duration
    hours_all = total_minutes_all // 60
    minutes_all = total_minutes_all % 60
    total_row["total_duration"] = f"{hours_all:02d}:{minutes_all:02d}"
    
    data.append(total_row)
    
    return columns, data

def calculate_total_duration(punches):
    total_duration = timedelta()
    
    for i in range(0, len(punches) - 1, 2):
        try:
            punch_in = punches[i]["punch_time"]
            punch_out = punches[i + 1]["punch_time"]
            time_diff = punch_out - punch_in
            total_duration += time_diff
        except Exception:
            return timedelta()
    
    return total_duration

def format_duration(duration):
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if seconds > 30:
        minutes += 1
    
    return f"{hours:02d}:{minutes:02d}"
