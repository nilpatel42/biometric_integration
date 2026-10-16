import frappe
from frappe.utils.user import is_website_user


APP_NAME = "biometric_integration"


def has_app_permission():
	"""Show the app when the user can read at least one biometric DocType."""
	if frappe.session.user == "Administrator":
		return True

	if is_website_user():
		return False

	doctypes = frappe.get_all("DocType", filters={"module.app_name": APP_NAME}, pluck="name")
	return any(frappe.has_permission(doctype, ptype="read") for doctype in doctypes)
