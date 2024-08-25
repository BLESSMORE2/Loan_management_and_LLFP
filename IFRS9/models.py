from django.db import models

# Create your models here.

class Ldn_Financial_Instrument(models.Model):
    v_account_number = models.CharField(max_length=255, unique=True, null=False)
    d_last_payment_date = models.DateField(null=True)
    d_revised_maturity_date = models.DateField(null=True)
    d_maturity_date = models.DateField(null=True)
    d_orig_maturity_date = models.DateField(null=True)
    d_start_date_p = models.DateField(null=True)
    d_start_date_i = models.DateField(null=True)
    d_start_date = models.DateField(null=True)
    d_next_payment_date = models.DateField(null=True)
    n_cnr = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_allocated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_commitment_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_maturity_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_eop_curr_prin_bal = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_eop_int_bal = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_eop_bal = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_current_fees = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_delinquent_days = models.IntegerField(null=True)
    v_interest_freq_unit = models.CharField(max_length=50, null=True)
    v_interest_payment_type = models.CharField(max_length=50, null=True)
    n_pd_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_lgd_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_ccf_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_acct_risk_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_amrt_term = models.IntegerField(null=True)
    v_amrt_term_unit = models.CharField(max_length=50, null=True)
    v_interest_method = models.CharField(max_length=50, null=True)
    v_ccy_code = models.CharField(max_length=10, null=True)
    v_loan_type = models.CharField(max_length=50, null=True)
    v_lob_code = models.CharField(max_length=50, null=True)
    v_lv_code = models.CharField(max_length=50, null=True)
    v_country_id = models.CharField(max_length=50, null=True)
    v_credit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_coll_ccy = models.CharField(max_length=10, null=True)
    v_collateral_type = models.CharField(max_length=50, null=True)
    n_effective_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    d_orig_next_payment_date = models.DateField(null=True)
    fic_mis_date = models.DateField(null=True)
    n_fees_eir = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    v_account_group_id = models.CharField(max_length=50, null=True)
    v_loan_desc = models.CharField(max_length=255, null=True)
    n_amortized_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_market_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_twelvemonths_pd_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_guaranteed_amt = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    v_loan_default_reason = models.CharField(max_length=255, null=True)
    d_past_due_date = models.DateField(null=True)
    n_ifrs9_provision_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_fees = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    v_account_classification_cd = models.CharField(max_length=50, null=True)
    v_day_count_ind = models.CharField(max_length=10, null=True)
    v_gaap_code = models.CharField(max_length=50, null=True)
    v_repayment_type = models.CharField(max_length=50, null=True)
    n_accrued_interest = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_curr_payment_recd = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_curr_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_undrawn_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    v_branch_code = models.CharField(max_length=50, null=True)
    v_cust_ref_code = models.CharField(max_length=50, null=True)
    v_prod_code = models.CharField(max_length=50, null=True)

    class Meta:
        db_table = 'Ldn_Financial_Instrument'


class Ldn_Customer_Rating_Detail(models.Model):
    fic_mis_date = models.DateField(null=False)
    v_rating_src_code = models.CharField(max_length=50)
    v_party_cd = models.CharField(max_length=50, null=False)
    v_purpose = models.CharField(max_length=50)  # No choices, just a CharField
    v_rating_code = models.CharField(max_length=50)
    v_data_origin = models.CharField(max_length=50)
    v_credit_reason_code = models.CharField(max_length=50)

    class Meta:
        db_table = 'Ldn_Customer_Rating_Detail'
        unique_together = ('fic_mis_date', 'v_party_cd')

class Ldn_Bank_Product_Info(models.Model):
    v_prod_code = models.CharField(max_length=50, unique=True)
    v_prod_name = models.CharField(max_length=100)
    v_prod_type = models.CharField(max_length=50)
    v_prod_group = models.CharField(max_length=50)
    v_prod_group_desc = models.CharField(max_length=255)
    v_prod_segment = models.CharField(max_length=100)
    v_balance_sheet_category = models.CharField(max_length=50)
    v_balance_sheet_category_desc = models.CharField(max_length=255)
    v_prod_type_desc = models.CharField(max_length=255)
    v_prod_desc = models.CharField(max_length=50)

class Ldn_Customer_Info(models.Model):
    v_party_id = models.CharField(max_length=50, unique=True)
    fic_mis_date = models.DateField()
    v_partner_code = models.CharField(max_length=50)
    v_party_type = models.CharField(max_length=50)

    class Meta:
        db_table = 'Ldn_Customer_Info'

class Ldn_PD_Term_Structure(models.Model):
    v_pd_term_structure_id = models.CharField(max_length=100, unique=True)
    v_pd_term_structure_name = models.CharField(max_length=255)
    v_pd_term_structure_desc = models.CharField(max_length=50)
    v_pd_term_frequency_unit = models.CharField(max_length=1, choices=[
        ('M', 'Monthly'),
        ('Q', 'Quarterly'),
        ('H', 'Half Yearly'),
        ('Y', 'Yearly'),
        ('D', 'Daily'),
    ])
    v_pd_term_structure_type = models.CharField(max_length=1, choices=[
        ('R', 'Rating'),
        ('D', 'DPD'),
    ])
    v_default_probability_type = models.CharField(max_length=1, choices=[
        ('M', 'Marginal'),
        ('C', 'Cumulative'),
    ])
    fic_mis_date = models.DateField()
    n_pd_term_frequency = models.PositiveIntegerField()
    v_data_source_code = models.CharField(max_length=50)

    class Meta:
        db_table = 'Ldn_pd_term_structure'
        unique_together = ('v_pd_term_structure_id', 'fic_mis_date')

class Ldn_PD_Term_Structure_Dtl(models.Model):
    v_pd_term_structure_id = models.ForeignKey(
        'Ldn_PD_Term_Structure',
        on_delete=models.CASCADE,
        related_name='term_structure_details'
    )
    fic_mis_date = models.DateField()
    v_credit_risk_basis_cd = models.CharField(max_length=100)
    n_period_applicable = models.PositiveIntegerField()
    n_pd_percent = models.DecimalField(max_digits=5, decimal_places=4)
    v_scenario_cd = models.CharField(max_length=50)
    v_data_source_code = models.CharField(max_length=50)

    class Meta:
        db_table = 'Ldn_pd_term_structure_dtl'
        unique_together = ('v_pd_term_structure_id', 'fic_mis_date', 'v_credit_risk_basis_cd', 'n_period_applicable', 'v_scenario_cd')




class Ldn_LGD_Term_Structure(models.Model):
    v_lgd_term_structure_id = models.CharField(max_length=100, primary_key=True)
    v_lgd_term_structure_name = models.CharField(max_length=255)
    v_lgd_term_structure_desc = models.CharField(max_length=50)
    v_lgd_term_frequency_unit = models.CharField(max_length=1)  # e.g., M, Q, H, Y, D
    n_lgd_percent = models.DecimalField(max_digits=5, decimal_places=4)
    fic_mis_date = models.DateField()
    v_data_source_code = models.CharField(max_length=50)

    class Meta:
        db_table = 'Ldn_lgd_term_structure'


class Ldn_Exchange_Rate(models.Model):
    fic_mis_date = models.DateField()
    v_from_ccy_code = models.CharField(max_length=3)
    v_to_ccy_code = models.CharField(max_length=3)
    n_exchange_rate = models.DecimalField(max_digits=15, decimal_places=6)

    class Meta:
        db_table = 'Ldn_exchange_rate'
        unique_together = ('fic_mis_date', 'v_from_ccy_code', 'v_to_ccy_code')

class Ldn_Expected_Cashflow(models.Model):
    fic_mis_date = models.DateField()
    v_account_number = models.CharField(max_length=50)
    d_cash_flow_date = models.DateField()
    n_cash_flow_amount = models.DecimalField(max_digits=20, decimal_places=2)
    v_financial_element_code = models.CharField(max_length=10)
    v_iso_ccy_code = models.CharField(max_length=3)

    class Meta:
        db_table = 'Ldn_expected_cashflow'
        unique_together = ('fic_mis_date', 'v_account_number', 'd_cash_flow_date')

class Ldn_Recovery_Cashflow(models.Model):
    fic_mis_date = models.DateField()
    v_account_number = models.CharField(max_length=50)
    d_cash_flow_date = models.DateField()
    n_cash_flow_amount = models.DecimalField(max_digits=20, decimal_places=2)
    v_financial_element_code = models.CharField(max_length=10)
    v_iso_ccy_code = models.CharField(max_length=3)

    class Meta:
        db_table = 'Ldn_Recovery_Cashflow'
        unique_together = ('fic_mis_date', 'v_account_number', 'd_cash_flow_date')

class Ldn_Acct_Recovery_Detail(models.Model):
    v_account_number = models.CharField(max_length=50)
    fic_mis_date = models.DateField()
    d_recovery_date = models.DateField()
    v_recovery_type_code = models.CharField(max_length=20)
    n_prin_recovery_amt = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_int_recovery_amt = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_charge_recovery_amt = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    v_recovery_stage_code = models.CharField(max_length=20, null=True, blank=True)
    n_cost_case_filed = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    v_iso_currency_cd = models.CharField(max_length=3, null=True, blank=True)
    v_lv_code = models.CharField(max_length=20, null=True, blank=True)
    n_recovery_income_amt = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    v_data_source_code = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "ldn_acct_recovery_detail"
        unique_together = ('v_account_number', 'fic_mis_date', 'd_recovery_date')

class TableMetadata(models.Model):
    TABLE_TYPE_CHOICES = [
        ('FACT', 'Fact Table'),
        ('DIM', 'Dimension Table'),
        ('REF', 'Reference Table'),
        ('STG', 'Staging Table'),
        ('OTHER', 'Other'),
    ]

    table_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    table_type = models.CharField(max_length=10, choices=TABLE_TYPE_CHOICES, default='OTHER')

    def __str__(self):
        return f"{self.table_name} ({self.get_table_type_display()})"