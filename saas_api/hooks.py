app_name = "saas_api"
app_title = "Saas Api"
app_publisher = "chirovemunyaradzi@gmail.com"
app_description = "Saas Api"
app_email = "chirovemunyaradzi@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "saas_api",
# 		"logo": "/assets/saas_api/logo.png",
# 		"title": "Saas Api",
# 		"route": "/saas_api",
# 		"has_permission": "saas_api.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/saas_api/css/saas_api.css"
# app_include_js = "/assets/saas_api/js/saas_api.js"

# include js, css files in header of web template
# web_include_css = "/assets/saas_api/css/saas_api.css"
# web_include_js = "/assets/saas_api/js/saas_api.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "saas_api/public/scss/website"

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
# app_include_icons = "saas_api/public/icons.svg"

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

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "saas_api.utils.jinja_methods",
# 	"filters": "saas_api.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "saas_api.install.before_install"


# Uninstallation
# ------------

# before_uninstall = "saas_api.uninstall.before_uninstall"
# after_uninstall = "saas_api.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "saas_api.utils.before_app_install"
# after_app_install = "saas_api.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "saas_api.utils.before_app_uninstall"
# after_app_uninstall = "saas_api.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "saas_api.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
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

# scheduler_events = {
# 	"all": [
# 		"saas_api.tasks.all"
# 	],
# 	"daily": [
# 		"saas_api.tasks.daily"
# 	],
# 	"hourly": [
# 		"saas_api.tasks.hourly"
# 	],
# 	"weekly": [
# 		"saas_api.tasks.weekly"
# 	],
# 	"monthly": [
# 		"saas_api.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "saas_api.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "saas_api.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "saas_api.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["saas_api.utils.before_request"]
# after_request = ["saas_api.utils.after_request"]

# Job Events
# ----------
# before_job = ["saas_api.utils.before_job"]
# after_job = ["saas_api.utils.after_job"]

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
# 	"saas_api.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
after_install = [
    "saas_api.www.api.c",
    # "saas_api.utils.create_default_user_rights",
    # "saas_api.user.assign_admin_profile"
]
# patches = [
#    "saas_api.patches.add_user_rights_profile",
#    "saas_api.patches.create_default_profiles"
# ]

boot = "utils.create_default_user_rights"
doc_events = {
     "User": {
        "after_insert": "saas_api.www.on_before.after_insert"
    },
    "Item": {
        "before_insert": "saas_api.www.on_before.item_before_insert"
    },
    # "Supplier": {
    #     "before_insert": "saas_api.www.on_before.supplier_before_insert"
    # },
    # "Item Group": {
    #     "before_insert": "saas_api.www.on_before.item_group_before_insert"
    # }
}

permission_query_conditions = {
    "Supplier": "saas_api.www.on_before.supplier_permission_query",
    "Warehouse": "saas_api.www.on_before.warehouse_permission_query",
    "User": "saas_api.www.on_before.users_permission_query",
    "Item Group": "saas_api.www.on_before.item_group_permission_query"
}

fixtures = [
    # Existing Custom Fields fixture
    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "=", "Customer"],
            ["fieldname", "in", [
                "custom_cost_center",
                "custom_warehouse",
            ]]
        ]
    },
    {
        "dt": "Client Script",
        "filters": [
            ["name", "in", [
                "settings user permmission", 
               
            ]]
        ]
    }
]


