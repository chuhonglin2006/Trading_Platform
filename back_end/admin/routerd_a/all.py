"""后台所有路由汇总"""
from admin.routerd_a.admins import admin
from admin.routerd_a.announcements import admin_announcement
from admin.routerd_a.orders import admin_order
from admin.routerd_a.overview import admin_overview
from admin.routerd_a.products import admin_product
from admin.routerd_a.reports import admin_reports
from admin.routerd_a.users import admin_user

ADMIN_ROUTERS = [
    admin,
    admin_overview,
    admin_user,
    admin_product,
    admin_order,
    admin_reports,
    admin_announcement,
]
