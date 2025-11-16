from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/assembly_engineer/', views.assembly_engineer_dashboard, name='assembly_engineer_dashboard'),
    path('dashboard/assembler/', views.assembler_dashboard, name='assembler_dashboard'),
    path('dashboard/tester/', views.tester_dashboard, name='tester_dashboard'),
    path('dashboard/painting_engineer/', views.painting_engineer_dashboard, name='painting_engineer_dashboard'),
    path('dashboard/painter/', views.painter_dashboard, name='painter_dashboard'),
    path('dashboard/blaster/', views.blaster_dashboard, name='blaster_dashboard'),
    path('dashboard/name_plate_printer/', views.name_plate_printer_dashboard, name='name_plate_printer_dashboard'),
    path('dashboard/finisher/', views.finisher_dashboard, name='finisher_dashboard'),
    path('dashboard/qa_engineer/', views.qa_engineer_dashboard, name='qa_engineer_dashboard'),
   
path('assembler/', views.assembler_dashboard, name='assembler_dashboard'),
path('assembler/order/<str:order_no>/', views.assembler_order_details, name='assembler_order_details'),
path("heat-report/<str:order_no>/", views.generate_heat_report, name="generate_heat_report"),


]
