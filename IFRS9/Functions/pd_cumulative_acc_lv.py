from django.db import connection, transaction
from .save_log import save_log

def get_latest_run_skey_sql():
    """Retrieve the latest_run_skey from Dim_Run table using raw SQL."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT latest_run_skey FROM Dim_Run LIMIT 1;")
        row = cursor.fetchone()
        if not row:
            raise ValueError("No run key available in Dim_Run table.")
        return row[0]

def update_cash_flow_with_account_pd_buckets_sql(fic_mis_date):
    """
    Updates the fsi_Financial_Cash_Flow_Cal table using account-level PD values from 
    FSI_PD_Account_Interpolated in a set-based manner.
    """
    try:
        # Retrieve the latest run_skey using raw SQL
        n_run_skey = get_latest_run_skey_sql()

        with transaction.atomic(), connection.cursor() as cursor:
            # First update: Set cumulative loss and impaired probabilities
            cursor.execute("""
                UPDATE fsi_Financial_Cash_Flow_Cal AS cf
                JOIN FSI_PD_Account_Interpolated AS pd 
                    ON pd.v_account_number = cf.v_account_number
                    AND pd.fic_mis_date = cf.fic_mis_date
                    AND pd.v_cash_flow_bucket_id = cf.n_cash_flow_bucket_id
                SET 
                    cf.n_cumulative_loss_rate = pd.n_cumulative_default_prob * cf.n_lgd_percent,
                    cf.n_cumulative_impaired_prob = pd.n_cumulative_default_prob
                WHERE cf.fic_mis_date = %s
                  AND cf.n_run_skey = %s;
            """, [fic_mis_date, n_run_skey])

            # Second update: Set 12-month cumulative PD based on bucket and term unit
            cursor.execute("""
                UPDATE fsi_Financial_Cash_Flow_Cal AS cf
                JOIN FSI_PD_Account_Interpolated AS pd 
                    ON pd.v_account_number = cf.v_account_number
                    AND pd.fic_mis_date = cf.fic_mis_date
                    AND pd.v_cash_flow_bucket_id = CASE 
                        WHEN cf.n_cash_flow_bucket_id <= 
                            CASE cf.v_amrt_term_unit
                                WHEN 'M' THEN 12
                                WHEN 'Q' THEN 4
                                WHEN 'H' THEN 2
                                WHEN 'Y' THEN 1
                                ELSE 12
                            END
                        THEN cf.n_cash_flow_bucket_id
                        ELSE 
                            CASE cf.v_amrt_term_unit
                                WHEN 'M' THEN 12
                                WHEN 'Q' THEN 4
                                WHEN 'H' THEN 2
                                WHEN 'Y' THEN 1
                                ELSE 12
                            END
                    END
                SET cf.n_12m_cumulative_pd = pd.n_cumulative_default_prob
                WHERE cf.fic_mis_date = %s
                  AND cf.n_run_skey = %s;
            """, [fic_mis_date, n_run_skey])

        save_log('update_cash_flow_with_account_pd_buckets_sql', 'INFO', 
                 f"Successfully updated cash flows for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}.")
        return 1

    except Exception as e:
        save_log('update_cash_flow_with_account_pd_buckets_sql', 'ERROR', 
                 f"Error updating cash flow for fic_mis_date {fic_mis_date}: {e}")
        return 0



# from django.db import transaction
# from concurrent.futures import ThreadPoolExecutor
# from ..models import *
# from ..Functions import save_log

# def get_latest_run_skey():
#     """
#     Retrieve the latest_run_skey from Dim_Run table.
#     """
#     try:
#         run_record = Dim_Run.objects.first()
#         if not run_record:
#             raise ValueError("No run key is available in the Dim_Run table.")
#         return run_record.latest_run_skey
#     except Dim_Run.DoesNotExist:
#         raise ValueError("Dim_Run table is missing.")

# def update_cash_flow_with_account_pd_buckets(fic_mis_date, batch_size=1000, max_workers=8):
#     """
#     This function updates the fsi_Financial_Cash_Flow_Cal table using account-level PD values from 
#     FSI_PD_Account_Interpolated. It directly aligns the PD values to the cash flow buckets of each account.
#     """
#     try:
#         n_run_skey = get_latest_run_skey()
#         cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

#         if not cash_flows.exists():
#             save_log('update_cash_flow_with_account_pd_buckets', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date} and run_skey {n_run_skey}.")
#             return 0  # Return 0 if no records are found

#         def process_batch(batch):
#             updates = []
#             for cash_flow in batch:
#                 try:
#                     account_pd_records = FSI_PD_Account_Interpolated.objects.filter(
#                         v_account_number=cash_flow.v_account_number,
#                         fic_mis_date=fic_mis_date
#                     )

#                     if account_pd_records.exists():
#                         pd_record = account_pd_records.filter(v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id).first()

#                         if pd_record:
#                             cash_flow.n_cumulative_loss_rate = pd_record.n_cumulative_default_prob * cash_flow.n_lgd_percent
#                             cash_flow.n_cumulative_impaired_prob = pd_record.n_cumulative_default_prob

#                             months_to_12m = get_buckets_for_12_months(cash_flow.v_amrt_term_unit)
#                             if cash_flow.n_cash_flow_bucket_id <= months_to_12m:
#                                 cash_flow.n_12m_cumulative_pd = pd_record.n_cumulative_default_prob
#                             else:
#                                 pd_record_12 = account_pd_records.filter(v_cash_flow_bucket_id=months_to_12m).first()
#                                 if pd_record_12:
#                                     cash_flow.n_12m_cumulative_pd = pd_record_12.n_cumulative_default_prob

#                             updates.append(cash_flow)

#                 except Exception as e:
#                     save_log('process_batch', 'ERROR', f"Error updating account {cash_flow.v_account_number}: {str(e)}")

#             if updates:
#                 fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                     updates, 
#                     ['n_cumulative_loss_rate', 'n_cumulative_impaired_prob', 'n_12m_cumulative_pd']
#                 )

#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             batch = []
#             futures = []
#             for cash_flow in cash_flows.iterator(chunk_size=batch_size):
#                 batch.append(cash_flow)
#                 if len(batch) >= batch_size:
#                     futures.append(executor.submit(process_batch, batch))
#                     batch = []

#             if batch:
#                 futures.append(executor.submit(process_batch, batch))

#             for future in futures:
#                 try:
#                     future.result()
#                 except Exception as exc:
#                     save_log('update_cash_flow_with_account_pd_buckets', 'ERROR', f"An error occurred during batch processing: {str(exc)}")
#                     return 0  # Return 0 if any thread encounters an error

#         save_log('update_cash_flow_with_account_pd_buckets', 'INFO', f"Updated {cash_flows.count()} records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}")
#         return 1  # Return 1 on successful completion

#     except Exception as e:
#         save_log('update_cash_flow_with_account_pd_buckets', 'ERROR', f"Error updating cash flow for fic_mis_date {fic_mis_date}: {str(e)}")
#         return 0  # Return 0 in case of any exception

# def get_buckets_for_12_months(v_amrt_term_unit):
#     """
#     This function returns the number of buckets required to reach 12 months based on the amortization term unit (M, Q, H, Y).
#     """
#     term_unit_to_buckets = {
#         'M': 12,  # Monthly: 12 months = 12 buckets
#         'Q': 4,   # Quarterly: 12 months = 4 buckets
#         'H': 2,   # Half-yearly: 12 months = 2 buckets
#         'Y': 1    # Yearly: 12 months = 1 bucket
#     }
#     return term_unit_to_buckets.get(v_amrt_term_unit, 12)  # Default to 12 months for monthly if not found
