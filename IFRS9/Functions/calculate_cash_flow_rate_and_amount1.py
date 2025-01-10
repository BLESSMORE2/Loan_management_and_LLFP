from decimal import Decimal
from django.db import connection, transaction
from ..models import Dim_Run
from .save_log import save_log

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.first()
        if not run_record:
            save_log('get_latest_run_skey', 'ERROR', "No run key is available in Dim_Run table.")
            return None
        return run_record.latest_run_skey
    except Exception as e:
        save_log('get_latest_run_skey', 'ERROR', str(e))
        return None

def calculate_expected_cash_flow(fic_mis_date):
    """
    Perform SQL-based bulk update to calculate expected cash flow fields for all relevant records.
    """
    try:
        run_skey = get_latest_run_skey()
        if not run_skey:
            save_log('calculate_expected_cash_flow_sql', 'ERROR', "No valid run key found.")
            return 0

        with connection.cursor() as cursor, transaction.atomic():
            cursor.execute("""
                UPDATE fsi_Financial_Cash_Flow_Cal
                SET 
                    n_expected_cash_flow_rate = CASE 
                        WHEN n_cumulative_loss_rate IS NOT NULL 
                        THEN 1 - n_cumulative_loss_rate 
                        ELSE n_expected_cash_flow_rate 
                    END,
                    
                    n_12m_exp_cash_flow = CASE
                        WHEN n_12m_cumulative_pd IS NOT NULL 
                             AND n_lgd_percent IS NOT NULL 
                        THEN COALESCE(n_cash_flow_amount, 0) 
                             * (1 - (n_12m_cumulative_pd * n_lgd_percent))
                        ELSE n_12m_exp_cash_flow
                    END,
                    
                    n_expected_cash_flow = CASE
                        WHEN n_expected_cash_flow_rate IS NOT NULL 
                        THEN COALESCE(n_cash_flow_amount, 0) * n_expected_cash_flow_rate
                        ELSE n_expected_cash_flow
                    END
                WHERE 
                    fic_mis_date = %s 
                    AND n_run_skey = %s;
            """, [fic_mis_date, run_skey])

        save_log('calculate_expected_cash_flow_sql', 'INFO', 
                 f"Successfully updated expected cash flow calculations for fic_mis_date={fic_mis_date}, run_skey={run_skey}.")
        return 1

    except Exception as e:
        save_log('calculate_expected_cash_flow_sql', 'ERROR', f"Error during SQL update: {e}")
        return 0



# from concurrent.futures import ThreadPoolExecutor, as_completed
# from decimal import Decimal
# from django.db import transaction
# from django.db.models import F
# from ..models import fsi_Financial_Cash_Flow_Cal, Dim_Run
# from .save_log import save_log

# # You can tune this if you want to split the bulk update into multiple sub-batches
# UPDATE_BATCH_SIZE = 5000

# def get_latest_run_skey():
#     """
#     Retrieve the latest_run_skey from Dim_Run table.
#     """
#     try:
#         run_record = Dim_Run.objects.first()
#         if not run_record:
#             save_log('get_latest_run_skey', 'ERROR', "No run key is available in Dim_Run table.")
#             return None
#         return run_record.latest_run_skey
#     except Dim_Run.DoesNotExist:
#         save_log('get_latest_run_skey', 'ERROR', "Dim_Run table is missing.")
#         return None


# def process_records(records):
#     """
#     Process a batch of records to calculate expected cash flow fields.
#     Returns a list of updated records.
#     """
#     updated_records = []
#     for record in records:
#         try:
#             # 1. Calculate `n_expected_cash_flow_rate`
#             if record.n_cumulative_loss_rate is not None:
#                 record.n_expected_cash_flow_rate = Decimal(1) - record.n_cumulative_loss_rate

#             # 2. Calculate `n_12m_exp_cash_flow`
#             #    = (cash_flow_amount) * (1 - (12m PD * LGD))
#             if record.n_12m_cumulative_pd is not None and record.n_lgd_percent is not None:
#                 record.n_12m_exp_cash_flow = (
#                     (record.n_cash_flow_amount or Decimal(0)) *
#                     (Decimal(1) - (record.n_12m_cumulative_pd * record.n_lgd_percent))
#                 )

#             # 3. Calculate `n_expected_cash_flow`
#             #    = (cash_flow_amount) * expected_cash_flow_rate
#             if record.n_expected_cash_flow_rate is not None:
#                 record.n_expected_cash_flow = (
#                     (record.n_cash_flow_amount or Decimal(0)) *
#                     record.n_expected_cash_flow_rate
#                 )

#             updated_records.append(record)

#         except Exception as e:
#             save_log('process_records', 'ERROR',
#                      f"Error processing record for account {record.v_account_number}: {e}")
#     return updated_records


# def calculate_expected_cash_flow(
#     fic_mis_date,
#     batch_size=2000,
#     num_threads=8,
#     update_batch_size=UPDATE_BATCH_SIZE
# ):
#     """
#     Main function to calculate expected cash flow with multithreading and bulk updates.

#     :param fic_mis_date:      MIS date to filter records.
#     :param batch_size:        Number of records processed per thread chunk.
#     :param num_threads:       Number of parallel threads to use.
#     :param update_batch_size: Number of records to update in a single bulk update sub-batch.
#     :return:                  1 if successful, 0 otherwise.
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         if not run_skey:
#             return 0  # No valid run key

#         # 1) Fetch only the columns needed for computation.
#         records_qs = fsi_Financial_Cash_Flow_Cal.objects.filter(
#             fic_mis_date=fic_mis_date,
#             n_run_skey=run_skey
#         ).only(
#             'v_account_number',
#             'n_cumulative_loss_rate',
#             'n_12m_cumulative_pd',
#             'n_lgd_percent',
#             'n_cash_flow_amount',
#             'n_expected_cash_flow_rate',
#             'n_12m_exp_cash_flow',
#             'n_expected_cash_flow'
#         )

#         # Convert to list for in-memory processing
#         records = list(records_qs)
#         if not records:
#             save_log('calculate_expected_cash_flow', 'INFO',
#                      f"No records found for fic_mis_date={fic_mis_date}, run_skey={run_skey}.")
#             return 0

#         save_log('calculate_expected_cash_flow', 'INFO',
#                  f"Fetched {len(records)} records for processing.")

#         # 2) Utility to chunk records for parallel processing
#         def chunker(seq, size):
#             for pos in range(0, len(seq), size):
#                 yield seq[pos:pos + size]

#         # 3) Process in parallel
#         updated_records_all = []
#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = []
#             for batch in chunker(records, batch_size):
#                 futures.append(executor.submit(process_records, batch))

#             # Gather results
#             for future in as_completed(futures):
#                 try:
#                     updated_records_all.extend(future.result())
#                 except Exception as e:
#                     save_log('calculate_expected_cash_flow', 'ERROR',
#                              f"Error in thread execution: {e}")
#                     return 0

#         # 4) Bulk update in sub-batches
#         total_updated = len(updated_records_all)
#         if total_updated == 0:
#             save_log('calculate_expected_cash_flow', 'INFO',
#                      "No records were updated after processing.")
#             return 0

#         with transaction.atomic():
#             for start in range(0, total_updated, update_batch_size):
#                 end = start + update_batch_size
#                 fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                     updated_records_all[start:end],
#                     [
#                         'n_expected_cash_flow_rate',
#                         'n_12m_exp_cash_flow',
#                         'n_expected_cash_flow'
#                     ]
#                 )

#         save_log('calculate_expected_cash_flow', 'INFO',
#                  f"Successfully updated {total_updated} records.")
#         return 1

#     except Exception as e:
#         save_log('calculate_expected_cash_flow', 'ERROR',
#                  f"Error calculating expected cash flows for fic_mis_date={fic_mis_date}: {e}")
#         return 0


# from concurrent.futures import ThreadPoolExecutor
# from decimal import Decimal
# from django.db import transaction
# from ..models import *
# from .save_log import save_log

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

# def process_records(records):
#     """
#     Function to process a batch of records and apply calculations.
#     """
#     updated_records = []
    
#     for record in records:
#         try:
#             # 1. Calculate `n_expected_cash_flow_rate`
#             if record.n_cumulative_loss_rate is not None:
#                 record.n_expected_cash_flow_rate = Decimal(1) - record.n_cumulative_loss_rate

#             # 2. Calculate `n_12m_exp_cash_flow` using 12-month cumulative PD and LGD
#             if record.n_12m_cumulative_pd is not None and record.n_lgd_percent is not None:
#                 record.n_12m_exp_cash_flow = (record.n_cash_flow_amount or Decimal(0)) * (Decimal(1) - (record.n_12m_cumulative_pd * record.n_lgd_percent))

#             # 3. Calculate `n_expected_cash_flow` using the expected cash flow rate
#             if record.n_expected_cash_flow_rate is not None:
#                 record.n_expected_cash_flow = (record.n_cash_flow_amount or Decimal(0)) * record.n_expected_cash_flow_rate

#             # Add the updated record to the list
#             updated_records.append(record)
#         except Exception as e:
#             save_log('process_records', 'ERROR', f"Error processing record for account {record.v_account_number}: {e}")
    
#     return updated_records

# def calculate_expected_cash_flow(fic_mis_date, batch_size=1000, num_threads=4):
#     """
#     Main function to calculate expected cash flow with multithreading and bulk update.
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))
        
#         if not records:
#             save_log('calculate_expected_cash_flow', 'INFO', f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
#             return 0
        
#         total_updated_records = 0

#         # Helper to chunk the records into smaller batches
#         def chunker(seq, size):
#             return (seq[pos:pos + size] for pos in range(0, len(seq), size))

#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = []
#             for batch in chunker(records, batch_size):
#                 futures.append(executor.submit(process_records, batch))

#             updated_batches = []
#             for future in futures:
#                 try:
#                     updated_records = future.result()
#                     updated_batches.extend(updated_records)
#                     total_updated_records += len(updated_records)
#                 except Exception as e:
#                     save_log('calculate_expected_cash_flow', 'ERROR', f"Error in thread execution: {e}")
#                     return 0

#         # Perform a single bulk update for all processed records
#         with transaction.atomic():
#             fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
#                 'n_expected_cash_flow_rate', 
#                 'n_12m_exp_cash_flow', 
#                 'n_expected_cash_flow'
#             ])
        
#         save_log('calculate_expected_cash_flow', 'INFO', f"Successfully updated {total_updated_records} records.")
#         return 1

#     except Exception as e:
#         save_log('calculate_expected_cash_flow', 'ERROR', f"Error calculating expected cash flows for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
#         return 0
