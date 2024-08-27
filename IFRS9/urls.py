from django.urls import path
from . import views
from .views import *

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
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

    
]