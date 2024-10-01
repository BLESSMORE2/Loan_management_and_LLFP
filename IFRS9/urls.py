from django.urls import path
from . import views
from .views import *
from django.views.generic import TemplateView  # Import TemplateView
from .views import CreditRatingStageListView, CreditRatingStageCreateView, CreditRatingStageUpdateView, CreditRatingStageDeleteView
from .views import *


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
    path('projections/', cashflow_projection_view, name='cashflow_projection'),
    path('projections/success/', TemplateView.as_view(template_name='projection_success.html'), name='projection_success'),

    path('configure-stages/', views.configure_stages, name='configure_stages'),
    path('staging/ratings/', CreditRatingStageListView.as_view(), name='staging_using_ratings'),
    path('staging/delinquent-days/', views.staging_using_delinquent_days, name='staging_using_delinquent_days'),
    path('staging/stage-reassignment/', stage_reassignment, name='stage_reassignment'),
    path('staging/ratings/add/', CreditRatingStageCreateView.as_view(), name='creditrating_stage_add'),
    path('staging/ratings/<pk>/edit/', CreditRatingStageUpdateView.as_view(), name='creditrating_stage_edit'),
    path('staging/ratings/<pk>/delete/', CreditRatingStageDeleteView.as_view(), name='creditrating_stage_delete'),

    path('staging/dpd/', DPDStageMappingListView.as_view(), name='dpd_stage_mapping_list'),
    path('staging/dpd/add/', DPDStageMappingCreateView.as_view(), name='dpd_stage_mapping_add'),
    path('staging/dpd/<pk>/edit/', DPDStageMappingUpdateView.as_view(), name='dpd_stage_mapping_edit'),
    path('staging/dpd/<pk>/delete/', DPDStageMappingDeleteView.as_view(), name='dpd_stage_mapping_delete'),

    path('staging/cooling-periods/', CoolingPeriodDefinitionListView.as_view(), name='cooling_period_definitions'),
    path('staging/cooling-periods/add/', CoolingPeriodDefinitionCreateView.as_view(), name='cooling_period_definition_add'),
    path('staging/cooling-periods/<pk>/edit/', CoolingPeriodDefinitionUpdateView.as_view(), name='cooling_period_definition_edit'),
    path('staging/cooling-periods/<pk>/delete/', CoolingPeriodDefinitionDeleteView.as_view(), name='cooling_period_definition_delete'),

    path('staging/delinquency-band/', DimDelinquencyBandListView.as_view(), name='dim_delinquency_band_list'),
    path('staging/delinquency-band/add/', DimDelinquencyBandCreateView.as_view(), name='dim_delinquency_band_add'),
    path('staging/delinquency-band/<pk>/edit/', DimDelinquencyBandUpdateView.as_view(), name='dim_delinquency_band_edit'),
    path('staging/delinquency-band/<pk>/delete/', DimDelinquencyBandDeleteView.as_view(), name='dim_delinquency_band_delete'),

    path('staging/credit-rating-codes/', CreditRatingCodeBandListView.as_view(), name='credit_rating_code_band_list'),
    path('staging/credit-rating-codes/add/', CreditRatingCodeBandCreateView.as_view(), name='credit_rating_code_band_add'),
    path('staging/credit-rating-codes/<pk>/edit/', CreditRatingCodeBandUpdateView.as_view(), name='credit_rating_code_band_edit'),
    path('staging/credit-rating-codes/<pk>/delete/', CreditRatingCodeBandDeleteView.as_view(), name='credit_rating_code_band_delete'),

    path('cashflow-projections/', views.cashflow_projections, name='cashflow_projections'),
    path('cashflow-projections/documentation/', views.cashflow_projections_documentation, name='cashflow_projections_documentation'),
    path('interest-methods/', InterestMethodListView.as_view(), name='interest_method_list'),
    path('interest-methods/add/', InterestMethodCreateView.as_view(), name='interest_method_add'),
    path('interest-methods/<int:pk>/edit/', InterestMethodUpdateView.as_view(), name='interest_method_edit'),
    path('interest-methods/<int:pk>/delete/', InterestMethodDeleteView.as_view(), name='interest_method_delete'),



]





    

    
