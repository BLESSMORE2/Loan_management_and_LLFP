from django.db import connection, transaction
from .save_log import save_log

def calculate_account_level_pd_for_accounts_sql(fic_mis_date):
    """
    Set-based account-level PD calculation using raw SQL for MySQL/MariaDB.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Update for accounts with months_to_maturity > 12
            cursor.execute("""
                UPDATE fct_stage_determination sd
                SET 
                    n_twelve_months_pd = (
                        SELECT pd.n_cumulative_default_prob
                        FROM fsi_pd_account_interpolated pd
                        WHERE pd.v_account_number = sd.n_account_number
                          AND pd.fic_mis_date = sd.fic_mis_date
                          AND pd.v_cash_flow_bucket_id = CASE
                                WHEN sd.v_amrt_term_unit = 'M' THEN 12
                                WHEN sd.v_amrt_term_unit = 'Q' THEN 4
                                WHEN sd.v_amrt_term_unit = 'H' THEN 2
                                WHEN sd.v_amrt_term_unit = 'Y' THEN 1
                                ELSE 12
                          END
                        LIMIT 1
                    ),
                    n_lifetime_pd = (
                        SELECT pd.n_cumulative_default_prob
                        FROM fsi_pd_account_interpolated pd
                        WHERE pd.v_account_number = sd.n_account_number
                          AND pd.fic_mis_date = sd.fic_mis_date
                          AND pd.v_cash_flow_bucket_id = FLOOR(
                                GREATEST(
                                    TIMESTAMPDIFF(MONTH, sd.fic_mis_date, sd.d_maturity_date) /
                                    (12 / CASE
                                        WHEN sd.v_amrt_term_unit = 'M' THEN 12
                                        WHEN sd.v_amrt_term_unit = 'Q' THEN 4
                                        WHEN sd.v_amrt_term_unit = 'H' THEN 2
                                        WHEN sd.v_amrt_term_unit = 'Y' THEN 1
                                        ELSE 12
                                    END),
                                    1
                                )
                          )
                        LIMIT 1
                    )
                WHERE sd.fic_mis_date = %s 
                  AND sd.d_maturity_date IS NOT NULL
                  AND TIMESTAMPDIFF(MONTH, sd.fic_mis_date, sd.d_maturity_date) > 12;
            """, [fic_mis_date])

            # Update for accounts with months_to_maturity <= 12
            cursor.execute("""
                UPDATE fct_stage_determination sd
                SET 
                    n_twelve_months_pd = (
                        SELECT pd.n_cumulative_default_prob
                        FROM fsi_pd_account_interpolated pd
                        WHERE pd.v_account_number = sd.n_account_number
                          AND pd.fic_mis_date = sd.fic_mis_date
                          AND pd.v_cash_flow_bucket_id = FLOOR(
                                GREATEST(
                                    TIMESTAMPDIFF(MONTH, sd.fic_mis_date, sd.d_maturity_date) /
                                    (12 / CASE
                                        WHEN sd.v_amrt_term_unit = 'M' THEN 12
                                        WHEN sd.v_amrt_term_unit = 'Q' THEN 4
                                        WHEN sd.v_amrt_term_unit = 'H' THEN 2
                                        WHEN sd.v_amrt_term_unit = 'Y' THEN 1
                                        ELSE 12
                                    END),
                                    1
                                )
                          )
                        LIMIT 1
                    ),
                    n_lifetime_pd = (
                        SELECT pd.n_cumulative_default_prob
                        FROM fsi_pd_account_interpolated pd
                        WHERE pd.v_account_number = sd.n_account_number
                          AND pd.fic_mis_date = sd.fic_mis_date
                          AND pd.v_cash_flow_bucket_id = FLOOR(
                                GREATEST(
                                    TIMESTAMPDIFF(MONTH, sd.fic_mis_date, sd.d_maturity_date) /
                                    (12 / CASE
                                        WHEN sd.v_amrt_term_unit = 'M' THEN 12
                                        WHEN sd.v_amrt_term_unit = 'Q' THEN 4
                                        WHEN sd.v_amrt_term_unit = 'H' THEN 2
                                        WHEN sd.v_amrt_term_unit = 'Y' THEN 1
                                        ELSE 12
                                    END),
                                    1
                                )
                          )
                        LIMIT 1
                    )
                WHERE sd.fic_mis_date = %s 
                  AND sd.d_maturity_date IS NOT NULL
                  AND TIMESTAMPDIFF(MONTH, sd.fic_mis_date, sd.d_maturity_date) <= 12;
            """, [fic_mis_date])

        save_log('calculate_account_level_pd_for_accounts_sql', 'INFO', 
                 f"Account-level PD calculation completed for fic_mis_date={fic_mis_date}.")
        return 1

    except Exception as e:
        save_log('calculate_account_level_pd_for_accounts_sql', 'ERROR', 
                 f"Error during account-level PD calculation: {str(e)}")
        return 0


# import concurrent.futures
# from django.db import transaction
# from decimal import Decimal
# from ..models import FCT_Stage_Determination, FSI_PD_Account_Interpolated
# from .save_log import save_log

# def calculate_account_level_pd_for_account(account, fic_mis_date, term_unit_to_periods):
#     """
#     Function to calculate 12-month PD and Lifetime PD for a single account using account-level interpolated PD data.
#     """
#     amortization_periods = term_unit_to_periods.get(account.v_amrt_term_unit, 12)  # Default to 12 (monthly)
#     try:
#         # Calculate the number of months and buckets to maturity
#         if account.d_maturity_date and account.fic_mis_date:
#             months_to_maturity = (account.d_maturity_date.year - account.fic_mis_date.year) * 12 + \
#                                  (account.d_maturity_date.month - account.fic_mis_date.month)
#             buckets_to_maturity = months_to_maturity // (12 // amortization_periods)
#         else:
#             return None

#         buckets_needed_for_12_months = 12 // (12 // amortization_periods)
#         twelve_months_pd, lifetime_pd = None, None

#         # Fetch PD records based on maturity
#         if months_to_maturity > 12:
#             twelve_months_pd_record = FSI_PD_Account_Interpolated.objects.filter(
#                 v_account_number=account.n_account_number,
#                 fic_mis_date=fic_mis_date,
#                 v_cash_flow_bucket_id=buckets_needed_for_12_months
#             ).first()
#             twelve_months_pd = twelve_months_pd_record.n_cumulative_default_prob if twelve_months_pd_record else None

#             lifetime_pd_record = FSI_PD_Account_Interpolated.objects.filter(
#                 v_account_number=account.n_account_number,
#                 fic_mis_date=fic_mis_date,
#                 v_cash_flow_bucket_id=buckets_to_maturity
#             ).first()
#             lifetime_pd = lifetime_pd_record.n_cumulative_default_prob if lifetime_pd_record else None
#         else:
#             pd_record = FSI_PD_Account_Interpolated.objects.filter(
#                 v_account_number=account.n_account_number,
#                 fic_mis_date=fic_mis_date,
#                 v_cash_flow_bucket_id=buckets_to_maturity
#             ).first()
#             twelve_months_pd = lifetime_pd = pd_record.n_cumulative_default_prob if pd_record else None

#         # Update the account with calculated PDs
#         account.n_twelve_months_pd = twelve_months_pd if twelve_months_pd is not None else account.n_twelve_months_pd
#         account.n_lifetime_pd = lifetime_pd if lifetime_pd is not None else account.n_lifetime_pd

#         return account if twelve_months_pd or lifetime_pd else None

#     except FSI_PD_Account_Interpolated.DoesNotExist:
#         save_log('calculate_account_level_pd_for_account', 'WARNING', f"Account {account.n_account_number}: No PD records found for specified buckets.")
#     except Exception as e:
#         save_log('calculate_account_level_pd_for_account', 'ERROR', f"Account {account.n_account_number}: Error calculating PD values: {e}")

#     return None

# def calculate_account_level_pd_for_accounts(fic_mis_date):
#     """
#     Main function to calculate the 12-month PD and Lifetime PD for accounts using multi-threading and account-level PDs.
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
#         save_log('calculate_account_level_pd_for_accounts', 'INFO', "No accounts found for the given MIS date.")
#         return 0

#     save_log('calculate_account_level_pd_for_accounts', 'INFO', f"Processing {total_accounts} accounts.")
#     updated_accounts = []
#     error_logs = {}

#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         futures = {executor.submit(calculate_account_level_pd_for_account, account, fic_mis_date, term_unit_to_periods): account for account in accounts}

#         for future in concurrent.futures.as_completed(futures):
#             account = futures[future]
#             try:
#                 result = future.result()
#                 if result:
#                     updated_accounts.append(result)
#             except Exception as e:
#                 error_message = f"Error occurred while processing account {account.n_account_number}: {e}"
#                 error_logs[error_message] = 1

#     # Perform bulk update in batches of 5000
#     batch_size = 5000
#     for i in range(0, len(updated_accounts), batch_size):
#         try:
#             FCT_Stage_Determination.objects.bulk_update(
#                 updated_accounts[i:i + batch_size], ['n_twelve_months_pd', 'n_lifetime_pd']
#             )
#         except Exception as e:
#             error_logs[f"Bulk update error: {e}"] = 1

#     for error_message in error_logs:
#         save_log('calculate_account_level_pd_for_accounts', 'ERROR', error_message)

#     if not error_logs:
#         save_log('calculate_account_level_pd_for_accounts', 'INFO', f"{len(updated_accounts)} out of {total_accounts} accounts were successfully updated.")
    
#     return 1 if updated_accounts else 0


