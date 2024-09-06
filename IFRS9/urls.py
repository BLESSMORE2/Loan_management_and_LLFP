from django.urls import path
from . import views
from .views import *
from django.views.generic import TemplateView  # Import TemplateView

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('app-list/', views.app_list_view, name='app_list'),
    path('ifrs9-home-list/', views.ifrs9_home_view, name='ifrs9_home'),
    path('data_management/', views.data_management, name='data_management'),
    path('upload/', FileUploadView.as_view(), name='file_upload'),
    path('select_columns/', ColumnSelectionView.as_view(), name='select_columns'),
    path('map_columns/', ColumnMappingView.as_view(), name='map_columns'),
    path('submit_to_database/', SubmitToDatabaseView.as_view(), name='submit_to_database'),
    path('data-entry/', data_entry_view, name='data_entry'),
    path('view-data/', view_data, name='view_data'),
    path('filter-table/<str:table_name>/', filter_table, name='filter_table'),
    path('download-data/<str:table_name>/', download_data, name='download_data'),
    path('edit-row/<str:table_name>/<int:row_id>/', edit_row, name='edit_row'),
    path('delete-row/<str:table_name>/<int:row_id>/', delete_row, name='delete_row'),

    path('credit-risk-models/', views.credit_risk_models_view, name='credit_risk_models'),
    path('cash-flow-generation/', views.cash_flow_generation_issues, name='cash_flow_generation_issues'),
    path('projections/', cashflow_projection_view, name='cashflow_projection'),
    path('projections/success/', TemplateView.as_view(template_name='projection_success.html'), name='projection_success'),
]


    

    
