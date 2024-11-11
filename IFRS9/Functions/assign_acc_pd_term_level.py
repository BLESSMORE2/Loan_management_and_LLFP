import concurrent.futures
from django.db import transaction
from decimal import Decimal
from django.db.models import Prefetch
from ..models import FCT_Stage_Determination, FSI_PD_Interpolated, Ldn_PD_Term_Structure
from .save_log import save_log

def calculate_pd_for_rating(account, pd_interpolated_records, term_unit_to_periods):
    """
    Calculate PD for accounts based on the rating term structure.
    """
    if not account.d_maturity_date or not account.fic_mis_date:
        return None  # Skip accounts with missing dates

    amortization_periods = term_unit_to_periods.get(account.v_amrt_term_unit, 12)
    months_to_maturity = (account.d_maturity_date.year - account.fic_mis_date.year) * 12 + \
                         (account.d_maturity_date.month - account.fic_mis_date.month)
    buckets_to_maturity = months_to_maturity // (12 // amortization_periods)
    buckets_needed_for_12_months = 12 // (12 // amortization_periods)

    twelve_months_pd = None
    lifetime_pd = None

    try:
        if months_to_maturity > 12:
            twelve_months_pd = pd_interpolated_records.get(
                (account.n_credit_rating_code, account.n_pd_term_structure_skey, 'R', buckets_needed_for_12_months)
            )
            lifetime_pd = pd_interpolated_records.get(
                (account.n_credit_rating_code, account.n_pd_term_structure_skey, 'R', buckets_to_maturity)
            )
        else:
            twelve_months_pd = pd_interpolated_records.get(
                (account.n_credit_rating_code, account.n_pd_term_structure_skey, 'R', buckets_to_maturity)
            )
            lifetime_pd = twelve_months_pd

    except Exception as e:
        save_log('calculate_pd_for_rating', 'ERROR', f"Error calculating PD for account {account.n_account_number} (Rating): {e}")
        return None

    account.n_twelve_months_pd = twelve_months_pd or account.n_twelve_months_pd
    account.n_lifetime_pd = lifetime_pd or account.n_lifetime_pd
    return account

def calculate_pd_for_delinquency(account, pd_interpolated_records, term_unit_to_periods):
    """
    Calculate PD for accounts based on the delinquency term structure.
    """
    if not account.d_maturity_date or not account.fic_mis_date:
        return None  # Skip accounts with missing dates

    amortization_periods = term_unit_to_periods.get(account.v_amrt_term_unit, 12)
    months_to_maturity = (account.d_maturity_date.year - account.fic_mis_date.year) * 12 + \
                         (account.d_maturity_date.month - account.fic_mis_date.month)
    buckets_to_maturity = months_to_maturity // (12 // amortization_periods)
    buckets_needed_for_12_months = 12 // (12 // amortization_periods)

    twelve_months_pd = None
    lifetime_pd = None

    try:
        if months_to_maturity > 12:
            twelve_months_pd = pd_interpolated_records.get(
                (account.n_delq_band_code, account.n_pd_term_structure_skey, 'D', buckets_needed_for_12_months)
            )
            lifetime_pd = pd_interpolated_records.get(
                (account.n_delq_band_code, account.n_pd_term_structure_skey, 'D', buckets_to_maturity)
            )
        else:
            twelve_months_pd = pd_interpolated_records.get(
                (account.n_delq_band_code, account.n_pd_term_structure_skey, 'D', buckets_to_maturity)
            )
            lifetime_pd = twelve_months_pd

    except Exception as e:
        save_log('calculate_pd_for_delinquency', 'ERROR', f"Error calculating PD for account {account.n_account_number} (Delinquency): {e}")
        return None

    account.n_twelve_months_pd = twelve_months_pd or account.n_twelve_months_pd
    account.n_lifetime_pd = lifetime_pd or account.n_lifetime_pd
    return account

def calculate_pd_for_accounts(fic_mis_date):
    term_unit_to_periods = {
        'M': 12,
        'Q': 4,
        'H': 2,
        'Y': 1
    }

    # Prefetch PD term structure and FSI_PD_Interpolated records to reduce DB lookups
    pd_term_structures = Ldn_PD_Term_Structure.objects.filter(
        v_pd_term_structure_id__isnull=False
    ).only('v_pd_term_structure_id', 'v_pd_term_structure_type')

    pd_interpolated_records = FSI_PD_Interpolated.objects.filter(fic_mis_date=fic_mis_date).only(
        'v_int_rating_code', 'v_delq_band_code', 'v_pd_term_structure_id', 'v_pd_term_structure_type', 'v_cash_flow_bucket_id', 'n_cumulative_default_prob'
    )

    # Create in-memory dictionary for pd_interpolated_records
    pd_interpolated_dict = {
        (
            pd.v_int_rating_code or pd.v_delq_band_code, pd.v_pd_term_structure_id,
            pd.v_pd_term_structure_type, pd.v_cash_flow_bucket_id
        ): pd.n_cumulative_default_prob
        for pd in pd_interpolated_records
    }

    accounts = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date).select_related(
        'n_pd_term_structure_skey'
    )

    total_accounts = accounts.count()
    
    if total_accounts == 0:
        save_log('calculate_pd_for_accounts', 'INFO', f"No accounts found for fic_mis_date {fic_mis_date}.")
        return 0

    updated_accounts = []
    error_logs = {}
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {}
        for account in accounts:
            try:
                pd_term_structure_type = pd_term_structures.get(v_pd_term_structure_id=account.n_pd_term_structure_skey).v_pd_term_structure_type

                if pd_term_structure_type == 'R':
                    futures[executor.submit(calculate_pd_for_rating, account, pd_interpolated_dict, term_unit_to_periods)] = account
                elif pd_term_structure_type == 'D':
                    futures[executor.submit(calculate_pd_for_delinquency, account, pd_interpolated_dict, term_unit_to_periods)] = account

            except Ldn_PD_Term_Structure.DoesNotExist:
                warning_message = f"No matching PD term structure found for account {account.n_account_number}. Skipping."
                error_logs[warning_message] = 1
                continue

        for future in concurrent.futures.as_completed(futures):
            account = futures[future]
            try:
                result = future.result()
                if result:
                    updated_accounts.append(result)
            except Exception as e:
                error_message = f"Error processing account {account.n_account_number}: {e}"
                error_logs[error_message] = 1

    # Perform bulk update in batches of 5000
    batch_size = 5000
    for i in range(0, len(updated_accounts), batch_size):
        try:
            FCT_Stage_Determination.objects.bulk_update(
                updated_accounts[i:i + batch_size], ['n_twelve_months_pd', 'n_lifetime_pd']
            )
        except Exception as e:
            error_logs[f"Bulk update error: {e}"] = 1

    for error_message in error_logs:
        save_log('calculate_pd_for_accounts', 'ERROR', error_message)

    if not error_logs:
        save_log('calculate_pd_for_accounts', 'INFO', f"{len(updated_accounts)} out of {total_accounts} accounts were successfully updated.")
    
    return 1 if updated_accounts else 0



# import concurrent.futures
# from django.db import transaction
# from ..models import FCT_Stage_Determination, FSI_PD_Interpolated, Ldn_PD_Term_Structure
# from .save_log import save_log

# def calculate_pd_for_rating(account, fic_mis_date, term_unit_to_periods):
#     """
#     Calculate PD for accounts based on the rating code (v_pd_term_structure_type='R').
#     """

#     if not account.d_maturity_date or not account.fic_mis_date:
#         return None  # Skip accounts with missing dates

#     amortization_periods = term_unit_to_periods.get(account.v_amrt_term_unit, 12)
#     months_to_maturity = (account.d_maturity_date.year - account.fic_mis_date.year) * 12 + \
#                          (account.d_maturity_date.month - account.fic_mis_date.month)
#     buckets_to_maturity = months_to_maturity // (12 // amortization_periods)
#     buckets_needed_for_12_months = 12 // (12 // amortization_periods)

#     twelve_months_pd = None
#     lifetime_pd = None

#     try:
#         if months_to_maturity > 12:
#             pd_record = FSI_PD_Interpolated.objects.filter(
#                 v_int_rating_code=account.n_credit_rating_code,
#                 v_pd_term_structure_id=account.n_pd_term_structure_skey,
#                 v_pd_term_structure_type='R',
#                 v_cash_flow_bucket_id=buckets_needed_for_12_months
#             ).first()
#             twelve_months_pd = pd_record.n_cumulative_default_prob if pd_record else None

#             pd_record = FSI_PD_Interpolated.objects.filter(
#                 v_int_rating_code=account.n_credit_rating_code,
#                 v_pd_term_structure_id=account.n_pd_term_structure_skey,
#                 v_pd_term_structure_type='R',
#                 v_cash_flow_bucket_id=buckets_to_maturity
#             ).first()
#             lifetime_pd = pd_record.n_cumulative_default_prob if pd_record else None
#         else:
#             pd_record = FSI_PD_Interpolated.objects.filter(
#                 v_int_rating_code=account.n_credit_rating_code,
#                 v_pd_term_structure_id=account.n_pd_term_structure_skey,
#                 v_pd_term_structure_type='R',
#                 v_cash_flow_bucket_id=buckets_to_maturity
#             ).first()
#             twelve_months_pd = pd_record.n_cumulative_default_prob if pd_record else None
#             lifetime_pd = twelve_months_pd

#     except Exception as e:
#         save_log('calculate_pd_for_rating', 'ERROR', f"Error calculating PD for account {account.n_account_number} (Rating): {e}")
#         return None

#     account.n_twelve_months_pd = twelve_months_pd if twelve_months_pd is not None else account.n_twelve_months_pd
#     account.n_lifetime_pd = lifetime_pd if lifetime_pd is not None else account.n_lifetime_pd
#     return account


# def calculate_pd_for_delinquency(account, fic_mis_date, term_unit_to_periods):
#     """
#     Calculate PD for accounts based on the delinquency code (v_pd_term_structure_type='D').
#     """
#     if not account.d_maturity_date or not account.fic_mis_date:
#         return None  # Skip accounts with missing dates

#     amortization_periods = term_unit_to_periods.get(account.v_amrt_term_unit, 12)
#     months_to_maturity = (account.d_maturity_date.year - account.fic_mis_date.year) * 12 + \
#                          (account.d_maturity_date.month - account.fic_mis_date.month)
#     buckets_to_maturity = months_to_maturity // (12 // amortization_periods)
#     buckets_needed_for_12_months = 12 // (12 // amortization_periods)

#     twelve_months_pd = None
#     lifetime_pd = None

#     try:
#         if months_to_maturity > 12:
#             pd_record = FSI_PD_Interpolated.objects.filter(
#                 v_delq_band_code=account.n_delq_band_code,
#                 v_pd_term_structure_id=account.n_pd_term_structure_skey,
#                 v_pd_term_structure_type='D',
#                 v_cash_flow_bucket_id=buckets_needed_for_12_months
#             ).first()
#             twelve_months_pd = pd_record.n_cumulative_default_prob if pd_record else None

#             pd_record = FSI_PD_Interpolated.objects.filter(
#                 v_delq_band_code=account.n_delq_band_code,
#                 v_pd_term_structure_id=account.n_pd_term_structure_skey,
#                 v_pd_term_structure_type='D',
#                 v_cash_flow_bucket_id=buckets_to_maturity
#             ).first()
#             lifetime_pd = pd_record.n_cumulative_default_prob if pd_record else None
#         else:
#             pd_record = FSI_PD_Interpolated.objects.filter(
#                 v_delq_band_code=account.n_delq_band_code,
#                 v_pd_term_structure_id=account.n_pd_term_structure_skey,
#                 v_pd_term_structure_type='D',
#                 v_cash_flow_bucket_id=buckets_to_maturity
#             ).first()
#             twelve_months_pd = pd_record.n_cumulative_default_prob if pd_record else None
#             lifetime_pd = twelve_months_pd

#     except Exception as e:
#         save_log('calculate_pd_for_delinquency', 'ERROR', f"Error calculating PD for account {account.n_account_number} (Delinquency): {e}")
#         return None

#     account.n_twelve_months_pd = twelve_months_pd if twelve_months_pd is not None else account.n_twelve_months_pd
#     account.n_lifetime_pd = lifetime_pd if lifetime_pd is not None else account.n_lifetime_pd
#     return account


# def calculate_pd_for_accounts(fic_mis_date):
#     """
#     Main function to calculate the 12-month PD and Lifetime PD for accounts using multi-threading.
#     """
#     term_unit_to_periods = {
#         'M': 12,  # Monthly
#         'Q': 4,   # Quarterly
#         'H': 2,   # Half-Yearly
#         'Y': 1    # Yearly
#     }
    
#     accounts = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date)
#     total_accounts = accounts.count()
    
#     if total_accounts == 0:
#         return 0

#     updated_accounts = []
#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         futures = {}
#         for account in accounts:
#             try:
#                 pd_term_structure = Ldn_PD_Term_Structure.objects.get(v_pd_term_structure_id=account.n_pd_term_structure_skey)
#                 term_structure_type = pd_term_structure.v_pd_term_structure_type

#                 if term_structure_type == 'R':
#                     futures[executor.submit(calculate_pd_for_rating, account, fic_mis_date, term_unit_to_periods)] = account
#                 elif term_structure_type == 'D':
#                     futures[executor.submit(calculate_pd_for_delinquency, account, fic_mis_date, term_unit_to_periods)] = account

#             except Ldn_PD_Term_Structure.DoesNotExist:
#                 save_log('calculate_pd_for_accounts', 'WARNING', f"No matching PD term structure found for account {account.n_account_number}. Skipping.")
#                 continue

#         for future in concurrent.futures.as_completed(futures):
#             account = futures[future]
#             try:
#                 result = future.result()
#                 if result:
#                     updated_accounts.append(result)
#             except Exception as e:
#                 save_log('calculate_pd_for_accounts', 'ERROR', f"Error processing account {account.n_account_number}: {e}")

#     if updated_accounts:
#         FCT_Stage_Determination.objects.bulk_update(updated_accounts, ['n_twelve_months_pd', 'n_lifetime_pd'])
#         save_log('calculate_pd_for_accounts', 'INFO', f"{len(updated_accounts)} out of {total_accounts} accounts were successfully updated.")
    
#     return 1 if updated_accounts else 0
