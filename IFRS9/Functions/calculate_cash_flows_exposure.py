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

def calculate_ead_by_buckets(fic_mis_date):
    """
    Efficiently calculate and update n_exposure_at_default for each cash flow bucket 
    using a temporary table and set-based SQL operations.
    """
    run_skey = get_latest_run_skey()
    if not run_skey:
        return 0

    try:
        with connection.cursor() as cursor, transaction.atomic():
            # Step 1: Create a temporary table with the computed cumulative_ead values.
            create_temp_sql = """
                CREATE TEMPORARY TABLE temp_ead AS
                SELECT
                    id,
                    SUM(n_cash_flow_amount * n_discount_factor)
                    OVER (
                        PARTITION BY v_account_number
                        ORDER BY n_cash_flow_bucket_id
                        ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
                    ) AS cumulative_ead
                FROM fsi_financial_cash_flow_cal
                WHERE fic_mis_date = %s AND n_run_skey = %s;
            """
            cursor.execute(create_temp_sql, [fic_mis_date, run_skey])

            # Step 2: Update the original table by joining with the temporary table.
            update_sql = """
                UPDATE fsi_financial_cash_flow_cal AS cf
                JOIN temp_ead AS te ON cf.id = te.id
                SET cf.n_exposure_at_default = te.cumulative_ead;
            """
            cursor.execute(update_sql)
            updated_count = cursor.rowcount

            # Step 3: Drop the temporary table.
            cursor.execute("DROP TEMPORARY TABLE IF EXISTS temp_ead;")

        save_log('calculate_ead_by_buckets', 'INFO', f"Updated {updated_count} records.")
        return 1 if updated_count > 0 else 0

    except Exception as e:
        save_log('calculate_ead_by_buckets', 'ERROR', f"Error: {e}")
        return 0



# from concurrent.futures import ThreadPoolExecutor
# from decimal import Decimal
# from django.db import transaction
# from django.db.models import F, Sum
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


# def _process_ead_for_account(
#     account_number, 
#     account_records, 
#     account_sums_dict
# ):
#     """
#     Calculate decreasing EAD for a single account.

#     - account_number: The account identifier (v_account_number).
#     - account_records: List of records (already sorted by n_cash_flow_bucket_id).
#     - account_sums_dict: Dictionary with precomputed total discounted CF for each account.
#     """
#     updated = []

#     # Pull initial EAD (sum of discounted CF) from the aggregator dictionary.
#     # If not found, default to 0.
#     cumulative_ead = account_sums_dict.get(account_number, Decimal(0))

#     for rec in account_records:
#         if rec.n_cash_flow_amount is not None and rec.n_discount_factor is not None:
#             # Set the current EAD
#             rec.n_exposure_at_default = cumulative_ead
#             # Subtract discounted cash flow for this bucket
#             cumulative_ead -= rec.n_cash_flow_amount * rec.n_discount_factor
#         else:
#             # If any required field is missing, set EAD to None
#             rec.n_exposure_at_default = None
#         updated.append(rec)

#     return updated


# def _process_ead_records_batch(
#     batch_of_accounts, 
#     account_records_dict, 
#     account_sums_dict
# ):
#     """
#     Process a chunk of accounts in a separate thread.

#     - batch_of_accounts: A list of account numbers belonging to this thread's chunk.
#     - account_records_dict: Dict of { account_number -> [records for that account] }.
#     - account_sums_dict: Dict of { account_number -> sum of discounted CF }.
#     """
#     updated_records = []
#     for account in batch_of_accounts:
#         records = account_records_dict[account]
#         updated_records.extend(
#             _process_ead_for_account(account, records, account_sums_dict)
#         )
#     return updated_records


# def calculate_ead_by_buckets(fic_mis_date, batch_size=100, num_threads=10):
#     """
#     Main function to calculate EAD for each cash flow bucket with multithreading and a single bulk update.

#     Steps:
#     1) Get run_skey.
#     2) Precompute sum of discounted CF for each account (initial EAD).
#     3) Fetch and group records by account, sorted by bucket.
#     4) Chunk the accounts and process them in parallel.
#     5) Perform one bulk update with all results.
#     """
#     try:
#         run_skey = get_latest_run_skey()

#         # --- STEP 1: Compute total discounted CF per account in ONE DB query ---
#         # Using Django's F expressions for efficient DB-level multiplication:
#         account_sums_qs = (
#             fsi_Financial_Cash_Flow_Cal.objects
#             .filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey)
#             .values('v_account_number')
#             .annotate(
#                 total_dcf=Sum(
#                     F('n_cash_flow_amount') * F('n_discount_factor')
#                 )
#             )
#         )

#         # Build a dict: { 'ACCOUNT123': Decimal(...) }
#         account_sums_dict = {
#             row['v_account_number']: row['total_dcf'] or Decimal(0)
#             for row in account_sums_qs
#         }

#         # --- STEP 2: Fetch detailed records (minimal fields) ---
#         # Ordering ensures the buckets are in ascending order for each account.
#         records = list(
#             fsi_Financial_Cash_Flow_Cal.objects
#             .filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey)
#             .only(
#                 'v_account_number',
#                 'n_cash_flow_bucket_id',
#                 'n_cash_flow_amount',
#                 'n_discount_factor',
#                 'n_exposure_at_default'
#             )
#             .order_by('v_account_number', 'n_cash_flow_bucket_id')
#         )

#         if not records:
#             save_log(
#                 'calculate_ead_by_buckets',
#                 'INFO',
#                 f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}."
#             )
#             return 0

#         save_log(
#             'calculate_ead_by_buckets',
#             'INFO',
#             f"Fetched {len(records)} records for processing."
#         )

#         # --- STEP 3: Group records by account in memory ---
#         account_records_dict = {}
#         for rec in records:
#             acc = rec.v_account_number
#             if acc not in account_records_dict:
#                 account_records_dict[acc] = []
#             account_records_dict[acc].append(rec)

#         # We'll have one entry per account: { 'ACCOUNT123': [record1, record2, ...] }

#         # --- STEP 4: Chunk the accounts and process in parallel ---
#         all_accounts = list(account_records_dict.keys())

#         def chunk_accounts(seq, size):
#             for pos in range(0, len(seq), size):
#                 yield seq[pos:pos + size]

#         updated_records_all = []

#         with ThreadPoolExecutor(max_workers=num_threads) as executor:
#             futures = []
#             for batch_of_accounts in chunk_accounts(all_accounts, batch_size):
#                 futures.append(
#                     executor.submit(
#                         _process_ead_records_batch,
#                         batch_of_accounts,
#                         account_records_dict,
#                         account_sums_dict
#                     )
#                 )

#             # Collect results from each thread
#             for future in futures:
#                 try:
#                     updated_records_all.extend(future.result())
#                 except Exception as e:
#                     save_log(
#                         'calculate_ead_by_buckets',
#                         'ERROR',
#                         f"Error in thread execution: {e}"
#                     )
#                     return 0  # Immediately return on any fatal thread error

#         # --- STEP 5: Perform a single bulk update ---
#         with transaction.atomic():
#             fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                 updated_records_all,
#                 ['n_exposure_at_default']
#             )

#         save_log(
#             'calculate_ead_by_buckets',
#             'INFO',
#             f"Successfully updated {len(updated_records_all)} records."
#         )
#         return 1

#     except Exception as e:
#         # If something goes wrong at any step, log and return 0
#         save_log(
#             'calculate_ead_by_buckets',
#             'ERROR',
#             f"Error calculating EAD for fic_mis_date {fic_mis_date}, run_skey {run_skey}: {e}"
#         )
#         return 0
