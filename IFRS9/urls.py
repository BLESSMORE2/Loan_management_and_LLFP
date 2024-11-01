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
    path('upload/progress/', CheckProgressView.as_view(), name='check_progress'),
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

    path('configurations/probability/', views.probability_configuration, name='probability_configuration'),
    path('segments/', views.segment_list, name='segment_list'),
    path('segments/create/', views.segment_create, name='segment_create'),
    path('get-product-types/', views.get_product_types, name='get_product_types'),
    path('get-product-description/', views.get_product_description, name='get_product_description'),
    path('segments/<int:segment_id>/edit/', views.segment_edit, name='segment_edit'),
    path('segments/<int:segment_id>/delete/', views.segment_delete, name='segment_delete'),

    path('pd-term-structures/', pd_term_structure_list, name='pd_term_structure_list'),
    path('pd-term-structures/create/', pd_term_structure_create, name='pd_term_structure_create'),
    path('pd-term-structures/edit/<int:term_id>/', pd_term_structure_edit, name='pd_term_structure_edit'),
    path('pd-term-structures/delete/<int:term_id>/', pd_term_structure_delete, name='pd_term_structure_delete'),

    path('delinquent-pd/', delinquent_pd_list, name='delinquent_pd_list'),
    path('delinquent-pd/create/', delinquent_pd_create, name='delinquent_pd_create'),
    path('delinquent-pd/edit/<int:term_id>/', delinquent_pd_edit, name='delinquent_pd_edit'),
    path('delinquent-pd/delete/<int:term_id>/', delinquent_pd_delete, name='delinquent_pd_delete'),

    # List view for rating based PD terms
    path('rating-pd/', views.rating_pd_list, name='rating_pd_list'),
    path('rating-pd/create/', views.rating_pd_create, name='rating_pd_create'),
    path('rating-pd/edit/<int:term_id>/', views.rating_pd_edit, name='rating_pd_edit'),
    path('rating-pd/delete/<int:term_id>/', views.rating_pd_delete, name='rating_pd_delete'),

    path('interpolation-methods/', views.interpolation_method_list, name='interpolation_method_list'),
    path('interpolation-methods/create/', views.interpolation_method_create, name='interpolation_method_create'),
    path('interpolation-methods/edit/<int:method_id>/', views.interpolation_method_edit, name='interpolation_method_edit'),
    path('interpolation-methods/delete/<int:method_id>/', views.interpolation_method_delete, name='interpolation_method_delete'),

    path('lgd-configuration/', views.lgd_configuration, name='lgd_configuration'),
    path('lgd-term-structure/', lgd_term_structure_list, name='lgd_term_structure_list'),
    path('lgd-term-structure/create/', lgd_term_structure_create, name='lgd_term_structure_create'),
    path('lgd-term-structure/edit/<int:term_id>/', lgd_term_structure_edit, name='lgd_term_structure_edit'),
    path('lgd-term-structure/delete/<int:term_id>/', lgd_term_structure_delete, name='lgd_term_structure_delete'),
    path('lgd-calculation/view/', views.view_lgd_calculation, name='view_lgd_calculation'),
    path('lgd-calculation/edit/', views.edit_lgd_calculation, name='edit_lgd_calculation'),

    path('ifrs9-configuration/', views.ifrs9_configuration, name='ifrs9_configuration'),
    path('ecl-methodology/', views.ecl_methodology_options, name='ecl_methodology'),
    path('ecl-methodology/documentation/', views.ecl_methodology_documentation, name='ecl_methodology_documentation'),
    path('ecl-methodology-list/', views.ecl_methodology_list, name='ecl_methodology_list'),
    path('ecl-methodology/add/', views.add_ecl_method, name='add_ecl_method'),
    path('ecl-methodology/edit/<int:method_id>/', views.edit_ecl_method, name='edit_ecl_method'),
    path('ecl-methodology/delete/<int:method_id>/', views.delete_ecl_method, name='delete_ecl_method'),

    path('ecl-methodology/choose/', views.choose_ecl_methodology, name='choose_ecl_methodology'),
    path('column_mapping/', column_mapping_view, name='column_mapping'),
    path('configure-reporting-currency/', configure_reporting_currency, name='configure_reporting_currency'),
    #path('define-currency-codes/', define_currency_codes_view, name='define_currency_codes'),
    path('reporting-currencies/', reporting_currency_list, name='reporting_currency_list'),
    path('reporting-currencies/create/', reporting_currency_create, name='reporting_currency_create'),
    path('reporting-currencies/edit/<int:currency_id>/', reporting_currency_edit, name='reporting_currency_edit'),
    path('reporting-currencies/delete/<int:currency_id>/', reporting_currency_delete, name='reporting_currency_delete'),
    path('define-reporting-currency/', define_currency_view, name='define_reporting_currency_view'),
    path('define-reporting-currency/create/', define_currency_create, name='define_reporting_currency_create'),
    path('define-reporting-currency/edit/<int:currency_id>/', define_currency_edit, name='define_reporting_currency_edit'),
    path('define-reporting-currency/delete/<int:currency_id>/', define_currency_delete, name='define_reporting_currency_delete'),
    path('configure-exchange-rates-options/', configure_exchange_rates_options, name='configure_exchange_rates_options'),
    path('supported-currencies/', supported_currencies, name='supported_currencies'),
    path('configure-exchange-rate-process/', configure_exchange_rate_process, name='configure_exchange_rate_process'),
    path('configure-exchange-rate', views.add_exchange_rate_conf, name='add_exchange_rate_conf'),
    path('configure-exchange-rate-process/edit/<int:id>/', edit_exchange_rate_conf, name='edit_exchange_rate_conf'),
    path('configure-exchange-rate-process/delete/<int:id>/', delete_exchange_rate_conf, name='delete_exchange_rate_conf'),
    path('view-exchange-rate/', views.view_exchange_rate, name='view_exchange_rate'),




    path('operations/', views.operations_view, name='operations'),
    path('processes/', views.process_list, name='process_list'),
    path('process/<int:process_id>/', views.process_detail, name='process_detail'),
    path('process/create/', views.create_process, name='create_process'),
    path('process/delete/<int:process_id>/', views.delete_process, name='delete_process'),
    path('process/execute/', views.execute_process_view, name='execute_process_view'),
    path('process/run/', views.run_process_execution, name='run_process_execution'),
    path('ajax/get_process_functions/<int:process_id>/', views.get_process_functions, name='get_process_functions'),
    path('process/monitor/', views.monitor_running_process_view, name='monitor_running_process_view'),
    path('ajax/get_process_function_status/<str:process_run_id>/', views.get_process_function_status, name='get_process_function_status'),
    path('process/monitor/<str:process_run_id>/', views.monitor_specific_process, name='monitor_specific_process'),
    path('get-updated-status-table/', views.get_updated_status_table, name='get_updated_status_table'),
    path('running-processes/', running_processes_view, name='running_processes'),
    path('cancel-process/<str:process_run_id>/', cancel_running_process, name='cancel_running_process'),


    path('reports-home/', views.reporting_home, name='reporting_home'),
    path('report/', view_results_and_extract, name='view_results_and_extract'),
    path('reports/', views.list_reports, name='list_reports'),
    path('download_report/', views.download_report, name='download_report'),
    path('ecl-summary-report/', views.ecl_main_filter_view, name='ecl_summary_report'),
    path('ecl-sub-filter/', ecl_sub_filter_view, name='ecl_sub_filter_view'),
    path('export-ecl-report/', views.export_ecl_report_to_excel, name='export_ecl_report_to_excel'),
    path('ecl-reconciliation-main-filter/', ecl_reconciliation_main_filter_view, name='ecl_reconciliation_main_filter'),
    path('ecl-reconciliation-sub-filter/', views.ecl_reconciliation_sub_filter_view, name='ecl_reconciliation_sub_filter_view'),
    path('export-ecl-reconciliation-to-excel/', export_ecl_reconciliation_to_excel, name='export_ecl_reconciliation_to_excel'),
    path('ecl-account-reconciliation-main-filter/', ecl_account_reconciliation_main_filter_view, name='ecl_account_reconciliation_main_filter'),
    path('ecl-account-reconciliation-sub-filter/', ecl_account_reconciliation_sub_filter_view, name='ecl_account_reconciliation_sub_filter'),
    path('export-full-ecl-report/', export_full_ecl_report_to_excel, name='export_full_ecl_report_to_excel'),
    path('pd-analysis-main-filter/', views.pd_analysis_main_filter_view, name='pd_analysis_main_filter'),
    path('pd-analysis-report/', views.pd_analysis_sub_filter_view, name='pd_analysis_sub_filter_view'),
    path('export-pd-report-to-excel/', export_pd_report_to_excel, name='export_pd_report_to_excel'),









]





    

    
