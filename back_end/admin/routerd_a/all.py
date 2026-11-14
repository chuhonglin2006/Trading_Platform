"""后台所有路由汇总"""
from admin.routerd_a.admins import admin
from admin.routerd_a.announcements import admin_announcement
from admin.routerd_a.orders import admin_order
from admin.routerd_a.overview import admin_overview
from admin.routerd_a.products import admin_product
from admin.routerd_a.reports import admin_reports
from admin.routerd_a.system import admin_system
from admin.routerd_a.users import admin_user
from admin.routerd_a.logs import admin_logs

ADMIN_ROUTERS = [
    admin,
    admin_overview,
    admin_user,
    admin_product,
    admin_order,
    admin_reports,
    admin_announcement,
    admin_system,
    admin_logs,
]
