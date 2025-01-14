from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

class Ldn_Financial_Instrument(models.Model):
    fic_mis_date = models.DateField(null=True)
    v_account_number = models.CharField(max_length=255, null=False)
    v_cust_ref_code = models.CharField(max_length=50, null=True)
    v_prod_code = models.CharField(max_length=50, null=True)
    n_curr_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=False, help_text="Fixed interest rate for the loan")    
    # The changing interest rate (e.g., LIBOR or SOFR)
    n_interest_changing_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, help_text="Changing interest rate value, e.g., LIBOR rate at a specific time")   
    v_interest_freq_unit = models.CharField(max_length=50, null=True)
    v_interest_payment_type = models.CharField(max_length=50, null=True)
    v_day_count_ind= models.CharField(max_length=7,default='30/365', help_text="This column stores the accrual basis code for interest accrual calculation.")
    # New fields for variable rate and fees   
    v_management_fee_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, help_text="Annual management fee rate, e.g., 1%")
    n_wht_percent= models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_effective_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_accrued_interest = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    d_start_date = models.DateField(null=True)
    d_last_payment_date = models.DateField(null=True)
    d_next_payment_date = models.DateField(null=True)
    d_maturity_date = models.DateField(null=False)
    v_amrt_repayment_type = models.CharField(max_length=50, null=True)
    v_amrt_term_unit = models.CharField(max_length=50, null=True)
    n_eop_curr_prin_bal = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_eop_int_bal = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_eop_bal = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    n_curr_payment_recd= models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_collateral_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    n_delinquent_days = models.IntegerField(null=True)
    n_pd_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_lgd_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_ccy_code = models.CharField(max_length=10, null=True)
    v_loan_type = models.CharField(max_length=50, null=True)
    m_fees = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_m_fees_term_unit=models.CharField(max_length=1, null=True)
    v_lob_code = models.CharField(max_length=50, null=True)
    v_lv_code = models.CharField(max_length=50, null=True)
    v_country_id = models.CharField(max_length=50, null=True)
    v_credit_rating_code=models.CharField(max_length=50, null=True)
    v_org_credit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_curr_credit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_acct_rating_movement=models.DecimalField(max_digits=5, decimal_places=2, null=True)
    v_collateral_type = models.CharField(max_length=50, null=True)
    v_loan_desc = models.CharField(max_length=255, null=True)
    v_account_classification_cd = models.CharField(max_length=50, null=True)
    v_gaap_code = models.CharField(max_length=50, null=True)
    v_branch_code = models.CharField(max_length=50, null=True)
    class Meta:
        db_table = 'Ldn_Financial_Instrument'
        unique_together = ('fic_mis_date', 'v_account_number')
        permissions = [
            ("can_load_data", "Can load data"), ("can_view_edit_data", "Can load data"), 
        ]


    
class Ldn_Customer_Rating_Detail(models.Model):
    fic_mis_date = models.DateField(null=True)
    v_party_cd = models.CharField(max_length=50,unique=True)
    v_rating_code = models.CharField(max_length=50)
    v_purpose = models.CharField(max_length=50)  # No choices, just a CharField

    class Meta:
        db_table = 'Ldn_Customer_Rating_Detail'
        unique_together = ('fic_mis_date', 'v_party_cd')

class Ldn_Bank_Product_Info(models.Model):
    fic_mis_date = models.DateField(null=False)
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
    class Meta:
        db_table = 'Ldn_Bank_Product_Info'
        

class FSI_Product_Segment(models.Model):
    segment_id = models.AutoField(primary_key=True)  # Auto-incrementing ID   
    v_prod_segment = models.CharField(max_length=255)
    v_prod_type = models.CharField(max_length=255)
    v_prod_desc = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    

    def __str__(self):
        return f"{self.v_prod_segment} - {self.v_prod_type} - {self.v_prod_desc}"

    class Meta:
        db_table = 'fsi_product_segment'
        constraints = [
            models.UniqueConstraint(fields=['v_prod_segment', 'v_prod_type'], name='unique_segment_type_desc')
        ]

        
class Ldn_Customer_Info(models.Model):
    fic_mis_date = models.DateField()
    v_party_id = models.CharField(max_length=50, unique=True) 
    v_partner_name = models.CharField(max_length=50)
    v_party_type = models.CharField(max_length=50)

    class Meta:
        db_table = 'Ldn_Customer_Info'

class Ldn_PD_Term_Structure(models.Model):
    v_pd_term_structure_id = models.CharField(max_length=100, unique=True)  # This will be auto-filled
    v_pd_term_structure_name = models.ForeignKey(FSI_Product_Segment, on_delete=models.CASCADE)  # Use ForeignKey to select segment by ID
    v_pd_term_structure_desc = models.CharField(max_length=50, editable=False)  # Auto-filled from v_prod_desc in FSI_Product_Segment
    v_pd_term_frequency_unit = models.CharField(max_length=1, choices=[('M', 'Monthly'), ('Q', 'Quarterly'), ('H', 'Half Yearly'), ('Y', 'Yearly'), ('D', 'Daily')])
    v_pd_term_structure_type = models.CharField(max_length=1, choices=[('R', 'Rating'), ('D', 'DPD')])
    fic_mis_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Automatically populate v_pd_term_structure_id and v_pd_term_structure_desc
        product_segment = self.v_pd_term_structure_name  # Reference the FSI_Product_Segment object
        # Fill fields based on the selected segment
        self.v_pd_term_structure_id = product_segment.segment_id  # Use segment_id as ID
        self.v_pd_term_structure_desc = self.v_pd_term_structure_desc = f"{product_segment.v_prod_type} - {product_segment.v_prod_desc}"

        super(Ldn_PD_Term_Structure, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.v_pd_term_structure_name.v_prod_segment} - {self.v_pd_term_structure_desc}"

    class Meta:
        db_table = 'ldn_pd_term_structure'
        unique_together = ('v_pd_term_structure_id', 'fic_mis_date')

class Ldn_PD_Term_Structure_Dtl(models.Model):
    v_pd_term_structure_id = models.ForeignKey('Ldn_PD_Term_Structure',on_delete=models.CASCADE,to_field='v_pd_term_structure_id' )
    fic_mis_date = models.DateField()
    v_credit_risk_basis_cd = models.CharField(max_length=100)
    n_pd_percent = models.DecimalField(max_digits=5, decimal_places=4)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'Ldn_pd_term_structure_dtl'
        unique_together = ('v_pd_term_structure_id', 'fic_mis_date', 'v_credit_risk_basis_cd')


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
    PD_INTERPOLATION_METHOD_CHOICES = [ ('NL-POISSON', 'Non-Linear Poisson'),('NL-GEOMETRIC', 'Non-Linear Geometric'),('NL-ARITHMETIC', 'Non-Linear Arithmetic'),('EXPONENTIAL_DECAY', 'Exponential Decay'),]
    pd_interpolation_method = models.CharField(max_length=100,choices=PD_INTERPOLATION_METHOD_CHOICES,null=True,blank=True,default='NL-POISSON')
    n_pd_model_proj_cap = models.IntegerField(default=25)
    # New column to determine interpolation level
    INTERPOLATION_LEVEL_CHOICES = [('ACCOUNT', 'Account Level'),('TERM_STRUCTURE', 'PD Term Structure Level')]
    interpolation_level = models.CharField( max_length=20,choices=INTERPOLATION_LEVEL_CHOICES,default='TERM_STRUCTURE' )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        db_table = 'FSI_LLFP_APP_PREFERENCES'
   

class Ldn_LGD_Term_Structure(models.Model):
    v_lgd_term_structure_id = models.BigIntegerField( primary_key=True)  # This will be filled automatically
    v_lgd_term_structure_name = models.ForeignKey(FSI_Product_Segment, on_delete=models.CASCADE)  # Use ForeignKey to select segment by ID
    v_lgd_term_structure_desc = models.CharField(max_length=50,blank=True,null=True)  # Auto-filled from v_prod_desc in FSI_Product_Segment
    n_lgd_percent = models.DecimalField(max_digits=5, decimal_places=4)
    fic_mis_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Automatically populate v_lgd_term_structure_id and v_lgd_term_structure_desc
        product_segment = self.v_lgd_term_structure_name  # Reference the FSI_Product_Segment object
        
        # Fill fields based on the selected segment
        self.v_lgd_term_structure_id = product_segment.segment_id  # Use segment_id as ID
        self.v_lgd_term_structure_desc = product_segment.v_prod_desc  # Fill description from the product segment

        super(Ldn_LGD_Term_Structure, self).save(*args, **kwargs)

    class Meta:
        db_table = 'ldn_lgd_term_structure'
        constraints = [
            models.UniqueConstraint(fields=['v_lgd_term_structure_id', 'fic_mis_date'], name='unique_term_structure_id_date')
        ]

class LgdCollateral(models.Model):
    fic_mis_date = models.DateField(null=False)
    v_cust_ref_code = models.CharField(max_length=50, null=False)
    v_ccy_code = models.CharField(max_length=50, blank=True, null=True)
    cash = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    guarantees_corporate = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    guarantees_personal = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    insurance = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    land_and_buildings = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    floating_charge_debenture = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    notarial_bond = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    general_haircuts = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    project_specific_haircuts = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    class Meta:
        db_table = 'lgd_collateral'
        constraints = [
            models.UniqueConstraint(fields=['v_cust_ref_code', 'fic_mis_date'], name='lgd_collateral_pk')
        ]

    def __str__(self):
        return f"{self.v_cust_ref_code} - {self.fic_mis_date}"   
class CollateralLGD(models.Model):
    can_calculate_lgd = models.BooleanField(default=False)  # Yes/No field to allow LGD calculation   
    created_at = models.DateTimeField(auto_now_add=True)  # Record creation timestamp
    updated_at = models.DateTimeField(auto_now=True)  # Record update timestamp
    class Meta:
        db_table = 'collateral_lgd'

    def save(self, *args, **kwargs):
        # Check if there is already one record in the table
        if CollateralLGD.objects.exists() and not self.pk:
            raise ValidationError("Only one instance of CollateralLGD is allowed.")
        
        # If not, save the instance
        super(CollateralLGD, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion of the record
        raise ValidationError("Cannot delete this record. The table must always have one record.")
    
class Ldn_Exchange_Rate(models.Model):
    fic_mis_date = models.DateField()
    v_from_ccy_code = models.CharField(max_length=3)
    v_to_ccy_code = models.CharField(max_length=3)
    n_exchange_rate = models.DecimalField(max_digits=15, decimal_places=6)
    d_last_updated= models.DateField(default=timezone.now)
    class Meta:
        db_table = 'Ldn_exchange_rate'
        unique_together = ('fic_mis_date', 'v_from_ccy_code', 'v_to_ccy_code')

class DimExchangeRateConf(models.Model):
    EXCHANGE_RATE_API_KEY = models.CharField(max_length=255)
    use_on_exchange_rates = models.BooleanField(default=False)
    use_latest_exchange_rates = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        db_table = 'dim_exchange_rate_conf'

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




class Fsi_Interest_Method(models.Model):
    # Define choices for the interest method
    INTEREST_METHOD_CHOICES = [('Simple', 'Simple Interest'), ('Compound', 'Compound Interest'),('Amortized', 'Amortized Interest'),('Floating', 'Floating/Variable Interest'),]
    
    v_interest_method = models.CharField( max_length=50, choices=INTEREST_METHOD_CHOICES,unique=True)
    description = models.TextField(blank=True)  # Optional description for documentation
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        db_table = 'Fsi_Interest_Method'

    
class FSI_Expected_Cashflow(models.Model):
    fic_mis_date = models.DateField()
    v_account_number = models.CharField(max_length=50)
    n_cash_flow_bucket = models.IntegerField() 
    d_cash_flow_date = models.DateField()
    n_principal_payment = models.DecimalField(max_digits=20, decimal_places=2)
    n_interest_payment = models.DecimalField(max_digits=20, decimal_places=2)
    n_cash_flow_amount = models.DecimalField(max_digits=20, decimal_places=2)
    n_balance = models.DecimalField(max_digits=20, decimal_places=2)
    n_accrued_interest = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)  # Accrued interest
    n_exposure_at_default = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True) 
    V_CASH_FLOW_TYPE = models.CharField(max_length=10)
    management_fee_added = models.DecimalField(max_digits=20, decimal_places=2)
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
    class Meta:
        db_table = 'Ldn_Payment_Schedule'
        unique_together = ('fic_mis_date', 'v_account_number', 'd_payment_date')



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
    TABLE_TYPE_CHOICES = [('FACT', 'Fact Table'),('DIM', 'Dimension Table'),('REF', 'Reference Table'),('STG', 'Staging Table'),('OTHER', 'Other'),]
    table_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    table_type = models.CharField(max_length=10, choices=TABLE_TYPE_CHOICES, default='OTHER')

    class Meta:
        db_table = "TableMetadata"


class fsi_Financial_Cash_Flow_Cal(models.Model):
    n_run_skey = models.BigIntegerField(null=False,default=1)
    v_account_number = models.CharField(max_length=20, null=False)
    d_cash_flow_date = models.DateField(null=False)
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
    v_ccy_code = models.CharField(max_length=3, null=True)
    n_cash_shortfall = models.DecimalField(max_digits=22, decimal_places=3, null=True)
    n_cash_shortfall_pv = models.DecimalField(max_digits=22, decimal_places=3, null=True)
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


class FCT_Stage_Determination(models.Model):
    fic_mis_date = models.DateField()
    n_account_number = models.CharField(max_length=50, null=True)
    d_acct_start_date = models.DateField(null=True, blank=True)
    d_last_payment_date = models.DateField(null=True, blank=True)
    d_next_payment_date = models.DateField(null=True, blank=True)
    d_maturity_date = models.DateField(null=True, blank=True)
    n_acct_classification = models.IntegerField(null=True, blank=True)    
    n_cust_ref_code = models.CharField(max_length=50, null=True)
    n_partner_name = models.CharField(max_length=50,null=True, blank=True)
    n_party_type = models.CharField(max_length=50,null=True, blank=True)
      
    # Grouped Interest-related Fields
    n_accrual_basis_code =models.CharField(max_length=7, null=True, blank=True)
    n_curr_interest_rate = models.DecimalField(max_digits=11, decimal_places=6, null=True, blank=True)  # Current interest rate
    n_effective_interest_rate = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)  # Effective interest rate
    v_interest_freq_unit = models.CharField(max_length=1, null=True, blank=True)  # Interest frequency unit
    v_interest_method = models.CharField(max_length=5, null=True, blank=True)  # Interest computation method
    n_accrued_interest = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)  # Accrued interest
    n_rate_chg_min = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)  # Rate change minimum
    # Grouped exposure and balance fields
    n_carrying_amount_ncy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_exposure_at_default = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)  # Added for exposure at default
    n_exposure_limit = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_eop_prin_bal = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)  # Moved next to n_exposure_at_default
    
    # Grouped PD and LGD fields
    n_lgd_percent = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_pd_percent = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    n_twelve_months_orig_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_lifetime_orig_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_twelve_months_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_lifetime_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_pd_term_structure_skey = models.BigIntegerField(null=True, blank=True)
    n_pd_term_structure_name =  models.CharField(max_length=50, editable=False,null=True, blank=True) # Use ForeignKey to select segment by ID
    n_pd_term_structure_desc = models.CharField(max_length=50, editable=False,null=True, blank=True)  # Auto-filled from v_prod_desc in FSI_Product_Segment
    
    n_12m_pd_change = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True) 
    n_rating_impaired_state_skey = models.BigIntegerField(null=True, blank=True)
    v_amrt_repayment_type = models.CharField(max_length=50, null=True)
    n_remain_no_of_pmts = models.BigIntegerField(null=True, blank=True)
    n_amrt_term = models.IntegerField(null=True, blank=True)
    v_amrt_term_unit = models.CharField(max_length=1, null=True, blank=True)
    v_ccy_code = models.CharField(max_length=3, null=True, blank=True)
    v_common_coa_code = models.CharField(max_length=20, null=True, blank=True)
    v_gl_code = models.CharField(max_length=20, null=True, blank=True)
     # Stage-related fields
    n_delinquent_days = models.IntegerField(null=True, blank=True)
    n_delq_band_code =  models.CharField(max_length=50, null=True) 
    n_stage_descr = models.CharField(max_length=50, null=True)
    n_curr_ifrs_stage_skey = models.BigIntegerField(null=True, blank=True)
    n_prev_ifrs_stage_skey = models.BigIntegerField(null=True, blank=True)
    
    # Cooling Period Fields
    d_cooling_start_date = models.DateField(null=True, blank=True)  # Start date of cooling period
    n_target_ifrs_stage_skey = models.BigIntegerField(null=True, blank=True)  # Target stage after cooling period
    n_in_cooling_period_flag = models.BooleanField(default=False,null=True, blank=True)  # True for Yes, False for No
    n_cooling_period_duration = models.IntegerField(null=True, blank=True)  # Duration of the cooling period in days
    
    n_country = models.CharField(max_length=50, null=True)
    n_segment_skey = models.BigIntegerField(null=True, blank=True)
    n_prod_segment = models.CharField(max_length=255,null=True, blank=True)
    n_prod_code = models.CharField(max_length=50, null=True) 
    n_prod_name= models.CharField(max_length=50, null=True) 
    n_prod_type = models.CharField(max_length=50, null=True)
    n_prod_desc = models.CharField(max_length=255,null=True, blank=True)
    n_ecl_compute_ind = models.IntegerField(default=0,null=True, blank=True)
    n_credit_rating_code=models.CharField(max_length=50,null=True, blank=True)
    n_org_credit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    n_curr_credit_score = models.IntegerField(null=True, blank=True)
    n_acct_rating_movement = models.IntegerField(null=True, blank=True)
    n_party_rating_movement = models.IntegerField(null=True, blank=True)
    n_conditionally_cancel_flag = models.IntegerField(null=True, blank=True)
    n_collateral_amount = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)  # Added new column for collateral amount
    n_loan_type = models.CharField(max_length=50,null=True, blank=True)
    class Meta:
        db_table = "fct_stage_determination"  # Updated table name
        unique_together = ('fic_mis_date', 'n_account_number') 


# Credit Rating to Stage Mapping
# Choices for Stages
STAGE_CHOICES = [
    ('Stage 1', 'Stage 1'),
    ('Stage 2', 'Stage 2'),
    ('Stage 3', 'Stage 3')
]

# Choices for Payment Frequency
PAYMENT_FREQUENCY_CHOICES = [
    ('D', 'Daily'),
    ('M', 'Monthly'),
    ('Q', 'Quarterly'),
    ('H', 'Half-Yearly'),
    ('Y', 'Yearly')
]

# Credit Rating to Stage Mapping
class FSI_CreditRating_Stage(models.Model):
    credit_rating = models.CharField(max_length=50, unique=True)  # e.g., "AAA SNP"
    stage = models.CharField(max_length=10, choices=STAGE_CHOICES)  # Use choices for stages
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        db_table = "FSI_CreditRating_Stage"  # Updated table name
# Days Past Due to Stage Mapping
class FSI_DPD_Stage_Mapping(models.Model):
    payment_frequency = models.CharField(max_length=50, choices=PAYMENT_FREQUENCY_CHOICES)  # Use choices for payment frequency
    stage_1_threshold = models.IntegerField()  # DPD days for Stage 1
    stage_2_threshold = models.IntegerField()  # DPD days for Stage 2
    stage_3_threshold = models.IntegerField()  # DPD days for Stage 3
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        db_table = "FSI_DPD_Stage_Mapping"  # Updated table name


# Choices for Payment Frequency
AMRT_CHOICES = [
    ('D', 'Daily'),
    ('M', 'Monthly'),
    ('Q', 'Quarterly'),
    ('H', 'Half-Yearly'),
    ('Y', 'Yearly')
]
class CoolingPeriodDefinition(models.Model):
    v_amrt_term_unit = models.CharField(max_length=1,choices=AMRT_CHOICES)  # M (Monthly), Q (Quarterly), H (Half-Yearly), Y (Yearly)
    n_cooling_period_days = models.IntegerField()  # Number of days for cooling period
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'FSI_Cooling_Period_Definition'

class Dim_Delinquency_Band(models.Model):
    date = models.DateField(default=timezone.now) # Date field for FIC_MIS_DATE
    n_delq_band_code = models.CharField(max_length=20,primary_key=True)  # Primary Key for N_DELQ_BAND_CODE
    v_delq_band_desc = models.CharField(max_length=20,null=True, blank=True)  # VARCHAR2(60 CHAR) for V_DELQ_BAND_DESC
    n_delq_lower_value = models.PositiveIntegerField()  # Number(5,0) for N_DELQ_LOWER_VALUE
    n_delq_upper_value = models.PositiveIntegerField()  # Number(5,0) for N_DELQ_UPPER_VALUE
    v_amrt_term_unit = models.CharField(max_length=1, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'dim_delinquency_band'  # Custom table name

    def __str__(self):
        return f"{self.n_delq_band_code} - {self.v_delq_band_desc}"
    
class Credit_Rating_Code_Band(models.Model):
    date = models.DateField(default=timezone.now)
    v_rating_code = models.CharField(max_length=10, primary_key=True)  # Primary Key for Credit Rating Code
    v_rating_desc = models.CharField(max_length=100)  # Description for the rating code
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'dim_credit_rating_code_band'  # Custom table name

    def __str__(self):
        return f"{self.v_rating_code} - {self.v_rating_desc}"
    
class Dim_Run(models.Model):
    date = models.DateField(default=timezone.now)
    latest_run_skey = models.BigIntegerField(default=1)

    class Meta:
        db_table = 'dim_run'


class FCT_Reporting_Lines(models.Model):
    n_run_key = models.BigIntegerField(null=True, blank=True)
    fic_mis_date = models.DateField()
    n_account_number = models.CharField(max_length=50, null=True)
    d_acct_start_date = models.DateField(null=True, blank=True)
    d_last_payment_date = models.DateField(null=True, blank=True)
    d_next_payment_date = models.DateField(null=True, blank=True)
    d_maturity_date = models.DateField(null=True, blank=True)
    n_acct_classification = models.IntegerField(null=True, blank=True)    
    n_cust_ref_code = models.CharField(max_length=50, null=True)
    n_partner_name = models.CharField(max_length=50,null=True, blank=True)
    n_party_type = models.CharField(max_length=50,null=True, blank=True)
      
    # Grouped Interest-related Fields
    n_accrual_basis_code = models.CharField(max_length=7, null=True, blank=True)
    n_curr_interest_rate = models.DecimalField(max_digits=11, decimal_places=6, null=True, blank=True)
    n_effective_interest_rate = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    v_interest_freq_unit = models.CharField(max_length=1, null=True, blank=True)
    v_interest_method = models.CharField(max_length=5, null=True, blank=True)
    n_accrued_interest = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_rate_chg_min = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Grouped exposure and balance fields
    v_ccy_code = models.CharField(max_length=3, null=True, blank=True)
    n_carrying_amount_ncy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_carrying_amount_rcy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_exposure_at_default_ncy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_exposure_at_default_rcy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True) 
    n_pv_of_cash_flows = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_write_off_amount = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)  
    n_expected_recovery = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)  
    # New Fields
    n_lifetime_ecl_ncy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_lifetime_ecl_rcy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_12m_ecl_ncy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_12m_ecl_rcy = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)   
    # Grouped PD and LGD fields
    n_lgd_percent = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_pd_percent = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    n_twelve_months_orig_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_lifetime_orig_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_twelve_months_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_lifetime_pd = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True)
    n_pd_term_structure_skey = models.BigIntegerField(null=True, blank=True)
    n_pd_term_structure_name =  models.CharField(max_length=50, editable=False,null=True, blank=True) 
    n_pd_term_structure_desc = models.CharField(max_length=50, editable=False,null=True, blank=True)
    
    n_12m_pd_change = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    v_amrt_repayment_type = models.CharField(max_length=50, null=True)
    n_remain_no_of_pmts = models.BigIntegerField(null=True, blank=True)
    n_amrt_term = models.IntegerField(null=True, blank=True)
    v_amrt_term_unit = models.CharField(max_length=1, null=True, blank=True)
    
    
    # Stage-related fields
    n_delinquent_days = models.IntegerField(null=True, blank=True)
    n_delq_band_code = models.CharField(max_length=50, null=True)
    n_stage_descr = models.CharField(max_length=50, null=True)
    n_curr_ifrs_stage_skey = models.BigIntegerField(null=True, blank=True)
    n_prev_ifrs_stage_skey = models.BigIntegerField(null=True, blank=True)
    
    # Cooling Period Fields
    d_cooling_start_date = models.DateField(null=True, blank=True)
    n_target_ifrs_stage_skey = models.BigIntegerField(null=True, blank=True)
    n_in_cooling_period_flag = models.BooleanField(default=False,null=True, blank=True)
    n_cooling_period_duration = models.IntegerField(null=True, blank=True)
    
    n_country = models.CharField(max_length=50, null=True)
    n_segment_skey = models.BigIntegerField(null=True, blank=True)
    n_prod_segment = models.CharField(max_length=255,null=True, blank=True)
    n_prod_code = models.CharField(max_length=50, null=True)
    n_prod_name = models.CharField(max_length=50, null=True)
    n_prod_type = models.CharField(max_length=50, null=True)
    n_prod_desc = models.CharField(max_length=255,null=True, blank=True)
    n_credit_rating_code = models.CharField(max_length=50, null=True)
    n_org_credit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    n_curr_credit_score = models.IntegerField(null=True, blank=True)
    n_acct_rating_movement = models.IntegerField(null=True, blank=True)
    n_party_rating_movement = models.IntegerField(null=True, blank=True)
    n_conditionally_cancel_flag = models.IntegerField(null=True, blank=True)
    n_collateral_amount = models.DecimalField(max_digits=22, decimal_places=3, null=True, blank=True)
    n_loan_type = models.CharField(max_length=50, null=True)
    
    class Meta:
        db_table = 'fct_reporting_lines'  # Custom table name
        constraints = [
            models.UniqueConstraint(fields=['fic_mis_date', 'n_account_number', 'n_run_key'], name='unique_fct_reporting_lines')
        ]
        permissions = [
            ("can_view_reports", "Can view reports"), ("can_select_result_columns", "Can select columns"), 
        ]

class ECLMethod(models.Model):
    METHOD_CHOICES = [
        ('forward_exposure', 'Forward Exposure Methodology'),
        ('cash_flow', 'Cash Flow Calculations Methodology'),
        ('simple_ead', 'Simple EAD Methodology')
    ]
    
    method_name = models.CharField(max_length=50, choices=METHOD_CHOICES, unique=True, default='forward_exposure')
    uses_discounting = models.BooleanField(default=True)  # Default to 'yes' for discounting (EIR)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if ECLMethod.objects.exists() and not self.pk:
            raise ValidationError("You can only have one ECLMethod instance.")
        super(ECLMethod, self).save(*args, **kwargs)

    def __str__(self):
        return self.get_method_name_display()

    class Meta:
        db_table = 'dim_ecl_method'

class ReportColumnConfig(models.Model):
    report_name = models.CharField(max_length=20,default='default_report')
    selected_columns = models.JSONField()  # Store the selected columns as a list in JSON format
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'dim_report_column_map'

    def __str__(self):
        return f"Report: {self.report_name}"
    


class Function(models.Model):
    function_name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'dim_function'

    def __str__(self):
        return self.function_name
    
class Process(models.Model):
    process_name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'dim_process'

    def __str__(self):
        return self.process_name

class RunProcess(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='run_processes')
    function = models.ForeignKey(Function, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()  # Order in which the function will be executed
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['order']  # Ensures the functions are executed in the specified order
        db_table = 'dim_process_dtl'

    def __str__(self):
        return f"{self.process.process_name} - {self.function.function_name} - Order: {self.order}"
    
class FunctionExecutionStatus(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    function = models.ForeignKey(Function, on_delete=models.CASCADE)
    execution_start_date = models.DateTimeField(auto_now_add=True)  # Renamed from execution_date to execution_start_date
    execution_end_date = models.DateTimeField(null=True, blank=True)  # New field for when the function finishes execution
    duration = models.DurationField(null=True, blank=True)
    execution_order = models.PositiveIntegerField(null=True)
    reporting_date = models.DateField(null=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Ongoing', 'Ongoing'), ('Success', 'Success'), ('Failed', 'Failed')], default='Pending')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)  # Link to the User model
    # Track process execution instances
    process_run_id = models.CharField(max_length=50)  # Combined process_id, execution_date, and run_count
    run_count = models.PositiveIntegerField()  # Tracks how many times this process has been executed on a particular date

    class Meta:
        db_table = 'dim_function_execution_status'
        ordering = ['run_count', 'execution_start_date']
        constraints = [
            models.UniqueConstraint(fields=['execution_start_date', 'process_run_id','function'], name='unique_execution_process')
        ]
        permissions = [
            ("can_execute_run", "Can execute"), ("can_monitor", "Can monitor"),("can_cancel_run", "Can cancel run"),
        ]
      

    def __str__(self):
        return f"{self.process.process_name} - {self.function.function_name} - {self.status}"
    
    
class Log(models.Model):
    LOG_LEVEL_CHOICES = [
        ('INFO', 'Info'),
        ('ERROR', 'Error'),
    ]
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    function_name=models.CharField(max_length=50, choices=LOG_LEVEL_CHOICES)
    log_level = models.CharField(max_length=50, choices=LOG_LEVEL_CHOICES)
    message = models.TextField()
    status = models.CharField(max_length=10, default='SUCCESS')

    class Meta:
        verbose_name = 'Log'
        verbose_name_plural = 'Logs'
        ordering = ['-timestamp']
        db_table = 'dim_massage_logs'

class CurrencyCode(models.Model):

    code = models.CharField(max_length=3, unique=True)  # Currency code, e.g., USD, EUR
    description = models.CharField(max_length=100)  # Description of the currency, e.g., United States Dollar

    class Meta:
        db_table = 'dim_currency_code'

    def __str__(self):
        return f"{self.code} - {self.description}"
    

class ReportingCurrency(models.Model):
 
    currency_code = models.ForeignKey(CurrencyCode, on_delete=models.CASCADE)

    def clean(self):
        if ReportingCurrency.objects.exists() and not self.pk:
            raise ValidationError("You can only have one reporting currency.")

    def save(self, *args, **kwargs):
        self.clean()  # Validate the rule before saving
        super(ReportingCurrency, self).save(*args, **kwargs)

    class Meta:
        db_table = 'dim_reporting_currency_code'

    def __str__(self):
        return self.currency_code.code


 