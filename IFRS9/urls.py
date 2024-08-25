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
    
]