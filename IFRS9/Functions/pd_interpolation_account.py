import math
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from ..models import *
from ..Functions import save_log


def pd_interpolation(mis_date):
    """
    Perform PD interpolation based on the term structure details and preferences.
    :param mis_date: Date in 'YYYY-MM-DD' format.
    :return: String, status of the interpolation process ('1' for success, '0' for failure').
    """
    try:
        # Fetch preferences from FSI_LLFP_APP_PREFERENCES
        preferences = FSI_LLFP_APP_PREFERENCES.objects.first()
        if not preferences:
            print("No preferences found in FSI_LLFP_APP_PREFERENCES.")
            return '0'  # Return '0' if no preferences are found

        pd_interpolation_method = preferences.pd_interpolation_method or 'NL-POISSON'
        pd_model_proj_cap = preferences.n_pd_model_proj_cap
        bucket_length = preferences.llfp_bucket_length  # e.g., 'M' for Monthly, 'Y' for Yearly, etc.

        # Set the bucket frequency and cash flow bucket unit based on bucket length
        if bucket_length == 'M':
            bucket_frequency = 12  # Yearly -> Monthly conversion
            cash_flow_bucket_unit = 'M'
        elif bucket_length == 'H':
            bucket_frequency = 6  # Half-yearly -> Monthly
            cash_flow_bucket_unit = 'H'
        elif bucket_length == 'Q':
            bucket_frequency = 3  # Quarterly -> Monthly
            cash_flow_bucket_unit = 'Q'
        else:
            bucket_frequency = 1  # Default is yearly
            cash_flow_bucket_unit = 'Y'

        # Filter Ldn_PD_Term_Structure_Dtl by the mis_date
        term_structure_details = Ldn_PD_Term_Structure_Dtl.objects.filter(fic_mis_date=mis_date)

        if not term_structure_details.exists():
            print(f"No term structure details found for mis_date {mis_date}.")
            return '0'  # Return '0' if no details are found

        # Use ThreadPoolExecutor to run interpolation in parallel
        with ThreadPoolExecutor() as executor:
            # Submit each detail for parallel processing
            futures = [
                executor.submit(process_interpolation, detail, bucket_frequency, pd_model_proj_cap, pd_interpolation_method, cash_flow_bucket_unit)
                for detail in term_structure_details
            ]

            # Wait for all threads to complete
            for future in futures:
                try:
                    future.result()  # This will raise any exceptions encountered in the threads
                except Exception as exc:
                    print(f"Error occurred in thread: {exc}")
                    return '0'  # Return '0' if any thread encounters an error

        return '1'  # Return '1' on successful completion

    except Exception as e:
        print(f"Error during interpolation: {e}")
        return '0'  # Return '0' in case of any exception



def process_interpolation(detail, bucket_frequency, pd_model_proj_cap, pd_interpolation_method, cash_flow_bucket_unit):
    """
    Process PD interpolation for a given term structure detail.
    """
    credit_risk_band = detail.v_credit_risk_basis_cd
    print(f"Processing interpolation for credit risk band: {credit_risk_band}")

    # Delete existing records with the same fic_mis_date before inserting new ones
    FSI_PD_Interpolated.objects.filter(fic_mis_date=detail.fic_mis_date).delete()

    # Apply the appropriate interpolation method
    if pd_interpolation_method == 'NL-POISSON':
        interpolate_poisson(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'NL-GEOMETRIC':
        interpolate_geometric(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'NL-ARITHMETIC':
        interpolate_arithmetic(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit)
    elif pd_interpolation_method == 'EXPONENTIAL_DECAY':
        interpolate_exponential_decay(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit)


def interpolate_poisson(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit):
    """
    Perform Poisson interpolation for a given term structure detail.
    """
    periods = bucket_frequency * pd_model_proj_cap
    pd_percent = detail.n_pd_percent

    cumulative_pd = 0
    for bucket in range(1, periods + 1):
        marginal_pd = 1 - math.exp(math.log(1 - pd_percent) / bucket_frequency)
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Interpolated.objects.create(
            fic_mis_date=detail.v_pd_term_structure_id.fic_mis_date,
            v_int_rating_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'R' else None,
            v_delq_band_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'D' else None,
            v_pd_term_structure_type=detail.v_pd_term_structure_id.v_pd_term_structure_type,
            n_pd_percent=detail.n_pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit,
            d_record_start_date=detail.fic_mis_date,
            d_record_end_date=detail.fic_mis_date
        )


def interpolate_geometric(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit):
    """
    Perform Geometric interpolation for a given term structure detail.
    """
    print('Processing Geometric Interpolation')
    periods = bucket_frequency * pd_model_proj_cap
    pd_percent = float(detail.n_pd_percent)  # Convert to float

    cumulative_pd = 0
    for bucket in range(1, periods + 1):
        # Perform geometric-based marginal PD calculation
        marginal_pd = (1 + pd_percent) ** (1 / float(bucket_frequency)) - 1  # Ensure float division
        print(marginal_pd)
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Interpolated.objects.create(
            fic_mis_date=detail.v_pd_term_structure_id.fic_mis_date,
            v_int_rating_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'R' else None,
            v_delq_band_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'D' else None,
            v_pd_term_structure_type=detail.v_pd_term_structure_id.v_pd_term_structure_type,
            n_pd_percent=detail.n_pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit,
            d_record_start_date=detail.fic_mis_date,
            d_record_end_date=detail.fic_mis_date
        )

def interpolate_arithmetic(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit):
    """
    Perform Arithmetic interpolation for a given term structure detail.
    """
    periods = bucket_frequency * pd_model_proj_cap
    pd_percent = detail.n_pd_percent

    cumulative_pd = 0
    marginal_pd = pd_percent / bucket_frequency
    for bucket in range(1, periods + 1):
        cumulative_pd = 1 - (1 - cumulative_pd) * (1 - marginal_pd)

        FSI_PD_Interpolated.objects.create(
            fic_mis_date=detail.v_pd_term_structure_id.fic_mis_date,
            v_int_rating_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'R' else None,
            v_delq_band_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'D' else None,
            v_pd_term_structure_type=detail.v_pd_term_structure_id.v_pd_term_structure_type,
            n_pd_percent=detail.n_pd_percent,
            n_per_period_default_prob=marginal_pd,
            n_cumulative_default_prob=cumulative_pd,
            v_cash_flow_bucket_id=bucket,
            v_cash_flow_bucket_unit=cash_flow_bucket_unit,
            d_record_start_date=detail.fic_mis_date,
            d_record_end_date=detail.fic_mis_date
        )

def interpolate_exponential_decay(detail, bucket_frequency, pd_model_proj_cap, cash_flow_bucket_unit):
    """
    Perform Exponential Decay interpolation for a given term structure detail.
    This follows the cumulative default logic as demonstrated in the spreadsheet.
    """
    # Number of periods to calculate (total buckets based on projection capacity and frequency)
    periods = bucket_frequency * pd_model_proj_cap
    pd_percent = float(detail.n_pd_percent)  # Convert PD percent to float

    if cash_flow_bucket_unit == 'Q':  # Quarterly
        pd_percent= 1 - (1 - pd_percent) ** (1 / 4)
    elif cash_flow_bucket_unit == 'H':  # Half-yearly
        pd_percent= 1 - (1 - pd_percent) ** (1 / 2)
    elif cash_flow_bucket_unit == 'M':  # Monthly
        pd_percent= 1 - (1 - pd_percent) ** (1 / 12)
    else:  # Yearly (No conversion needed)
        return pd_percent

    cumulative_pd = 0  # Initial cumulative PD
    population_remaining = 1  # Start with 100% population
    
    # Create an initial bucket entry for bucket 0, like in the CTE's initial part
    FSI_PD_Interpolated.objects.create(
        fic_mis_date=detail.v_pd_term_structure_id.fic_mis_date,
        v_int_rating_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'R' else None,
        v_delq_band_code=detail.v_credit_risk_basis_cd if detail.v_pd_term_structure_id.v_pd_term_structure_type == 'D' else None,
        v_pd_term_structure_type=detail.v_pd_term_structure_id.v_pd_term_structure_type,
        n_pd_percent=detail.n_pd_percent,
        n_per_period_default_prob=0,
        n_cumulative_default_prob=0,
        v_cash_flow_bucket_id=0,
        v_cash_flow_bucket_unit=cash_flow_bucket_unit,
        d_record_start_date=detail.fic_mis_date,
        d_record_end_date=detail.fic_mis_date
    )

    # Loop through each bucket, calculating the marginal PD and adjusting the population
    for bucket in range(1, periods + 1):
        # Calculate default for the current bucket using the population from the previous bucket
        marginal_pd = round(population_remaining * pd_percent, 4)  # This mirrors the formula in the spreadsheet
        
        # Calculate cumulative impaired probability (remaining population)
        population_remaining = round(population_remaining - marginal_pd, 4)

        # Calculate cumulative default probability
        cumulative_pd = round(cumulative_pd + marginal_pd, 4)

        # Save interpolated values for the current bucket
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
            v_cash_flow_bucket_unit=cash_flow_bucket_unit,
            d_record_start_date=detail.fic_mis_date,
            d_record_end_date=detail.fic_mis_date
        )

        # Stop the loop if the population reaches 0
        if population_remaining <= 0:
            break




def pd_interpolation_account_level(mis_date):
    """
    Perform PD interpolation at the account level based on the PD details and cashflow buckets.
    :param mis_date: Date in 'YYYY-MM-DD' format.
    :return: String, status of the interpolation process ('1' for success, '0' for failure').
    """
    try:
        # Fetch accounts from the Ldn_Financial_Instrument table for the given mis_date
        accounts = Ldn_Financial_Instrument.objects.filter(fic_mis_date=mis_date)

        if not accounts.exists():
            print(f"No accounts found for mis_date {mis_date}.")
            return '0'  # Return '0' if no accounts are found

        # Use ThreadPoolExecutor to run interpolation in parallel
        with ThreadPoolExecutor() as executor:
            # Submit each account for parallel processing
            futures = [
                executor.submit(process_account_interpolation, account, mis_date)
                for account in accounts
            ]

            # Wait for all threads to complete
            for future in futures:
                try:
                    future.result()  # This will raise any exceptions encountered in the threads
                except Exception as exc:
                    print(f"Error occurred in thread: {exc}")
                    return '0'  # Return '0' if any thread encounters an error

        return '1'  # Return '1' on successful completion

    except Exception as e:
        print(f"Error during account-level interpolation: {e}")
        return '0'  # Return '0' in case of any exception



def process_account_interpolation(account, mis_date):
    """
    Process PD interpolation for a given account-level PD detail.
    """
    account_number = account.v_account_number
    print(f"Processing interpolation for account: {account_number}")

    # Fetch PD for this account from the Ldn_Financial_Instrument table
    try:
        pd_percent = Ldn_Financial_Instrument.objects.get(fic_mis_date=account.fic_mis_date, v_account_number=account_number).n_pd_percent
    except Ldn_Financial_Instrument.DoesNotExist:
        print(f"No PD found for account {account_number}")
        return

    # Fetch the maximum number of buckets from the cashflow table for this account and mis_date
    max_bucket = FSI_Expected_Cashflow.objects.filter(v_account_number=account_number, fic_mis_date=mis_date).aggregate(max_bucket=models.Max('n_cash_flow_bucket'))['max_bucket']
    if max_bucket is None:
        print(f"No cashflow buckets found for account {account_number}")
        return

    # Fetch the bucket frequency and cash flow bucket unit from V_INTEREST_FREQ_UNIT in Ldn_Financial_Instrument
    bucket_length = account.v_interest_freq_unit
    if bucket_length == 'M':
        bucket_frequency = 12  # Yearly -> Monthly conversion
        cash_flow_bucket_unit = 'M'
    elif bucket_length == 'H':
        bucket_frequency = 6  # Half-yearly -> Monthly
        cash_flow_bucket_unit = 'H'
    elif bucket_length == 'Q':
        bucket_frequency = 3  # Quarterly -> Monthly
        cash_flow_bucket_unit = 'Q'
    else:
        bucket_frequency = 1  # Default is monthly
        cash_flow_bucket_unit = 'Y'

    # Delete existing records with the same fic_mis_date and account number before inserting new ones
    FSI_PD_Account_Interpolated.objects.filter(fic_mis_date=account.fic_mis_date, v_account_number=account_number).delete()

    # Apply the appropriate interpolation method
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
            v_cash_flow_bucket_unit=cash_flow_bucket_unit,
            d_record_start_date=account.fic_mis_date,
            d_record_end_date=account.fic_mis_date
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
            v_cash_flow_bucket_unit=cash_flow_bucket_unit,
            d_record_start_date=account.fic_mis_date,
            d_record_end_date=account.fic_mis_date
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
            v_cash_flow_bucket_unit=cash_flow_bucket_unit,
            d_record_start_date=account.fic_mis_date,
            d_record_end_date=account.fic_mis_date
        )


def interpolate_exponential_decay_account(account, bucket_frequency, max_bucket, pd_percent, cash_flow_bucket_unit):
    """
    Perform Exponential Decay interpolation for a given account-level PD detail.
    """
    # Adjust the PD percent based on the bucket unit
    if cash_flow_bucket_unit == 'Q':  # Quarterly
        pd_percent = 1 - (1 - pd_percent) ** (1 / 4)
    elif cash_flow_bucket_unit == 'H':  # Half-yearly
        pd_percent = 1 - (1 - pd_percent) ** (1 / 2)
    elif cash_flow_bucket_unit == 'M':  # Monthly
        pd_percent = 1 - (1 - pd_percent) ** (1 / 12)

    cumulative_pd = 0
    population_remaining = 1

    # Create an initial bucket entry for bucket 0
    FSI_PD_Account_Interpolated.objects.create(
        fic_mis_date=account.fic_mis_date,
        v_account_number=account.v_account_number,
        n_pd_percent=pd_percent,
        n_per_period_default_prob=0,
        n_cumulative_default_prob=0,
        v_cash_flow_bucket_id=0,
        v_cash_flow_bucket_unit=cash_flow_bucket_unit,
        d_record_start_date=account.fic_mis_date,
        d_record_end_date=account.fic_mis_date
    )

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
            v_cash_flow_bucket_unit=cash_flow_bucket_unit,
            d_record_start_date=account.fic_mis_date,
            d_record_end_date=account.fic_mis_date
        )

        # Stop the loop if the population reaches 0
        if population_remaining <= 0:
            break
