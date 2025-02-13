import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    columns = [
        {"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 200, "align": "left"},
        {"fieldname": "employee_id", "label": _("Employee ID"), "fieldtype": "Data", "width": 65, "align": "center"},
        {"fieldname": "total_duration", "label": _("Total Duration (HH:MM)"), "fieldtype": "Data", "width": 75, "align": "center"}
    ]
    
    if not filters or not filters.get('date'):
        frappe.throw(_("Please select a date."))
        
    selected_date = filters.get('date')
    formatted_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%d-%b-%Y')
    
    columns[0]["label"] = formatted_date
    
    # Get all active employees with attendance device IDs
    all_active_employees = frappe.db.sql("""
        SELECT 
            employee_name,
            attendance_device_id
        FROM 
            tabEmployee
        WHERE 
            status = 'Active'
            AND attendance_device_id IS NOT NULL
            AND attendance_device_id != ''
        ORDER BY 
            attendance_device_id
    """, as_dict=True)
    
    # Get employees who had attendance that day
    present_employees = frappe.db.sql("""
        SELECT DISTINCT e.employee_no, e.employee_name
        FROM `tabBiometric Attendance Log` e
        WHERE e.event_date = %(selected_date)s
    """, {"selected_date": selected_date}, as_dict=True)
    
    # Create a set of present employee IDs for faster lookup
    present_employee_ids = {emp.employee_no for emp in present_employees}
    
    def natural_sort_key(emp):
        try:
            return int(emp["employee_no"])
        except ValueError:
            return emp["employee_no"]
    
    present_employees.sort(key=natural_sort_key)
    
    data = []
    max_punches = 0
    valid_minutes = []
    
    # Process present employees
    for employee in present_employees:
        attendance_logs = frappe.db.sql("""
            SELECT al.name, al.event_date
            FROM `tabBiometric Attendance Log` al
            WHERE al.employee_no = %(employee_no)s AND al.event_date = %(selected_date)s
            ORDER BY al.event_date
        """, {"employee_no": employee.employee_no, "selected_date": selected_date}, as_dict=True)
        
        for log in attendance_logs:
            punches = frappe.db.sql("""
                SELECT at.punch_time, at.punch_type
                FROM `tabBiometric Attendance Punch Table` at
                WHERE at.parent = %(log_name)s
                ORDER BY at.punch_time
            """, {"log_name": log.name}, as_dict=True)
            
            row_data = {}
            row_indicators = {}
            
            row_data["employee_name"] = employee.employee_name
            row_data["employee_id"] = employee.employee_no
            
            if len(punches) % 2 != 0:
                total_duration_formatted = "Check"
            else:
                total_minutes = calculate_total_minutes(punches)
                total_duration_formatted = format_minutes_to_hhmm(total_minutes)
                if total_duration_formatted != "Check":
                    valid_minutes.append(total_minutes)
            
            row_data["total_duration"] = total_duration_formatted
            
            for i, punch in enumerate(punches, 1):
                punch_field = f"punch_{i}"
                formatted_time = format_punch_with_type(punch)
                
                if punch.get("punch_type") == "Manual":
                    row_data[punch_field] = formatted_time
                    row_indicators[punch_field] = "red"
                else:
                    row_data[punch_field] = formatted_time
            
            max_punches = max(max_punches, len(punches))
            data.append({
                "data": row_data,
                "indicators": row_indicators
            })
    
    # Add punch columns
    punch_column_width = 95
    for i in range(1, max_punches + 1):
        columns.append({
            "fieldname": f"punch_{i}",
            "label": _("Punch " + str(i)),
            "fieldtype": "Data",
            "width": punch_column_width,
            "align": "center"
        })
    
    # Format data for report
    formatted_data = []
    for row in data:
        row_data = row["data"].copy()
        
        for field, color in row["indicators"].items():
            row_data[field] = frappe.render_template(
                '''<span style="color: {{ color }}">{{ value }}</span>''',
                {"value": row_data[field], "color": color}
            )
        
        for i in range(1, max_punches + 1):
            field = f"punch_{i}"
            if field not in row_data:
                row_data[field] = None
        
        formatted_data.append(row_data)
    
    # Add total row
    total_minutes = sum(valid_minutes)
    total_duration_formatted = format_minutes_to_hhmm(total_minutes)
    
    total_row = {
        "employee_name": "Total",
        "employee_id": len(present_employees),
        "total_duration": total_duration_formatted
    }
    
    for i in range(1, max_punches + 1):
        total_row[f"punch_{i}"] = None
    
    formatted_data.append(total_row)
    
    # Add two blank rows
    blank_row = {field["fieldname"]: None for field in columns}
    formatted_data.append(blank_row)
    formatted_data.append(blank_row)
    
    # Add absent active employees
    for employee in all_active_employees:
        if employee.attendance_device_id not in present_employee_ids:
            absent_row = {field["fieldname"]: None for field in columns}
            absent_row["employee_name"] = employee.employee_name
            absent_row["employee_id"] = employee.attendance_device_id
            formatted_data.append(absent_row)
    
    return columns, formatted_data

def calculate_total_minutes(punches):
    total_minutes = 0
    
    for i in range(0, len(punches) - 1, 2):
        try:
            punch_in = punches[i]["punch_time"]
            punch_out = punches[i + 1]["punch_time"]
            
            minutes_diff = int(punch_out.total_seconds() / 60) - int(punch_in.total_seconds() / 60)
            total_minutes += minutes_diff
        except Exception:
            return 0
    
    return total_minutes

def format_minutes_to_hhmm(minutes):
    hours, mins = divmod(minutes, 60)
    return f"{hours:02}:{mins:02}"

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
    if punch.get("punch_type") == "Manual":
        return f"{time_str} (MA)"
    return time_str