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
            save_log('get_latest_run_skey', 'ERROR', "No run key is available in Dim_Run")
            return None
        return run_record.latest_run_skey
    except Dim_Run.DoesNotExist:
        save_log('get_latest_run_skey', 'ERROR', "Dim_Run table is missing.")
        return None

def calculate_discount_factors(fic_mis_date):
    """
    Efficiently calculate and update discount rates and factors for all records matching the given fic_mis_date and latest run key using a single set-based SQL statement.
    """
    try:
        run_skey = get_latest_run_skey()
        if not run_skey:
            return 0

        # Perform set-based update in a single transaction
        with transaction.atomic(), connection.cursor() as cursor:
            sql = """
                UPDATE fsi_financial_cash_flow_cal
                SET 
                    n_discount_rate = COALESCE(n_effective_interest_rate, n_discount_rate),
                    n_discount_factor = CASE 
                        WHEN COALESCE(n_effective_interest_rate, n_discount_rate) IS NOT NULL 
                             AND n_cash_flow_bucket_id IS NOT NULL
                        THEN 1 / POWER(1 + (COALESCE(n_effective_interest_rate, n_discount_rate) / 100), 
                                       (n_cash_flow_bucket_id / 12))
                        ELSE n_discount_factor
                    END
                WHERE fic_mis_date = %s AND n_run_skey = %s;
            """
            cursor.execute(sql, [fic_mis_date, run_skey])
            updated_count = cursor.rowcount

        save_log('calculate_discount_factors', 'INFO', f"Successfully updated {updated_count} records.")
        return 1 if updated_count > 0 else 0

    except Exception as e:
        save_log('calculate_discount_factors', 'ERROR', f"Error calculating discount factors: {e}")
        return 0


# from concurrent.futures import ThreadPoolExecutor, as_completed
# from decimal import Decimal
# from math import pow
# from django.db import transaction
# from django.db.models import F
# from ..models import fsi_Financial_Cash_Flow_Cal, Dim_Run
# from .save_log import save_log


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


# def process_discount_records(records):
#     """
#     Process a batch of records for discount calculations.
#     Returns a list of updated records.
#     """
#     updated_records = []
#     for record in records:
#         try:
#             # 1. Set `n_discount_rate` based on whether n_effective_interest_rate is present
#             if record.n_effective_interest_rate is not None:
#                 record.n_discount_rate = record.n_effective_interest_rate
#             # Otherwise, keep existing n_discount_rate (no change needed)

#             # 2. Calculate `n_discount_factor`
#             if record.n_discount_rate is not None and record.n_cash_flow_bucket_id is not None:
#                 # discount_factor = 1 / (1 + discount_rate/100)^(bucket_id/12)
#                 discount_rate_decimal = Decimal(record.n_discount_rate) / Decimal(100)
#                 exponent = Decimal(record.n_cash_flow_bucket_id) / Decimal(12)
#                 record.n_discount_factor = Decimal(1) / (Decimal(pow((1 + discount_rate_decimal), exponent)))
#             # Otherwise, keep existing n_discount_factor

#             updated_records.append(record)

#         except Exception as e:
#             save_log('process_discount_records', 'ERROR',
#                      f"Error processing record {record.v_account_number}: {e}")
#     return updated_records


# def calculate_discount_factors(fic_mis_date, batch_size=2000, num_threads=4, update_batch_size=5000):
#     """
#     Main function to calculate discount rates and factors with multithreading and bulk update.

#     :param fic_mis_date:      The MIS date to filter fsi_Financial_Cash_Flow_Cal records
#     :param batch_size:        Number of records processed per thread chunk
#     :param num_threads:       Number of worker threads in ThreadPoolExecutor
#     :param update_batch_size: Number of records to update in a single bulk update sub-batch
#     :return:                  1 on success, 0 on failure or no records
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         if not run_skey:
#             return 0  # No valid run key found

#         # Fetch only the fields required for discount calculations
#         records_qs = fsi_Financial_Cash_Flow_Cal.objects.filter(
#             fic_mis_date=fic_mis_date,
#             n_run_skey=run_skey
#         ).only(
#             'v_account_number',
#             'n_effective_interest_rate',
#             'n_discount_rate',
#             'n_cash_flow_bucket_id',
#             'n_discount_factor'
#         )

#         # Convert to list in memory
#         records = list(records_qs)
#         if not records:
#             save_log('calculate_discount_factors', 'INFO',
#                      f"No records found for fic_mis_date={fic_mis_date}, run_skey={run_skey}.")
#             return 0

#         save_log('calculate_discount_factors', 'INFO',
#                  f"Fetched {len(records)} records for processing discount factors.")

#         # Chunker to split the records into smaller batches
#         def chunker(seq, size):
#             for pos in range(0, len(seq), size):
#                 yield seq[pos:pos + size]

#         updated_records_all = []
#         error_occurred = False

#         # Parallel processing
#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = []
#             for batch in chunker(records, batch_size):
#                 futures.append(executor.submit(process_discount_records, batch))

#             for future in as_completed(futures):
#                 try:
#                     updated_records_all.extend(future.result())
#                 except Exception as e:
#                     save_log('calculate_discount_factors', 'ERROR', f"Thread error: {e}")
#                     error_occurred = True

#         if error_occurred:
#             return 0  # Return early if any thread failed

#         total_updated = len(updated_records_all)
#         if total_updated == 0:
#             save_log('calculate_discount_factors', 'INFO', "No records to update after processing.")
#             return 0

#         # Perform a bulk update in sub-batches
#         with transaction.atomic():
#             for start in range(0, total_updated, update_batch_size):
#                 end = start + update_batch_size
#                 fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                     updated_records_all[start:end],
#                     ['n_discount_rate', 'n_discount_factor']
#                 )

#         save_log('calculate_discount_factors', 'INFO',
#                  f"Successfully updated {total_updated} records with discount factors.")
#         return 1

#     except Exception as e:
#         save_log('calculate_discount_factors', 'ERROR',
#                  f"Error calculating discount factors for fic_mis_date={fic_mis_date}: {e}")
#         return 0

