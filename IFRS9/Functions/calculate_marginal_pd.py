from django.db import connection, transaction
from ..models import Dim_Run
from .save_log import save_log

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.only('latest_run_skey').first()
        if not run_record:
            save_log('get_latest_run_skey', 'ERROR', "No run key is available.")
            return None
        return run_record.latest_run_skey
    except Exception as e:
        save_log('get_latest_run_skey', 'ERROR', str(e))
        return None

def update_marginal_pd(fic_mis_date):
    """
    Efficiently update n_per_period_impaired_prob and n_12m_per_period_pd for all 
    records in fsi_Financial_Cash_Flow_Cal on a given fic_mis_date using window functions.
    """
    run_skey = get_latest_run_skey()
    if not run_skey:
        return 0

    try:
        with connection.cursor() as cursor, transaction.atomic():
            # Step 1: Create a temporary table with computed marginal PD values using window functions.
            create_temp_sql = """
                CREATE TEMPORARY TABLE temp_marginal_pd AS
                SELECT
                    id,
                    ABS(n_cumulative_impaired_prob - 
                        COALESCE(LAG(n_cumulative_impaired_prob) OVER (
                            PARTITION BY v_account_number
                            ORDER BY n_cash_flow_bucket_id
                        ), 0)
                    ) AS computed_per_period_impaired_prob,
                    ABS(n_12m_cumulative_pd - 
                        COALESCE(LAG(n_12m_cumulative_pd) OVER (
                            PARTITION BY v_account_number
                            ORDER BY n_cash_flow_bucket_id
                        ), 0)
                    ) AS computed_12m_per_period_pd
                FROM fsi_financial_cash_flow_cal
                WHERE fic_mis_date = %s AND n_run_skey = %s;
            """
            cursor.execute(create_temp_sql, [fic_mis_date, run_skey])

            # Step 2: Update the main table by joining with the temporary table.
            update_sql = """
                UPDATE fsi_financial_cash_flow_cal AS cf
                JOIN temp_marginal_pd AS tmp ON cf.id = tmp.id
                SET 
                    cf.n_per_period_impaired_prob = tmp.computed_per_period_impaired_prob,
                    cf.n_12m_per_period_pd = tmp.computed_12m_per_period_pd
                WHERE cf.fic_mis_date = %s AND cf.n_run_skey = %s;
            """
            cursor.execute(update_sql, [fic_mis_date, run_skey])
            updated_count = cursor.rowcount

            # Step 3: Drop the temporary table.
            cursor.execute("DROP TEMPORARY TABLE IF EXISTS temp_marginal_pd;")

        save_log('update_marginal_pd_setbased', 'INFO', f"Updated {updated_count} rows for marginal PD on {fic_mis_date}.")
        return 1 if updated_count > 0 else 0

    except Exception as e:
        save_log('update_marginal_pd_setbased', 'ERROR', f"Error: {e}")
        return 0


# from concurrent.futures import ThreadPoolExecutor, as_completed
# from django.db.models import F
# from ..models import fsi_Financial_Cash_Flow_Cal, Dim_Run
# from .save_log import save_log

# def get_latest_run_skey():
#     try:
#         run_record = Dim_Run.objects.first()
#         if not run_record:
#             raise ValueError("No run key is available in the Dim_Run table.")
#         return run_record.latest_run_skey
#     except Dim_Run.DoesNotExist:
#         raise ValueError("Dim_Run table is missing.")

# def update_marginal_pd(fic_mis_date, max_workers=5, batch_size=1000):
#     try:
#         n_run_skey = get_latest_run_skey()
#         cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(
#             fic_mis_date=fic_mis_date, n_run_skey=n_run_skey
#         ).order_by('v_account_number', 'n_cash_flow_bucket_id')
        
#         if not cash_flows.exists():
#             save_log('update_marginal_pd', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date} and run_skey {n_run_skey}.")
#             return 0

#         total_updated_records = 0
#         cash_flow_dict = {}
        
#         # Populate dictionary with all cash flows for quick access
#         for cash_flow in cash_flows:
#             account_key = (cash_flow.v_account_number, cash_flow.n_cash_flow_bucket_id)
#             cash_flow_dict[account_key] = cash_flow

#         def process_batch(batch):
#             try:
#                 updates = []
#                 for cash_flow in batch:
#                     prev_key = (cash_flow.v_account_number, cash_flow.n_cash_flow_bucket_id - 1)
#                     previous_cash_flow = cash_flow_dict.get(prev_key)

#                     # Calculate n_per_period_impaired_prob
#                     if cash_flow.n_cumulative_impaired_prob is not None:
#                         if previous_cash_flow and previous_cash_flow.n_cumulative_impaired_prob is not None:
#                             cash_flow.n_per_period_impaired_prob = abs(cash_flow.n_cumulative_impaired_prob - previous_cash_flow.n_cumulative_impaired_prob)
#                         else:
#                             cash_flow.n_per_period_impaired_prob = abs(cash_flow.n_cumulative_impaired_prob)

#                     # Calculate n_12m_per_period_pd
#                     if cash_flow.n_12m_cumulative_pd is not None:
#                         if previous_cash_flow and previous_cash_flow.n_12m_cumulative_pd is not None:
#                             cash_flow.n_12m_per_period_pd = abs(cash_flow.n_12m_cumulative_pd - previous_cash_flow.n_12m_cumulative_pd)
#                         else:
#                             cash_flow.n_12m_per_period_pd = abs(cash_flow.n_12m_cumulative_pd)

#                     updates.append(cash_flow)

#                 # Bulk update for the current batch
#                 if updates:
#                     fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                         updates, ['n_per_period_impaired_prob', 'n_12m_per_period_pd']
#                     )
#                 return len(updates)

#             except Exception as e:
#                 save_log('update_marginal_pd', 'ERROR', f"Error updating batch: {e}")
#                 return 0

#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = []
#             batch = []
#             for cash_flow in cash_flows.iterator(chunk_size=batch_size):
#                 batch.append(cash_flow)
#                 if len(batch) >= batch_size:
#                     futures.append(executor.submit(process_batch, batch))
#                     batch = []

#             if batch:
#                 futures.append(executor.submit(process_batch, batch))

#             for future in as_completed(futures):
#                 try:
#                     total_updated_records += future.result()
#                 except Exception as exc:
#                     save_log('update_marginal_pd', 'ERROR', f"Thread encountered an error: {exc}")
#                     return 0

#         save_log('update_marginal_pd', 'INFO', f"Total updated records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}: {total_updated_records}")
#         return 1 if total_updated_records > 0 else 0

#     except Exception as e:
#         save_log('update_marginal_pd', 'ERROR', f"Error during marginal PD update process: {e}")
#         return 0
