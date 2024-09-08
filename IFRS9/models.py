from django.db import models

# Create your models here.

class Ldn_Financial_Instrument(models.Model):
    fic_mis_date = models.DateField(null=True)
    v_account_number = models.CharField(max_length=255, unique=True, null=False)
    v_cust_ref_code = models.CharField(max_length=50, null=True)
    v_prod_code = models.CharField(max_length=50, null=True)
    n_curr_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, help_text="Fixed interest rate for the loan")    
    # The changing interest rate (e.g., LIBOR or SOFR)
    n_interest_changing_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, help_text="Changing interest rate value, e.g., LIBOR rate at a specific time")   
    v_interest_freq_unit = models.CharField(max_length=50, null=True)
    v_interest_payment_type = models.CharField(max_length=50, null=True)
    # New fields for variable rate and fees   
    v_management_fee_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, help_text="Annual management fee rate, e.g., 1%")
    n_wht_percent= models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_effective_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_accrued_interest = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    d_start_date = models.DateField(null=True)
    d_last_payment_date = models.DateField(null=True)
    d_next_payment_date = models.DateField(null=True)
    d_maturity_date = models.DateField(null=True)
    v_amrt_repayment_type = models.CharField(max_length=50, null=True)
    v_amrt_term_unit = models.CharField(max_length=50, null=True)
    n_eop_curr_prin_bal = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_eop_int_bal = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_eop_bal = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_delinquent_days = models.IntegerField(null=True)
    n_pd_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_lgd_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_acct_risk_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_ccy_code = models.CharField(max_length=10, null=True)
    v_loan_type = models.CharField(max_length=50, null=True)
    m_fees = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_m_fees_term_unit=models.CharField(max_length=1, null=True)
    v_lob_code = models.CharField(max_length=50, null=True)
    v_lv_code = models.CharField(max_length=50, null=True)
    v_country_id = models.CharField(max_length=50, null=True)
    v_credit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_collateral_type = models.CharField(max_length=50, null=True)
    v_loan_desc = models.CharField(max_length=255, null=True)
    v_account_classification_cd = models.CharField(max_length=50, null=True)
    v_gaap_code = models.CharField(max_length=50, null=True)
    v_branch_code = models.CharField(max_length=50, null=True)
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


class FSI_PD_Interpolated(models.Model):
    v_pd_term_structure_id = models.CharField(max_length=100)
    fic_mis_date = models.DateField( null=True)
    v_int_rating_code = models.CharField(max_length=20, null=True, blank=True)  # For Rating bands
    v_delq_band_code = models.CharField(max_length=20, null=True, blank=True)  # For DPD bands
    v_pd_term_structure_type = models.CharField(max_length=3)  # R for Rating, D for DPD
    n_pd_percent = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_per_period_default_prob = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_cumulative_default_prob = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    v_cash_flow_bucket_id = models.IntegerField()
    v_cash_flow_bucket_unit = models.CharField(max_length=1)  # E.g., 'M' for Monthly


    class Meta:
        db_table = 'FSI_PD_Interpolated'


class FSI_PD_Account_Interpolated(models.Model):
    """
    Model to store the interpolated PD values at the account level.
    """
    fic_mis_date = models.DateField()  # MIS date for the record
    v_account_number = models.CharField(max_length=50)  # Account number
    n_pd_percent = models.DecimalField(max_digits=10, decimal_places=6)  # PD percentage
    n_per_period_default_prob = models.DecimalField(max_digits=10, decimal_places=6)  # Marginal PD for the period
    n_cumulative_default_prob = models.DecimalField(max_digits=10, decimal_places=6)  # Cumulative default probability
    v_cash_flow_bucket_id = models.IntegerField()  # Cash flow bucket ID
    v_cash_flow_bucket_unit = models.CharField(max_length=1, choices=[('M', 'Monthly'), ('Q', 'Quarterly'), ('H', 'Half-Yearly'), ('Y', 'Yearly')])  # Cash flow bucket unit (M, Q, H, Y)
   

    class Meta:
        db_table = 'fsi_pd_account_interpolated'
        unique_together = ('fic_mis_date', 'v_account_number', 'v_cash_flow_bucket_id')

    def __str__(self):
        return f"Account {self.v_account_number} - Bucket {self.v_cash_flow_bucket_id}"


class FSI_LLFP_APP_PREFERENCES(models.Model):
    PD_INTERPOLATION_METHOD_CHOICES = [
        ('NL-POISSON', 'Non-Linear Poisson'),
        ('NL-GEOMETRIC', 'Non-Linear Geometric'),
        ('NL-ARITHMETIC', 'Non-Linear Arithmetic'),
        ('EXPONENTIAL_DECAY', 'Exponential Decay'),
        # Add more methods here if needed
    ]

    pd_interpolation_method = models.CharField(
        max_length=100,
        choices=PD_INTERPOLATION_METHOD_CHOICES,
        null=True,
        blank=True,
        default='NL-POISSON'
    )
    n_pd_model_proj_cap = models.IntegerField(default=25)
    llfp_bucket_length = models.CharField(
        max_length=1,
        choices=[
            ('Y', 'Yearly'),
            ('H', 'Half-Yearly'),
            ('Q', 'Quarterly'),
            ('M', 'Monthly'),
        ],
        default='Y'
    )
    # New column to determine interpolation level
    INTERPOLATION_LEVEL_CHOICES = [
        ('ACCOUNT', 'Account Level'),
        ('TERM_STRUCTURE', 'PD Term Structure Level')
    ]
    interpolation_level = models.CharField(
        max_length=20,
        choices=INTERPOLATION_LEVEL_CHOICES,
        default='TERM_STRUCTURE'  # Default to PD Term Structure level
    )
   






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
    V_CASH_FLOW_TYPE = models.CharField(max_length=10)
    V_CCY_CODE = models.CharField(max_length=3)

    class Meta:
        db_table = 'Ldn_expected_cashflow'
        unique_together = ('fic_mis_date', 'v_account_number', 'd_cash_flow_date')


from django.db import models

class Fsi_Interest_Method(models.Model):
    # Define choices for the interest method
    INTEREST_METHOD_CHOICES = [('Simple', 'Simple Interest'), ('Compound', 'Compound Interest'),('Amortized', 'Amortized Interest'),('Floating', 'Floating/Variable Interest'),]
    
    v_interest_method = models.CharField( max_length=50, choices=INTEREST_METHOD_CHOICES,unique=True)
    description = models.TextField(blank=True)  # Optional description for documentation
  

    def __str__(self):
        return self.v_interest_method

    
class FSI_Expected_Cashflow(models.Model):
    fic_mis_date = models.DateField()
    v_account_number = models.CharField(max_length=50)
    n_cash_flow_bucket = models.IntegerField() 
    d_cash_flow_date = models.DateField()
    n_principal_payment = models.DecimalField(max_digits=20, decimal_places=2)
    n_interest_payment = models.DecimalField(max_digits=20, decimal_places=2)
    n_cash_flow_amount = models.DecimalField(max_digits=20, decimal_places=2)
    n_balance = models.DecimalField(max_digits=20, decimal_places=2)
    V_CASH_FLOW_TYPE = models.CharField(max_length=10)
    V_CCY_CODE = models.CharField(max_length=3)

    class Meta:
        db_table = 'FSI_Expected_Cashflow'
        unique_together = ('fic_mis_date', 'v_account_number', 'd_cash_flow_date')

class Ldn_Payment_Schedule(models.Model):
    fic_mis_date = models.DateField(null=False)
    v_account_number = models.CharField(max_length=50, null=False)
    d_payment_date = models.DateField(null=False)
    n_principal_payment_amt = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_interest_payment_amt = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_amount = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    v_payment_type_cd = models.CharField(max_length=20, null=True)  # Payment type code



class Ldn_Recovery_Cashflow(models.Model):
    fic_mis_date = models.DateField()
    v_account_number = models.CharField(max_length=50)
    d_cash_flow_date = models.DateField()
    n_cash_flow_amount = models.DecimalField(max_digits=20, decimal_places=2)
    V_CASH_FLOW_TYPE = models.CharField(max_length=10)
    V_CCY_CODE = models.CharField(max_length=3)

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


class fsi_Financial_Cash_Flow_Cal(models.Model):
    v_account_number = models.CharField(max_length=20, null=False)
    d_cash_flow_date = models.DateField(null=False)
    n_run_skey = models.BigIntegerField(null=False, default=-1)
    fic_mis_date = models.DateField(null=False)
    n_principal_run_off = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_interest_run_off = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_cash_flow_bucket_id = models.IntegerField(null=True)
    n_cash_flow_amount = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_cumulative_loss_rate = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_expected_cash_flow_rate = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_discount_rate = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_discount_factor = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_expected_cash_flow = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_effective_interest_rate = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_lgd_percent = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_expected_cash_flow_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_exposure_at_default = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_forward_expected_loss = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_forward_expected_loss_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_interest_rate_cd = models.BigIntegerField(null=True)
    v_ccy_code = models.CharField(max_length=3, null=True)
    n_cash_shortfall = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_per_period_loss_rate = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_cash_shortfall_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_per_period_loss_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_cash_flow_fwd_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_forward_exposure_amt = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_per_period_impaired_prob = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_cumulative_impaired_prob = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_12m_per_period_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_12m_cumulative_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True)
    n_12m_exp_cash_flow = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_12m_exp_cash_flow_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_12m_cash_shortfall = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_12m_cash_shortfall_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_12m_fwd_expected_loss = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_12m_fwd_expected_loss_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)

    class Meta:
        db_table = 'fsi_Financial_Cash_Flow_Cal'
        unique_together = (('v_account_number', 'd_cash_flow_date', 'fic_mis_date', 'n_run_skey'),)