from django.db import connection, transaction
from ..models import Dim_Run
from .save_log import save_log
from decimal import Decimal

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.only('latest_run_skey').first()
        if not run_record:
            save_log('get_latest_run_skey', 'ERROR', "No run key available.")
            return None
        return run_record.latest_run_skey
    except Exception as e:
        save_log('get_latest_run_skey', 'ERROR', str(e))
        return None

def calculate_cashflow_fields(fic_mis_date):
    """
    Calculates and updates cash flow fields (PV, shortfalls, etc.) in a single set-based SQL update.
    """
    run_skey = get_latest_run_skey()
    if not run_skey:
        return 0

    try:
        with connection.cursor() as cursor, transaction.atomic():
            sql = """
            UPDATE fsi_financial_cash_flow_cal
            SET 
                n_expected_cash_flow_pv = CASE 
                    WHEN n_discount_factor IS NOT NULL AND n_expected_cash_flow IS NOT NULL 
                    THEN n_discount_factor * n_expected_cash_flow 
                    ELSE n_expected_cash_flow_pv END,
                n_12m_exp_cash_flow_pv = CASE 
                    WHEN n_discount_factor IS NOT NULL AND n_12m_exp_cash_flow IS NOT NULL 
                    THEN n_discount_factor * n_12m_exp_cash_flow 
                    ELSE n_12m_exp_cash_flow_pv END,
                n_cash_shortfall = CASE 
                    WHEN n_cash_flow_amount IS NOT NULL AND n_expected_cash_flow IS NOT NULL 
                    THEN (n_cash_flow_amount - n_expected_cash_flow) 
                    ELSE n_cash_shortfall END,
                n_12m_cash_shortfall = CASE 
                    WHEN n_cash_flow_amount IS NOT NULL AND n_12m_exp_cash_flow IS NOT NULL 
                    THEN (n_cash_flow_amount - n_12m_exp_cash_flow) 
                    ELSE n_12m_cash_shortfall END,
                n_cash_shortfall_pv = CASE 
                    WHEN n_discount_factor IS NOT NULL AND n_cash_flow_amount IS NOT NULL AND n_expected_cash_flow IS NOT NULL 
                    THEN n_discount_factor * (n_cash_flow_amount - n_expected_cash_flow) 
                    ELSE n_cash_shortfall_pv END,
                n_12m_cash_shortfall_pv = CASE 
                    WHEN n_discount_factor IS NOT NULL AND n_cash_flow_amount IS NOT NULL AND n_12m_exp_cash_flow IS NOT NULL 
                    THEN n_discount_factor * (n_cash_flow_amount - n_12m_exp_cash_flow) 
                    ELSE n_12m_cash_shortfall_pv END
            WHERE fic_mis_date = %s AND n_run_skey = %s;
            """
            cursor.execute(sql, [fic_mis_date, run_skey])
            updated_count = cursor.rowcount

        save_log('calculate_cashflow_fields_setbased', 'INFO', f"Successfully updated {updated_count} records.")
        return 1 if updated_count > 0 else 0

    except Exception as e:
        save_log('calculate_cashflow_fields_setbased', 'ERROR', f"Error: {e}")
        return 0


# from concurrent.futures import ThreadPoolExecutor, as_completed
# from decimal import Decimal
# from django.db import transaction
# from django.db.models import F
# from ..models import fsi_Financial_Cash_Flow_Cal, Dim_Run
# from .save_log import save_log


# # -------------------------------------------------------
# # Utility to get the latest run_skey from Dim_Run
# # -------------------------------------------------------
# def get_latest_run_skey():
#     """
#     Retrieve the latest_run_skey from Dim_Run table.
#     """
#     try:
#         run_record = Dim_Run.objects.first()
#         if not run_record:
#             save_log('get_latest_run_skey', 'ERROR', "No run key is available in the Dim_Run table.")
#             return None
#         return run_record.latest_run_skey
#     except Dim_Run.DoesNotExist:
#         save_log('get_latest_run_skey', 'ERROR', "Dim_Run table is missing.")
#         return None


# # -------------------------------------------------------
# # Function to process a batch of records (CPU-bound)
# # -------------------------------------------------------
# def process_cashflow_records(records):
#     """
#     Process a batch of records and apply calculations for cash flow fields in Python.
#     """
#     updated_records = []

#     for record in records:
#         try:
#             # 1. Calculate `n_expected_cash_flow_pv`
#             if record.n_discount_factor is not None and record.n_expected_cash_flow is not None:
#                 record.n_expected_cash_flow_pv = record.n_discount_factor * record.n_expected_cash_flow

#             # 2. Calculate `n_12m_exp_cash_flow_pv`
#             if record.n_discount_factor is not None and record.n_12m_exp_cash_flow is not None:
#                 record.n_12m_exp_cash_flow_pv = record.n_discount_factor * record.n_12m_exp_cash_flow

#             # 3. Calculate `n_cash_shortfall`
#             if record.n_cash_flow_amount is not None and record.n_expected_cash_flow is not None:
#                 record.n_cash_shortfall = (record.n_cash_flow_amount or Decimal(0)) - (record.n_expected_cash_flow or Decimal(0))

#             # 4. Calculate `n_12m_cash_shortfall`
#             if record.n_cash_flow_amount is not None and record.n_12m_exp_cash_flow is not None:
#                 record.n_12m_cash_shortfall = (record.n_cash_flow_amount or Decimal(0)) - (record.n_12m_exp_cash_flow or Decimal(0))

#             # 5. Calculate `n_cash_shortfall_pv`
#             if record.n_discount_factor is not None and record.n_cash_shortfall is not None:
#                 record.n_cash_shortfall_pv = record.n_discount_factor * record.n_cash_shortfall

#             # 6. Calculate `n_12m_cash_shortfall_pv`
#             if record.n_discount_factor is not None and record.n_12m_cash_shortfall is not None:
#                 record.n_12m_cash_shortfall_pv = record.n_discount_factor * record.n_12m_cash_shortfall

#             updated_records.append(record)
#         except Exception as e:
#             save_log('process_cashflow_records', 'ERROR', f"Error processing record {record.v_account_number}: {e}")

#     return updated_records


# # -------------------------------------------------------
# # Main function to update cash flow fields efficiently
# # -------------------------------------------------------
# def calculate_cashflow_fields(fic_mis_date, batch_size=2000, num_threads=8, update_batch_size=5000):
#     """
#     Calculates & updates cash flow fields (PV, shortfalls, etc.) using multithreading and bulk update.
    
#     :param fic_mis_date:         The MIS date to filter records on.
#     :param batch_size:           Number of records processed by each thread in one chunk.
#     :param num_threads:          Number of parallel threads to use.
#     :param update_batch_size:    Number of records to update in a single bulk operation.
#     :return:                     1 if records were updated, 0 otherwise.
#     """
#     try:
#         # 1) Get the latest run_skey
#         run_skey = get_latest_run_skey()
#         if not run_skey:
#             return 0  # No valid run key

#         # 2) Fetch relevant records minimally with only() if your DB is large
#         #    If you do not need all fields, do: .only(...fields...).
#         records = list(
#             fsi_Financial_Cash_Flow_Cal.objects.filter(
#                 fic_mis_date=fic_mis_date,
#                 n_run_skey=run_skey
#             )
#         )

#         if not records:
#             save_log(
#                 'calculate_cashflow_fields',
#                 'INFO',
#                 f"No records found for fic_mis_date={fic_mis_date} and run_skey={run_skey}."
#             )
#             return 0

#         save_log(
#             'calculate_cashflow_fields',
#             'INFO',
#             f"Fetched {len(records)} records for processing."
#         )

#         # 3) Chunk the records for parallel processing
#         def chunker(seq, size):
#             for pos in range(0, len(seq), size):
#                 yield seq[pos:pos + size]

#         updated_records_all = []
#         # 4) Parallel process with ThreadPoolExecutor
#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = []
#             for chunk in chunker(records, batch_size):
#                 futures.append(executor.submit(process_cashflow_records, chunk))

#             # Collect results as they complete
#             for future in as_completed(futures):
#                 try:
#                     updated_records_all.extend(future.result())
#                 except Exception as e:
#                     save_log('calculate_cashflow_fields', 'ERROR', f"Error in thread execution: {e}")
#                     return 0

#         # 5) Bulk update in sub-batches
#         total_updated = len(updated_records_all)
#         if total_updated == 0:
#             save_log(
#                 'calculate_cashflow_fields',
#                 'INFO',
#                 "No records to update after processing."
#             )
#             return 0

#         with transaction.atomic():
#             for start in range(0, total_updated, update_batch_size):
#                 end = start + update_batch_size
#                 fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                     updated_records_all[start:end],
#                     [
#                         'n_expected_cash_flow_pv',
#                         'n_12m_exp_cash_flow_pv',
#                         'n_cash_shortfall',
#                         'n_12m_cash_shortfall',
#                         'n_cash_shortfall_pv',
#                         'n_12m_cash_shortfall_pv'
#                     ]
#                 )

#         save_log(
#             'calculate_cashflow_fields',
#             'INFO',
#             f"Successfully updated {total_updated} records."
#         )
#         return 1

#     except Exception as e:
#         save_log(
#             'calculate_cashflow_fields',
#             'ERROR',
#             f"Error calculating cash flow fields for fic_mis_date={fic_mis_date}, run_skey={run_skey}: {e}"
#         )
#         return 0

# from concurrent.futures import ThreadPoolExecutor
# from decimal import Decimal
# from django.db import transaction
# from ..models import fsi_Financial_Cash_Flow_Cal, Dim_Run
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
    
# def process_cashflow_records(records):
#     """
#     Function to process a batch of records and apply calculations for cash flow fields.
#     """
#     updated_records = []

#     for record in records:
#         try:
#             # 1. Calculate `n_expected_cash_flow_pv`
#             if record.n_discount_factor is not None and record.n_expected_cash_flow is not None:
#                 record.n_expected_cash_flow_pv = record.n_discount_factor * record.n_expected_cash_flow

#             # 2. Calculate `n_12m_exp_cash_flow_pv`
#             if record.n_discount_factor is not None and record.n_12m_exp_cash_flow is not None:
#                 record.n_12m_exp_cash_flow_pv = record.n_discount_factor * record.n_12m_exp_cash_flow

#             # 3. Calculate `n_cash_shortfall`
#             if record.n_cash_flow_amount is not None and record.n_expected_cash_flow is not None:
#                 record.n_cash_shortfall = (record.n_cash_flow_amount or Decimal(0)) - (record.n_expected_cash_flow or Decimal(0))

#             # 4. Calculate `n_12m_cash_shortfall`
#             if record.n_cash_flow_amount is not None and record.n_12m_exp_cash_flow is not None:
#                 record.n_12m_cash_shortfall = (record.n_cash_flow_amount or Decimal(0)) - (record.n_12m_exp_cash_flow or Decimal(0))

#             # 5. Calculate `n_cash_shortfall_pv`
#             if record.n_discount_factor is not None and record.n_cash_shortfall is not None:
#                 record.n_cash_shortfall_pv = record.n_discount_factor * record.n_cash_shortfall

#             # 6. Calculate `n_12m_cash_shortfall_pv`
#             if record.n_discount_factor is not None and record.n_12m_cash_shortfall is not None:
#                 record.n_12m_cash_shortfall_pv = record.n_discount_factor * record.n_12m_cash_shortfall

#             # Add the updated record to the list
#             updated_records.append(record)
#         except Exception as e:
#             save_log('process_cashflow_records', 'ERROR', f"Error processing record {record.v_account_number}: {e}")

#     return updated_records


# def calculate_cashflow_fields(fic_mis_date, batch_size=1000, num_threads=10):
#     """
#     Main function to calculate all required cash flow fields with multithreading and bulk update.
#     """
#     try:
#         # Fetch the relevant records for the run_skey
#         run_skey = get_latest_run_skey()
#         records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))

#         if not records:
#             save_log('calculate_cashflow_fields', 'INFO', f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
#             return 0  # Return 0 if no records are found

#         save_log('calculate_cashflow_fields', 'INFO', f"Fetched {len(records)} records for processing.")

#         # Split the records into batches
#         def chunker(seq, size):
#             return (seq[pos:pos + size] for pos in range(0, len(seq), size))

#         # Process records in parallel using ThreadPoolExecutor
#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = [executor.submit(process_cashflow_records, batch) for batch in chunker(records, batch_size)]

#             # Wait for all threads to complete and gather the results
#             updated_batches = []
#             for future in futures:
#                 try:
#                     updated_batches.extend(future.result())
#                 except Exception as e:
#                     save_log('calculate_cashflow_fields', 'ERROR', f"Error in thread execution: {e}")
#                     return 0  # Return 0 if any thread encounters an error

#         # Perform a bulk update to save all the records at once
#         with transaction.atomic():
#             fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
#                 'n_expected_cash_flow_pv', 
#                 'n_12m_exp_cash_flow_pv',
#                 'n_cash_shortfall',
#                 'n_12m_cash_shortfall',
#                 'n_cash_shortfall_pv',
#                 'n_12m_cash_shortfall_pv'
#             ])

#         save_log('calculate_cashflow_fields', 'INFO', f"Successfully updated {len(updated_batches)} records.")
#         return 1  # Return 1 on successful completion

#     except Exception as e:
#         save_log('calculate_cashflow_fields', 'ERROR', f"Error calculating cash flow fields for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
#         return 0
