import frappe
from frappe import _
from calendar import monthrange
from datetime import datetime, timedelta

@frappe.whitelist()
def get_attendance_years():
    """Return list of years for which attendance records exist."""
    years = frappe.db.sql("""
        SELECT DISTINCT YEAR(event_date) as attendance_year
        FROM `tabBiometric Attendance Log`
        ORDER BY attendance_year DESC
    """)
    return "\n".join([str(year[0]) for year in years]) or \
        "\n".join([str(year) for year in range(datetime.now().year, datetime.now().year - 5, -1)])

def execute(filters=None):
    if not filters:
        frappe.throw(_('Please select Month and Year'))
    
    if not filters.get('month') or not filters.get('year'):
        frappe.throw(_('Please select Month and Year'))

    total_hours_hh_mm = filters.get('total_hours_hh_mm', False)
    
    # Convert month and year to date range
    month = int(filters.get('month'))
    year = int(filters.get('year'))
    days_in_month = monthrange(year, month)[1]
    
    from_date = datetime(year, month, 1)
    to_date = datetime(year, month, days_in_month)
    
    # Format dates for SQL queries
    from_date_str = from_date.strftime('%Y-%m-%d')
    to_date_str = to_date.strftime('%Y-%m-%d')
    
    # Create filter dict with date range for downstream processing
    filters['date_range'] = [from_date_str, to_date_str]
    filters['total_hours_hh_mm'] = True
    
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
    
    # Add total columns
    if total_hours_hh_mm:
        columns.append({"fieldname": "total_duration", "label": _("Total"), "fieldtype": "Data", "width": 100, "align": "center"})
        
    columns.append({"fieldname": "total_duration_decimal", "label": _("Total Hours"), "fieldtype": "Data", "width": 100, "align": "center"})
    
    # Build employee filter for the query
    employee_filter = ""
    employee_params = {
        "from_date": from_date_str,
        "to_date": to_date_str
    }
    
    if filters.get('employee'):
        employee_filter = "AND e.name = %(employee)s"
        employee_params["employee"] = filters.get('employee')
    
    # Get ALL employees except inactive ones, regardless of attendance logs
    employee_query = ""
    if filters.get('employee'):
        employee_query = "AND e.name = %(employee)s"
    
    employees = frappe.db.sql(f"""
        SELECT DISTINCT 
            e.attendance_device_id as employee_no,
            e.name as employee,
            e.employee_name,
            e.department,
            e.attendance_device_id,
            e.status,
            d.name as department_id,
            d.department_name
        FROM `tabEmployee` e
        LEFT JOIN `tabDepartment` d ON e.department = d.name
        WHERE e.status = 'Active'
        {employee_query}
    """, employee_params, as_dict=True)
    
    # Sort employees by their employee number
    def natural_sort_key(emp):
        # Handle None/NULL values
        if not emp["employee_no"]:
            return ""
        
        # Convert all to string to avoid type comparison issues
        emp_no = str(emp["employee_no"])
        
        # Try to extract digits if it's a mixed string
        digits = ''.join(c for c in emp_no if c.isdigit())
        
        if digits and emp_no == digits:  # Pure numeric string
            return int(digits)
        elif digits:  # Mixed string with some digits
            return (0, emp_no)  # Place mixed strings before pure numeric
        else:  # No digits at all
            return (0, emp_no)
    
    # Use try-except in case sorting fails
    try:
        employees.sort(key=natural_sort_key)
    except Exception:
        # Fallback to simple string sorting if natural sort fails
        employees.sort(key=lambda emp: str(emp.get("employee_no") or ""))
    
    data = []
    
    # Process each employee's attendance
    for employee in employees:
        # We already filtered out inactive employees in the SQL query
        row = {
            "employee_name": employee.employee_name,
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
                # Fetch punches
                punches = frappe.db.sql("""
                    SELECT at.punch_time
                    FROM `tabBiometric Attendance Punch Table` at
                    WHERE at.parent = %(log_name)s
                    ORDER BY at.punch_time
                """, {"log_name": log.name}, as_dict=True)
                
                # Skip if no punches exist
                if not punches:
                    continue
                
                # Make decisions about punches
                if len(punches) >= 2:  # Need at least one in-out pair
                    # If odd number of punches, ignore the last one
                    if len(punches) % 2 != 0:
                        punches = punches[:-1]
                    
                    duration = calculate_total_minutes(punches)
                    if duration > 0:
                        valid_durations.append(duration)
            
            # Calculate the total duration for the day
            if valid_durations:
                total_duration = sum(valid_durations)
                formatted_duration = format_minutes_to_hhmm(total_duration)
                total_employee_duration += timedelta(minutes=total_duration)
            else:
                formatted_duration = "00:00"
            
            row[f"duration_{date.strftime('%Y%m%d')}"] = formatted_duration
        
        # Format total duration for the employee
        row["total_duration"] = format_minutes_to_hhmm(int(total_employee_duration.total_seconds() / 60))
        row["total_duration_decimal"] = format_decimal_duration(total_employee_duration)
        
        # Include all active employees
        data.append(row)
    
    # Calculate totals for each date and overall
    total_row = {
        "employee_name": "Total",
        "employee_id": len(data),  # Count of active employees included in the report
    }
    total_minutes_all = 0
    
    for date in date_list:
        date_key = f"duration_{date.strftime('%Y%m%d')}"
        total_minutes = 0
        
        for row in data:
            if row.get(date_key) and row[date_key] != "00:00":
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
    total_row["total_duration_decimal"] = f"{hours_all + (minutes_all / 60):.2f}"
    
    data.append(total_row)
    
    return columns, data

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

def format_decimal_duration(duration):
    total_minutes = int(duration.total_seconds() // 60)
    hours = total_minutes // 60
    minutes_fraction = total_minutes % 60 / 60  # Convert remaining minutes to fraction
    
    result = hours + minutes_fraction  # Sum both values
    return f"{result:.4f}"  # Format to exactly 4 decimal places