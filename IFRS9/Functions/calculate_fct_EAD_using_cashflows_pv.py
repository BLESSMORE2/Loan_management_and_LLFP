from django.db import connection, transaction
from ..models import FCT_Stage_Determination
from .save_log import save_log

def update_stage_determination_ead_with_cashflow_pv(fic_mis_date):
    """
    SQL-based approach to update FCT_Stage_Determination table's n_exposure_at_default field
    based on the sum of discounted cash flows from fsi_Financial_Cash_Flow_Cal.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Step 1: Fetch the latest run key
            cursor.execute("""
                SELECT latest_run_skey FROM dim_run FETCH FIRST 1 ROWS ONLY
            """)
            result = cursor.fetchone()
            if not result:
                save_log(
                    'update_stage_determination_ead_with_cashflow_pv',
                    'ERROR',
                    "No latest run key found in Dim_Run table."
                )
                return 0
            run_skey = result[0]

            # Step 2: Compute and update n_exposure_at_default
            cursor.execute("""
                UPDATE fct_stage_determination sd
                SET n_exposure_at_default = (
                    SELECT SUM(fc.n_cash_flow_amount * fc.n_discount_factor)
                    FROM fsi_financial_cash_flow_cal fc
                    WHERE fc.v_account_number = sd.n_account_number
                      AND fc.fic_mis_date = %s
                      AND fc.n_run_skey = %s
                )
                WHERE sd.fic_mis_date = %s
                  AND sd.n_exposure_at_default IS NULL
                  AND sd.n_prod_code IS NOT NULL;
            """, [fic_mis_date, run_skey, fic_mis_date])

        # Log success
        save_log(
            'update_stage_determination_ead_with_cashflow_pv',
            'INFO',
            f"Successfully updated EAD for FCT_Stage_Determination with fic_mis_date={fic_mis_date}."
        )
        return 1  # Success

    except Exception as e:
        # Log any error
        save_log(
            'update_stage_determination_ead_with_cashflow_pv',
            'ERROR',
            f"Exception during update process for fic_mis_date={fic_mis_date}: {e}"
        )
        return 0  # Failure


# from django.db import transaction
# from django.db.models import Sum, F
# from decimal import Decimal
# from concurrent.futures import ThreadPoolExecutor, as_completed

# from ..models import (
#     FCT_Stage_Determination,
#     fsi_Financial_Cash_Flow_Cal,
#     Dim_Run
# )
# from .save_log import save_log

# # ------------------------------------------------------------------------
# # Utility to fetch the latest run key from Dim_Run
# # ------------------------------------------------------------------------
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


# # ------------------------------------------------------------------------
# # Step 1: Precompute the sum of discounted cash flows for each account
# # ------------------------------------------------------------------------
# def precompute_discounted_cashflows(fic_mis_date, run_skey):
#     """
#     Returns a dict mapping account_number -> sum_of_discounted_cash_flows,
#     computed in a single DB query for high performance.
#     """
#     # Aggregate sums in the database
#     cf_sums = (
#         fsi_Financial_Cash_Flow_Cal.objects
#         .filter(
#             fic_mis_date=fic_mis_date,
#             n_run_skey=run_skey
#         )
#         .values('v_account_number')
#         .annotate(
#             total_dcf=Sum(F('n_cash_flow_amount') * F('n_discount_factor'))
#         )
#     )

#     # Convert the QuerySet into a dict for O(1) lookups
#     # defaulting to Decimal(0) if an account isn't present
#     return {
#         row['v_account_number']: row['total_dcf'] or Decimal(0)
#         for row in cf_sums
#     }


# # ------------------------------------------------------------------------
# # Step 2: Worker function to process a batch of stage determination entries
# # ------------------------------------------------------------------------
# def process_stage_entries_batch(entries_batch, account_sums_dict):
#     """
#     Given a list of FCT_Stage_Determination entries and a dict of
#     account -> sum of discounted cash flows, update the EAD on each entry.
#     Returns the updated entries.
#     """
#     updated_entries_local = []

#     for entry in entries_batch:
#         try:
#             # Lookup sum of discounted cash flows for this account
#             ead_value = account_sums_dict.get(entry.n_account_number, Decimal(0))

#             # Update only if we found a value or default to 0
#             # (If you prefer to set it to None if missing, adjust accordingly.)
#             entry.n_exposure_at_default = ead_value
#             updated_entries_local.append(entry)

#         except Exception as e:
#             save_log(
#                 'process_stage_entries_batch',
#                 'ERROR',
#                 f"Error processing entry {entry.n_account_number}: {e}"
#             )
#     return updated_entries_local


# # ------------------------------------------------------------------------
# # Step 3: Main function to update the table with parallel processing
# # ------------------------------------------------------------------------
# def update_stage_determination_ead_with_cashflow_pv(
#     fic_mis_date,
#     chunk_size=2000,
#     max_workers=8
# ):
#     """
#     Update FCT_Stage_Determination table's n_exposure_at_default field
#     based on the sum of discounted cash flows from fsi_Financial_Cash_Flow_Cal.

#     Steps:
#     1) Get latest run_skey.
#     2) Precompute discounted cash flow sums for all accounts in one big query.
#     3) Query all stage determination entries that need EAD updates.
#     4) Process them in parallel (chunked) to set EAD from the precomputed sums.
#     5) Bulk update results in the DB in minimal write operations.

#     :param fic_mis_date: The MIS date used to filter both tables.
#     :param chunk_size: How many Stage Determination entries to process per thread batch.
#     :param max_workers: Number of parallel threads to use.
#     :return: 1 if updates occurred, 0 otherwise.
#     """
#     try:
#         # 1) Get the latest run key
#         run_skey = get_latest_run_skey()

#         # 2) Precompute discounted cash flows: account -> sum of DCF
#         account_sums_dict = precompute_discounted_cashflows(fic_mis_date, run_skey)

#         # 3) Fetch Stage Determination entries needing EAD updates
#         stage_qs = (
#             FCT_Stage_Determination.objects.filter(
#                 fic_mis_date=fic_mis_date,
#                 n_exposure_at_default__isnull=True
#             )
#             .exclude(n_prod_code__isnull=True)
#             .only('n_account_number', 'n_exposure_at_default', 'fic_mis_date', 'n_prod_code')
#         )

#         if not stage_qs.exists():
#             save_log(
#                 'update_stage_determination_accrued_interest_and_ead',
#                 'INFO',
#                 f"No records found with NULL EAD for fic_mis_date={fic_mis_date}."
#             )
#             return 0

#         save_log(
#             'update_stage_determination_accrued_interest_and_ead',
#             'INFO',
#             f"Processing {stage_qs.count()} records for fic_mis_date={fic_mis_date}, run_skey={run_skey}."
#         )

#         updated_entries = []
#         error_logs = {}

#         # 4) Process the Stage Determination entries in parallel
#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = []
#             batch = []

#             # We'll iterate the queryset in chunks (streamed from DB)
#             for entry in stage_qs.iterator(chunk_size=chunk_size):
#                 batch.append(entry)
#                 if len(batch) >= chunk_size:
#                     futures.append(
#                         executor.submit(process_stage_entries_batch, batch, account_sums_dict)
#                     )
#                     batch = []

#             # Handle leftover batch
#             if batch:
#                 futures.append(
#                     executor.submit(process_stage_entries_batch, batch, account_sums_dict)
#                 )

#             # Collect results from threads
#             for future in as_completed(futures):
#                 try:
#                     result_batch = future.result()
#                     updated_entries.extend(result_batch)
#                 except Exception as exc:
#                     # Log the error but keep going
#                     error_msg = f"Thread error: {exc}"
#                     if error_msg not in error_logs:
#                         error_logs[error_msg] = 1

#         # 5) Bulk update in batches
#         total_updated = len(updated_entries)
#         if total_updated > 0:
#             # You can adjust this final update chunk_size as needed
#             update_chunk_size = 5000
#             with transaction.atomic():
#                 for i in range(0, total_updated, update_chunk_size):
#                     FCT_Stage_Determination.objects.bulk_update(
#                         updated_entries[i : i + update_chunk_size],
#                         ['n_exposure_at_default']
#                     )

#             save_log(
#                 'update_stage_determination_accrued_interest_and_ead',
#                 'INFO',
#                 f"Successfully updated {total_updated} records with EAD."
#             )
#             # Log each unique thread error
#             for error_message in error_logs:
#                 save_log(
#                     'update_stage_determination_accrued_interest_and_ead',
#                     'ERROR',
#                     error_message
#                 )
#             return 1

#         else:
#             # No entries updated
#             save_log(
#                 'update_stage_determination_accrued_interest_and_ead',
#                 'INFO',
#                 "No Stage Determination entries were updated."
#             )
#             return 0

#     except Exception as e:
#         save_log(
#             'update_stage_determination_accrued_interest_and_ead',
#             'ERROR',
#             f"Exception during update process for fic_mis_date={fic_mis_date}: {e}"
#         )
#         return 0
