# from django.contrib import admin
# from .models import *
# from .forms import FSIProductSegmentForm

# # Register your models here.

# @admin.register(Ldn_Financial_Instrument)
# class Ldn_Financial_InstrumentsAdmin(admin.ModelAdmin):
#     list_display = ('v_account_number', 'fic_mis_date', 'v_prod_code')  # Ensure these fields exist
#     search_fields = ('v_account_number', 'v_loan_type')  # Ensure these fields exist
#     list_filter = ('v_loan_type', 'v_country_id') 

# @admin.register(Ldn_Customer_Rating_Detail)
# class Ldn_Customer_Rating_DetailsAdmin(admin.ModelAdmin):
#     list_display = ('v_party_cd', 'v_rating_code', 'fic_mis_date')
#     search_fields = ('v_party_cd', 'v_rating_code')
#     list_filter = ('v_rating_code',)

# @admin.register(Ldn_Bank_Product_Info)
# class Ldn_Bank_Product_InfoAdmin(admin.ModelAdmin):
#     list_display = ('v_prod_code', 'v_prod_name', 'v_prod_type','v_prod_segment')
#     search_fields = ('v_prod_code', 'v_prod_name')
#     list_filter = ('v_prod_type', 'v_prod_group')

# @admin.register(FSI_Product_Segment)
# class FSI_Product_SegmentAdmin(admin.ModelAdmin):
#     form = FSIProductSegmentForm  # Use the custom form
#     list_display = ('segment_id', 'v_prod_segment', 'v_prod_type', 'v_prod_desc')
#     search_fields = ('v_prod_segment', 'v_prod_type')
#     list_filter = ('v_prod_segment', 'v_prod_type')


# @admin.register(Ldn_Customer_Info)
# class Ldn_Customer_InfoAdmin(admin.ModelAdmin):
#     list_display = ('v_party_id', 'v_partner_name', 'fic_mis_date')
#     search_fields = ('v_party_id', 'v_partner_name')
#     list_filter = ('v_partner_name',)

# @admin.register(Ldn_PD_Term_Structure)
# class Ldn_PD_Term_StructureAdmin(admin.ModelAdmin):
#     list_display = ('v_pd_term_structure_id', 'v_pd_term_structure_name', 'fic_mis_date')
#     search_fields = ('v_pd_term_structure_id', 'v_pd_term_structure_name')
#     list_filter = ('v_pd_term_structure_type',)

# @admin.register(Ldn_PD_Term_Structure_Dtl)
# class Ldn_PD_Term_Structure_DtlAdmin(admin.ModelAdmin):
#     list_display = ('v_pd_term_structure_id', 'v_credit_risk_basis_cd')
#     search_fields = ('v_pd_term_structure_id', 'v_credit_risk_basis_cd')
#     list_filter = ('v_pd_term_structure_id',)


# @admin.register(FSI_PD_Interpolated)
# class FSI_PD_InterpolatedAdmin(admin.ModelAdmin):
#     list_display = ('v_pd_term_structure_id','v_pd_term_structure_type', 'v_delq_band_code','n_per_period_default_prob', 'n_cumulative_default_prob','v_cash_flow_bucket_id')
#     search_fields = ('v_pd_term_structure_type', )
#     list_filter = ('v_pd_term_structure_type',)

# @admin.register(FSI_PD_Account_Interpolated)
# class FSI_PD_Account_InterpolatedAdmin(admin.ModelAdmin):
#     list_display = ('v_account_number','n_per_period_default_prob', 'n_cumulative_default_prob','v_cash_flow_bucket_id')
#     search_fields = ('v_account_number', )
#     list_filter = ('v_account_number',)

# @admin.register(Ldn_LGD_Term_Structure)
# class Ldn_LGD_Term_StructureAdmin(admin.ModelAdmin):
#     list_display = ('v_lgd_term_structure_id', 'v_lgd_term_structure_name', 'fic_mis_date')
#     search_fields = ('v_lgd_term_structure_id', 'v_lgd_term_structure_name')
#     list_filter = ('v_lgd_term_structure_id',)

# @admin.register(Ldn_Exchange_Rate)
# class Ldn_Exchange_RatesAdmin(admin.ModelAdmin):
#     list_display = ('fic_mis_date', 'v_from_ccy_code', 'v_to_ccy_code', 'n_exchange_rate')
#     search_fields = ('v_from_ccy_code', 'v_to_ccy_code')
#     list_filter = ('v_from_ccy_code', 'v_to_ccy_code')

# @admin.register(Ldn_Expected_Cashflow)
# class Ldn_Expected_CashflowsAdmin(admin.ModelAdmin):
#     list_display = ('fic_mis_date', 'v_account_number', 'd_cash_flow_date', 'n_cash_flow_amount')
#     search_fields = ('v_account_number',)
#     list_filter = ('fic_mis_date', 'V_CASH_FLOW_TYPE')

# @admin.register(Ldn_Recovery_Cashflow)
# class Ldn_Recovery_CashflowsAdmin(admin.ModelAdmin):
#     list_display = ('fic_mis_date', 'v_account_number', 'd_cash_flow_date', 'n_cash_flow_amount')
#     search_fields = ('v_account_number',)
#     list_filter = ('fic_mis_date', 'V_CASH_FLOW_TYPE')


# @admin.register(FSI_Expected_Cashflow)
# class FSI_Expected_CashflowAdmin(admin.ModelAdmin):
#     list_display = ('fic_mis_date', 'v_account_number','n_cash_flow_bucket', 'd_cash_flow_date','n_principal_payment','n_interest_payment', 'n_cash_flow_amount','n_balance')
#     search_fields = ('v_account_number',)
#     list_filter = ('fic_mis_date', 'V_CASH_FLOW_TYPE')

# @admin.register(Ldn_Acct_Recovery_Detail)
# class Ldn_Acct_Recovery_DetailsAdmin(admin.ModelAdmin):
#     list_display = ('v_account_number', 'fic_mis_date', 'd_recovery_date', 'v_recovery_type_code')
#     search_fields = ('v_account_number', 'v_recovery_type_code')
#     list_filter = ('fic_mis_date', 'v_recovery_stage_code')



# @admin.register(FCT_Stage_Determination)
# class FCT_Stage_DeterminationAdmin(admin.ModelAdmin):
#     list_display = ('n_account_number', 'fic_mis_date','d_acct_start_date')
#     search_fields = ('n_account_number', )
#     list_filter = ('fic_mis_date', )
# @admin.register(TableMetadata)
# class TableMetadataAdmin(admin.ModelAdmin):
#     list_display = ('table_name', 'table_type', 'description')
#     list_filter = ('table_type',)
#     search_fields = ('table_name', 'description')

