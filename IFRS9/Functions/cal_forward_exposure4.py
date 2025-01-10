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
def calculate_12m_expected_loss_fields_setbased(fic_mis_date):
    try:
        run_skey = get_latest_run_skey()
        if not run_skey:
            return 0

        with connection.cursor() as cursor, transaction.atomic():
            sql = """
                UPDATE fsi_financial_cash_flow_cal
                SET 
                    n_12m_fwd_expected_loss = n_exposure_at_default * n_12m_per_period_pd * n_lgd_percent,
                    n_12m_fwd_expected_loss_pv = n_discount_factor * (n_exposure_at_default * n_12m_per_period_pd * n_lgd_percent)
                WHERE fic_mis_date = %s AND n_run_skey = %s;
            """
            cursor.execute(sql, [fic_mis_date, run_skey])
            updated_count = cursor.rowcount

        save_log('calculate_12m_expected_loss_fields_setbased', 'INFO', 
                 f"Updated {updated_count} records for 12m expected loss.")
        return 1 if updated_count > 0 else 0

    except Exception as e:
        save_log('calculate_12m_expected_loss_fields_setbased', 'ERROR', f"Error: {e}")
        return 0

def calculate_forward_expected_loss_fields_setbased(fic_mis_date):
    try:
        run_skey = get_latest_run_skey()
        if not run_skey:
            return 0

        with connection.cursor() as cursor, transaction.atomic():
            sql = """
                UPDATE fsi_financial_cash_flow_cal
                SET 
                    n_forward_expected_loss = n_exposure_at_default * n_per_period_impaired_prob * n_lgd_percent,
                    n_forward_expected_loss_pv = n_discount_factor * (n_exposure_at_default * n_per_period_impaired_prob * n_lgd_percent)
                WHERE fic_mis_date = %s AND n_run_skey = %s;
            """
            cursor.execute(sql, [fic_mis_date, run_skey])
            updated_count = cursor.rowcount

        save_log('calculate_forward_expected_loss_fields_setbased', 'INFO', 
                 f"Updated {updated_count} records for forward expected loss.")
        return 1 if updated_count > 0 else 0

    except Exception as e:
        save_log('calculate_forward_expected_loss_fields_setbased', 'ERROR', f"Error: {e}")
        return 0


def calculate_forward_loss_fields(fic_mis_date):
    """
    Main function to calculate both 12-month and forward expected loss fields using set-based SQL updates.
    """
    result_12m = calculate_12m_expected_loss_fields_setbased(fic_mis_date)
    if result_12m == 1:
        return calculate_forward_expected_loss_fields_setbased(fic_mis_date)
    else:
        save_log('calculate_forward_loss_fields_setbased', 'ERROR', 
                 f"Failed 12m calculation for {fic_mis_date}.")
        return 0


# from concurrent.futures import ThreadPoolExecutor, as_completed
# from decimal import Decimal
# from django.db import transaction
# from django.db.models import F
# from ..models import fsi_Financial_Cash_Flow_Cal, Dim_Run
# from .save_log import save_log

# # Batch size used for final bulk update (can be tuned)
# UPDATE_BATCH_SIZE = 5000


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


# # -----------------------------------------------------------------------------
# # Helper Functions: 12-Month Expected Loss
# # -----------------------------------------------------------------------------
# def process_12m_expected_loss(records):
#     """
#     Process a batch of records to calculate 12-month forward loss fields.
#     Returns a list of updated records.
#     """
#     updated_records = []
#     for record in records:
#         try:
#             # 1. Calculate `n_12m_fwd_expected_loss`
#             if (record.n_exposure_at_default is not None
#                 and record.n_12m_per_period_pd is not None
#                 and record.n_lgd_percent is not None):
#                 record.n_12m_fwd_expected_loss = (
#                     record.n_exposure_at_default
#                     * record.n_12m_per_period_pd
#                     * record.n_lgd_percent
#                 )

#             # 2. Calculate `n_12m_fwd_expected_loss_pv`
#             if (record.n_discount_factor is not None
#                 and record.n_12m_fwd_expected_loss is not None):
#                 record.n_12m_fwd_expected_loss_pv = (
#                     record.n_discount_factor
#                     * record.n_12m_fwd_expected_loss
#                 )

#             updated_records.append(record)

#         except Exception as e:
#             save_log('process_12m_expected_loss', 'ERROR',
#                      f"Error processing record {record.v_account_number}: {e}")

#     return updated_records


# def calculate_12m_expected_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
#     """
#     Calculate 12-month forward loss fields with multithreading and bulk update.
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         if not run_skey:
#             return 0  # No valid run key found

#         # Fetch only the fields needed for calculation
#         records_qs = fsi_Financial_Cash_Flow_Cal.objects.filter(
#             fic_mis_date=fic_mis_date,
#             n_run_skey=run_skey
#         ).only(
#             'v_account_number',
#             'n_exposure_at_default',
#             'n_12m_per_period_pd',
#             'n_lgd_percent',
#             'n_discount_factor',
#             'n_12m_fwd_expected_loss',
#             'n_12m_fwd_expected_loss_pv'
#         )

#         # Convert queryset to a list in memory
#         records = list(records_qs)
#         if not records:
#             save_log('calculate_12m_expected_loss_fields', 'INFO',
#                      f"No records found for fic_mis_date={fic_mis_date}, run_skey={run_skey}.")
#             return 0

#         save_log('calculate_12m_expected_loss_fields', 'INFO',
#                  f"Fetched {len(records)} records for processing 12m forward loss.")

#         # Split the records into chunks for parallel processing
#         def chunker(seq, size):
#             for pos in range(0, len(seq), size):
#                 yield seq[pos:pos + size]

#         updated_records_all = []

#         # Multithreading
#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = []
#             for batch in chunker(records, batch_size):
#                 futures.append(executor.submit(process_12m_expected_loss, batch))

#             # Gather the results
#             for future in as_completed(futures):
#                 try:
#                     updated_records_all.extend(future.result())
#                 except Exception as e:
#                     save_log('calculate_12m_expected_loss_fields', 'ERROR',
#                              f"Error in thread execution: {e}")
#                     return 0

#         # Bulk update in sub-batches
#         total_updated = len(updated_records_all)
#         if total_updated == 0:
#             save_log('calculate_12m_expected_loss_fields', 'INFO',
#                      "No records were updated (0 after processing).")
#             return 0

#         with transaction.atomic():
#             for start in range(0, total_updated, UPDATE_BATCH_SIZE):
#                 end = start + UPDATE_BATCH_SIZE
#                 fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                     updated_records_all[start:end],
#                     ['n_12m_fwd_expected_loss', 'n_12m_fwd_expected_loss_pv']
#                 )

#         save_log('calculate_12m_expected_loss_fields', 'INFO',
#                  f"Successfully updated {total_updated} records for 12m forward loss.")
#         return 1

#     except Exception as e:
#         save_log('calculate_12m_expected_loss_fields', 'ERROR',
#                  f"Error calculating 12m forward loss for fic_mis_date={fic_mis_date}, run_skey={run_skey}: {e}")
#         return 0


# # -----------------------------------------------------------------------------
# # Helper Functions: Forward Expected Loss
# # -----------------------------------------------------------------------------
# def process_forward_expected_loss(records):
#     """
#     Process a batch of records to calculate forward expected loss fields.
#     Returns a list of updated records.
#     """
#     updated_records = []
#     for record in records:
#         try:
#             # 1. Calculate `n_forward_expected_loss`
#             if (record.n_exposure_at_default is not None
#                 and record.n_per_period_impaired_prob is not None
#                 and record.n_lgd_percent is not None):
#                 record.n_forward_expected_loss = (
#                     record.n_exposure_at_default
#                     * record.n_per_period_impaired_prob
#                     * record.n_lgd_percent
#                 )

#             # 2. Calculate `n_forward_expected_loss_pv`
#             if (record.n_discount_factor is not None
#                 and record.n_forward_expected_loss is not None):
#                 record.n_forward_expected_loss_pv = (
#                     record.n_discount_factor
#                     * record.n_forward_expected_loss
#                 )

#             updated_records.append(record)

#         except Exception as e:
#             save_log('process_forward_expected_loss', 'ERROR',
#                      f"Error processing record {record.v_account_number}: {e}")

#     return updated_records


# def calculate_forward_expected_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
#     """
#     Calculate forward expected loss fields with multithreading and bulk update.
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         if not run_skey:
#             return 0  # No valid run key

#         # Fetch only needed fields
#         records_qs = fsi_Financial_Cash_Flow_Cal.objects.filter(
#             fic_mis_date=fic_mis_date,
#             n_run_skey=run_skey
#         ).only(
#             'v_account_number',
#             'n_exposure_at_default',
#             'n_per_period_impaired_prob',
#             'n_lgd_percent',
#             'n_discount_factor',
#             'n_forward_expected_loss',
#             'n_forward_expected_loss_pv'
#         )

#         records = list(records_qs)
#         if not records:
#             save_log('calculate_forward_expected_loss_fields', 'INFO',
#                      f"No records found for fic_mis_date={fic_mis_date}, run_skey={run_skey}.")
#             return 0

#         save_log('calculate_forward_expected_loss_fields', 'INFO',
#                  f"Fetched {len(records)} records for processing forward loss.")

#         def chunker(seq, size):
#             for pos in range(0, len(seq), size):
#                 yield seq[pos:pos + size]

#         updated_records_all = []

#         # Multithreading
#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = []
#             for batch in chunker(records, batch_size):
#                 futures.append(executor.submit(process_forward_expected_loss, batch))

#             # Collect results
#             for future in as_completed(futures):
#                 try:
#                     updated_records_all.extend(future.result())
#                 except Exception as e:
#                     save_log('calculate_forward_expected_loss_fields', 'ERROR',
#                              f"Error in thread execution: {e}")
#                     return 0

#         total_updated = len(updated_records_all)
#         if total_updated == 0:
#             save_log('calculate_forward_expected_loss_fields', 'INFO',
#                      "No records were updated (0 after processing).")
#             return 0

#         # Bulk update in sub-batches
#         with transaction.atomic():
#             for start in range(0, total_updated, UPDATE_BATCH_SIZE):
#                 end = start + UPDATE_BATCH_SIZE
#                 fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                     updated_records_all[start:end],
#                     ['n_forward_expected_loss', 'n_forward_expected_loss_pv']
#                 )

#         save_log('calculate_forward_expected_loss_fields', 'INFO',
#                  f"Successfully updated {total_updated} records for forward expected loss.")
#         return 1

#     except Exception as e:
#         save_log('calculate_forward_expected_loss_fields', 'ERROR',
#                  f"Error calculating forward loss for fic_mis_date={fic_mis_date}, run_skey={run_skey}: {e}")
#         return 0


# # -----------------------------------------------------------------------------
# # Main Wrapper: Calculate Both 12M and Forward Expected Loss
# # -----------------------------------------------------------------------------
# def calculate_forward_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
#     """
#     Main function to calculate forward loss fields in two stages:
#     1) 12-month expected loss calculation
#     2) Forward expected loss calculation
#     """
#     result_12m = calculate_12m_expected_loss_fields(fic_mis_date, batch_size, num_threads)
#     if result_12m == 1:
#         return calculate_forward_expected_loss_fields(fic_mis_date, batch_size, num_threads)
#     else:
#         save_log('calculate_forward_loss_fields', 'ERROR',
#                  f"Failed to complete 12-month expected loss calculation for fic_mis_date={fic_mis_date}.")
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

# def process_12m_expected_loss(records):
#     """
#     Function to process a batch of records and apply calculations for 12-month forward loss fields.
#     """
#     updated_records = []

#     for record in records:
#         try:
#             # Calculate `n_12m_fwd_expected_loss`
#             if record.n_exposure_at_default is not None and record.n_12m_per_period_pd is not None and record.n_lgd_percent is not None:
#                 record.n_12m_fwd_expected_loss = record.n_exposure_at_default * record.n_12m_per_period_pd * record.n_lgd_percent

#             # Calculate `n_12m_fwd_expected_loss_pv`
#             if record.n_discount_factor is not None and record.n_12m_fwd_expected_loss is not None:
#                 record.n_12m_fwd_expected_loss_pv = record.n_discount_factor * record.n_12m_fwd_expected_loss

#             updated_records.append(record)

#         except Exception as e:
#             save_log('process_12m_expected_loss', 'ERROR', f"Error processing record {record.v_account_number}: {e}")

#     return updated_records

# def process_forward_expected_loss(records):
#     """
#     Function to process a batch of records and apply calculations for forward loss fields.
#     """
#     updated_records = []

#     for record in records:
#         try:
#             # Calculate `n_forward_expected_loss`
#             if record.n_exposure_at_default is not None and record.n_per_period_impaired_prob is not None and record.n_lgd_percent is not None:
#                 record.n_forward_expected_loss = record.n_exposure_at_default * record.n_per_period_impaired_prob * record.n_lgd_percent

#             # Calculate `n_forward_expected_loss_pv`
#             if record.n_discount_factor is not None and record.n_forward_expected_loss is not None:
#                 record.n_forward_expected_loss_pv = record.n_discount_factor * record.n_forward_expected_loss

#             updated_records.append(record)

#         except Exception as e:
#             save_log('process_forward_expected_loss', 'ERROR', f"Error processing record {record.v_account_number}: {e}")

#     return updated_records

# def calculate_12m_expected_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
#     """
#     Calculate 12-month expected loss fields with multithreading and bulk update.
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))

#         if not records:
#             save_log('calculate_12m_expected_loss_fields', 'INFO', f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
#             return 0

#         save_log('calculate_12m_expected_loss_fields', 'INFO', f"Fetched {len(records)} records for processing.")

#         def chunker(seq, size):
#             return (seq[pos:pos + size] for pos in range(0, len(seq), size))

#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = [executor.submit(process_12m_expected_loss, batch) for batch in chunker(records, batch_size)]
#             updated_batches = []
#             for future in futures:
#                 try:
#                     updated_batches.extend(future.result())
#                 except Exception as e:
#                     save_log('calculate_12m_expected_loss_fields', 'ERROR', f"Error in thread execution: {e}")
#                     return 0

#         with transaction.atomic():
#             fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
#                 'n_12m_fwd_expected_loss', 
#                 'n_12m_fwd_expected_loss_pv'
#             ])

#         save_log('calculate_12m_expected_loss_fields', 'INFO', f"Successfully updated {len(updated_batches)} records.")
#         return 1

#     except Exception as e:
#         save_log('calculate_12m_expected_loss_fields', 'ERROR', f"Error calculating 12-month forward loss fields for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
#         return 0

# def calculate_forward_expected_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
#     """
#     Calculate forward expected loss fields with multithreading and bulk update.
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))

#         if not records:
#             save_log('calculate_forward_expected_loss_fields', 'INFO', f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
#             return 0

#         save_log('calculate_forward_expected_loss_fields', 'INFO', f"Fetched {len(records)} records for processing.")

#         def chunker(seq, size):
#             return (seq[pos:pos + size] for pos in range(0, len(seq), size))

#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = [executor.submit(process_forward_expected_loss, batch) for batch in chunker(records, batch_size)]
#             updated_batches = []
#             for future in futures:
#                 try:
#                     updated_batches.extend(future.result())
#                 except Exception as e:
#                     save_log('calculate_forward_expected_loss_fields', 'ERROR', f"Error in thread execution: {e}")
#                     return 0

#         with transaction.atomic():
#             fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
#                 'n_forward_expected_loss',  
#                 'n_forward_expected_loss_pv'
#             ])

#         save_log('calculate_forward_expected_loss_fields', 'INFO', f"Successfully updated {len(updated_batches)} records.")
#         return 1

#     except Exception as e:
#         save_log('calculate_forward_expected_loss_fields', 'ERROR', f"Error calculating forward loss fields for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
#         return 0

# def calculate_forward_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
#     """
#     Main function to calculate forward loss fields in two stages.
#     """
#     result = calculate_12m_expected_loss_fields(fic_mis_date, batch_size, num_threads)
#     if result == 1:
#         return calculate_forward_expected_loss_fields(fic_mis_date, batch_size, num_threads)
#     else:
#         save_log('calculate_forward_loss_fields', 'ERROR', f"Failed to complete 12-month expected loss calculation for fic_mis_date {fic_mis_date}.")
#         return 0
