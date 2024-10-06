import math
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from ..models import *
from ..Functions import save_log


def perform_interpolation(mis_date):
    """
    Perform PD interpolation based on the interpolation level set in preferences.
    :param mis_date: Date in 'YYYY-MM-DD' format.
    :return: String, status of the interpolation process ('1' for success, '0' for failure').
    """
    try:
        preferences = FSI_LLFP_APP_PREFERENCES.objects.first()
        if preferences is None:
            print("No preferences found.")
            return '0'

        interpolation_level = preferences.interpolation_level

        if interpolation_level == 'ACCOUNT':
            print("Performing account-level interpolation")
            return pd_interpolation_account_level(mis_date)
        elif interpolation_level == 'TERM_STRUCTURE':
            print("Performing term structure-level interpolation")
            return pd_interpolation(mis_date)
        else:
            print(f"Unknown interpolation level: {interpolation_level}")
            return '0'
    except Exception as e:
        print(f"Error during interpolation: {e}")
        return '0'

# Term structure interpolation functions
def pd_interpolation(mis_date):
    """
    Perform PD interpolation based on the term structure details and preferences.
    """
    try:
        preferences = FSI_LLFP_APP_PREFERENCES.objects.first()
        pd_interpolation_method = preferences.pd_interpolation_method or 'NL-POISSON'
        pd_model_proj_cap = preferences.n_pd_model_proj_cap

        # Filter Ldn_PD_Term_Structure_Dtl by the mis_date
        term_structure_details = Ldn_PD_Term_Structure_Dtl.objects.filter(fic_mis_date=mis_date)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_interpolation, detail, pd_model_proj_cap, pd_interpolation_method)
                for detail in term_structure_details
            ]

            for future in futures:
                future.result()

        return '1'

    except Exception as e:
        print(f"Error during interpolation: {e}")
        return '0'

def process_interpolation(detail, pd_model_proj_cap, pd_interpolation_method):
    """
    Process PD interpolation for a given term structure detail.
    """
    credit_risk_band = detail.v_credit_risk_basis_cd
    print(f"Processing interpolation for credit risk band: {credit_risk_band}")

    bucket_length = detail.v_pd_term_structure_id.v_pd_term_frequency_unit

    # Set the bucket frequency and cash flow bucket unit based on bucket length
    if bucket_length == 'M':
        bucket_frequency = 12
        cash_flow_bucket_unit = 'M'
    elif bucket_length == 'H':
        bucket_frequency = 2
        cash_flow_bucket_unit = 'H'
    elif bucket_length == 'Q':
        bucket_frequency = 4
        cash_flow_bucket_unit = 'Q'
    else:
        bucket_frequency = 1
        cash_flow_bucket_unit = 'Y'

    # Delete existing records with the same fic_mis_date before inserting new ones
    FSI_PD_Interpolated.objects.filter(fic_mis_date=detail.fic_mis_date).delete()

    if pd_interpolation_method == 'NL-POISSON':
        interpolate_poisson(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'NL-GEOMETRIC':
        interpolate_geometric(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'NL-ARITHMETIC':
        interpolate_arithmetic(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'EXPONENTIAL_DECAY':
        interpolate_exponential_decay(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit)

# Poisson Interpolation
def interpolate_poisson(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit):
    periods = bucket_frequency * pd_model_proj_cap
    pd_percent = float(detail.n_pd_percent)
    cumulative_pd = 0

    for bucket in range(1, periods + 1):
        marginal_pd = 1 - math.exp(math.log(1 - pd_percent) / bucket_frequency)
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Interpolated.objects.create(
            v_pd_term_structure_id=detail.v_pd_term_structure_id.v_pd_term_structure_id,
            fic_mis_date=detail.v_pd_term_structure_id.fic_mis_date,
            v_int_rating_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'R' else None,
            v_delq_band_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'D' else None,
            v_pd_term_structure_type=detail.v_pd_term_structure_id.v_pd_term_structure_type,
            n_pd_percent=detail.n_pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit
        )

def interpolate_geometric(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit):
    """
    Perform Geometric interpolation for a given term structure detail.
    """
    periods = bucket_frequency * pd_model_proj_cap
    pd_percent = float(detail.n_pd_percent)
    cumulative_pd = 0

    for bucket in range(1, periods + 1):
        marginal_pd = (1 + pd_percent) ** (1 / bucket_frequency) - 1
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Interpolated.objects.create(
            v_pd_term_structure_id=detail.v_pd_term_structure_id.v_pd_term_structure_id,
            fic_mis_date=detail.v_pd_term_structure_id.fic_mis_date,
            v_int_rating_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'R' else None,
            v_delq_band_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'D' else None,
            v_pd_term_structure_type=detail.v_pd_term_structure_id.v_pd_term_structure_type,
            n_pd_percent=detail.n_pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit
        )

def interpolate_arithmetic(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit):
    """
    Perform Arithmetic interpolation for a given term structure detail.
    """
    periods = bucket_frequency * pd_model_proj_cap
    pd_percent = detail.n_pd_percent
    pd_percent=float(pd_percent)
    cumulative_pd = 0
    marginal_pd = pd_percent / bucket_frequency

    for bucket in range(1, periods + 1):
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Interpolated.objects.create(
            v_pd_term_structure_id=detail.v_pd_term_structure_id.v_pd_term_structure_id,
            fic_mis_date=detail.v_pd_term_structure_id.fic_mis_date,
            v_int_rating_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'R' else None,
            v_delq_band_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'D' else None,
            v_pd_term_structure_type=detail.v_pd_term_structure_id.v_pd_term_structure_type,
            n_pd_percent=detail.n_pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit
        )

def interpolate_exponential_decay(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit):
    """
    Perform Exponential Decay interpolation for a given term structure detail.
    """
    periods = bucket_frequency * pd_model_proj_cap
    pd_percent = float(detail.n_pd_percent)

    if cash_flow_bucket_unit == 'Q':
        pd_percent = 1 - (1 - pd_percent) ** (1 / 4)
    elif cash_flow_bucket_unit == 'H':
        pd_percent = 1 - (1 - pd_percent) ** (1 / 2)
    elif cash_flow_bucket_unit == 'M':
        pd_percent = 1 - (1 - pd_percent) ** (1 / 12)

    cumulative_pd = 0
    population_remaining = 1

    for bucket in range(1, periods + 1):
        marginal_pd = round(population_remaining * pd_percent, 4)
        population_remaining = round(population_remaining - marginal_pd, 4)
        cumulative_pd = round(cumulative_pd + marginal_pd, 4)

        FSI_PD_Interpolated.objects.create(
            v_pd_term_structure_id=detail.v_pd_term_structure_id.v_pd_term_structure_id,
            fic_mis_date=detail.v_pd_term_structure_id.fic_mis_date,
            v_int_rating_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'R' else None,
            v_delq_band_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'D' else None,
            v_pd_term_structure_type=detail.v_pd_term_structure_id.v_pd_term_structure_type,
            n_pd_percent=detail.n_pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit
        )

        # Stop the loop if the population reaches 0
        if population_remaining <= 0:
            break

# Account-level interpolation functions
def pd_interpolation_account_level(mis_date):
    """
    Perform PD interpolation at the account level based on the PD details and cashflow buckets.
    """
    try:
        # Fetch accounts from the Ldn_Financial_Instrument table for the given mis_date
        accounts = Ldn_Financial_Instrument.objects.filter(fic_mis_date=mis_date)

        if not accounts.exists():
            print(f"No accounts found for mis_date {mis_date}.")
            return '0'  # Return '0' if no accounts are found


        # Use ThreadPoolExecutor to run interpolation in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_account_interpolation, account, mis_date)
                for account in accounts
            ]

            for future in futures:
                future.result()

        return '1'

    except Exception as e:
        print(f"Error during account-level interpolation: {e}")
        return '0'

def process_account_interpolation(account, mis_date):
    """
    Process PD interpolation for a given account-level PD detail.
    """
    account_number = account.v_account_number
    print(f"Processing interpolation for account: {account_number}")

    try:
        pd_percent = Ldn_Financial_Instrument.objects.get(fic_mis_date=account.fic_mis_date, v_account_number=account_number).n_pd_percent
        pd_percent =float(pd_percent)
    except Ldn_Financial_Instrument.DoesNotExist:
        print(f"No PD found for account {account_number}")
        return

    max_bucket = FSI_Expected_Cashflow.objects.filter(v_account_number=account_number, fic_mis_date=mis_date).aggregate(max_bucket=models.Max('n_cash_flow_bucket'))['max_bucket']
    if max_bucket is None:
        print(f"No cashflow buckets found for account {account_number}")
        return

    bucket_length = account.v_interest_freq_unit
    if bucket_length == 'M':
        bucket_frequency = 12
        cash_flow_bucket_unit = 'M'
    elif bucket_length == 'H':
        bucket_frequency = 2
        cash_flow_bucket_unit = 'H'
    elif bucket_length == 'Q':
        bucket_frequency = 4
        cash_flow_bucket_unit = 'Q'
    else:
        bucket_frequency = 1
        cash_flow_bucket_unit = 'Y'

    # Delete existing records with the same fic_mis_date and account number before inserting new ones
    FSI_PD_Account_Interpolated.objects.filter(fic_mis_date=account.fic_mis_date, v_account_number=account_number).delete()

    preferences = FSI_LLFP_APP_PREFERENCES.objects.first()
    pd_interpolation_method = preferences.pd_interpolation_method or 'NL-POISSON'

    if pd_interpolation_method == 'NL-POISSON':
        interpolate_poisson_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'NL-GEOMETRIC':
        interpolate_geometric_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'NL-ARITHMETIC':
        interpolate_arithmetic_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'EXPONENTIAL_DECAY':
        interpolate_exponential_decay_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit)

def interpolate_poisson_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit):
    """
    Perform Poisson interpolation for a given account-level PD detail.
    """
    cumulative_pd = 0
    for bucket in range(1, max_bucket + 1):
        marginal_pd = 1 - math.exp(math.log(1 - pd_percent) / bucket_frequency)
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Account_Interpolated.objects.create(
            fic_mis_date=account.fic_mis_date,
            v_account_number=account.v_account_number,
            n_pd_percent=pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit
        )

def interpolate_geometric_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit):
    """
    Perform Geometric interpolation for a given account-level PD detail.
    """
    cumulative_pd = 0
    for bucket in range(1, max_bucket + 1):
        marginal_pd = (1 + pd_percent) ** (1 / bucket_frequency) - 1
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Account_Interpolated.objects.create(
            fic_mis_date=account.fic_mis_date,
            v_account_number=account.v_account_number,
            n_pd_percent=pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit
        )

def interpolate_arithmetic_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit):
    """
    Perform Arithmetic interpolation for a given account-level PD detail.
    """
    cumulative_pd = 0
    marginal_pd = pd_percent / bucket_frequency
    for bucket in range(1, max_bucket + 1):
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Account_Interpolated.objects.create(
            fic_mis_date=account.fic_mis_date,
            v_account_number=account.v_account_number,
            n_pd_percent=pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit
        )

def interpolate_exponential_decay_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit):
    """
    Perform Exponential Decay interpolation for a given account-level PD detail.
    """
    if cash_flow_bucket_unit == 'Q':
        pd_percent = 1 - (1 - pd_percent) ** (1 / 4)
    elif cash_flow_bucket_unit == 'H':
        pd_percent = 1 - (1 - pd_percent) ** (1 / 2)
    elif cash_flow_bucket_unit == 'M':
        pd_percent = 1 - (1 - pd_percent) ** (1 / 12)

    cumulative_pd = 0
    population_remaining = 1

    for bucket in range(1, max_bucket + 1):
        marginal_pd = round(population_remaining * pd_percent, 4)
        population_remaining = round(population_remaining - marginal_pd, 4)
        cumulative_pd = round(cumulative_pd + marginal_pd, 4)

        FSI_PD_Account_Interpolated.objects.create(
            fic_mis_date=account.fic_mis_date,
            v_account_number=account.v_account_number,
            n_pd_percent=pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit
        )

        if population_remaining <= 0:
            break
