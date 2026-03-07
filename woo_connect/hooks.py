app_name = "woo_connect"
app_title = "Woocommerce Connect"
app_publisher = "Primetechbd"
app_description = "Woocommerce Connectior for erpnext"
app_email = "info@primetechbd.xyz"
app_license = "mit"

# Apps
# ------------------

# required_apps = []
required_apps = ["frappe", "erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "woo_connect",
# 		"logo": "/assets/woo_connect/logo.png",
# 		"title": "Woocommerce Connect",
# 		"route": "/woo_connect",
# 		"has_permission": "woo_connect.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/woo_connect/css/woo_connect.css"
# app_include_js = "/assets/woo_connect/js/woo_connect.js"

# include js, css files in header of web template
# web_include_css = "/assets/woo_connect/css/woo_connect.css"
# web_include_js = "/assets/woo_connect/js/woo_connect.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "woo_connect/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "woo_connect/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "woo_connect.utils.jinja_methods",
# 	"filters": "woo_connect.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "woo_connect.install.before_install"
# after_install = "woo_connect.install.after_install"

# Fixtures
# --------
fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Woocommerce Connect"]]}
]

# Uninstallation
# ------------

# before_uninstall = "woo_connect.uninstall.before_uninstall"
# after_uninstall = "woo_connect.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "woo_connect.utils.before_app_install"
# after_app_install = "woo_connect.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "woo_connect.utils.before_app_uninstall"
# after_app_uninstall = "woo_connect.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "woo_connect.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"hourly_long": [
		"woo_connect.woocommerce_connect.sync.item_sync.sync_items_from_woocommerce",
		"woo_connect.woocommerce_connect.sync.customer_sync.sync_customers_from_woocommerce",
		"woo_connect.woocommerce_connect.sync.order_sync.sync_orders_from_woocommerce",
		"woo_connect.woocommerce_connect.sync.invoice_sync.sync_invoices_from_woocommerce",
		"woo_connect.woocommerce_connect.sync.payment_sync.sync_payments_from_woocommerce",
		"woo_connect.woocommerce_connect.sync.discount_sync.sync_coupons_from_woocommerce",
		"woo_connect.woocommerce_connect.sync.loyalty_sync.sync_loyalty_points_from_woocommerce",
	],
	"daily": [
		"woo_connect.woocommerce_connect.sync.stock_sync.sync_stock_to_woocommerce",
	],
}

# Testing
# -------

# before_tests = "woo_connect.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "woo_connect.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "woo_connect.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "woo_connect.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["woo_connect.utils.before_request"]
# after_request = ["woo_connect.utils.after_request"]

# Job Events
# ----------
# before_job = ["woo_connect.utils.before_job"]
# after_job = ["woo_connect.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"woo_connect.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

