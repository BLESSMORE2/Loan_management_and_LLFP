from django.db import connection, transaction
from ..models import FCT_Stage_Determination
from .save_log import save_log


def update_stage_determination_accrued_interest_and_ead(fic_mis_date):
    """
    SQL-based implementation to update n_accrued_interest and n_exposure_at_default fields in FCT_Stage_Determination.

    1) Precompute accrued interest for each account in one SQL aggregation query.
    2) Use SQL joins to calculate and update EAD in a single query.

    :param fic_mis_date: MIS date to filter records.
    :return: 1 if updates occur, else 0.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Step 1: Precompute accrued interest
            cursor.execute("""
                UPDATE fct_stage_determination sd
                SET n_accrued_interest = (
                    SELECT SUM(ec.n_accrued_interest)
                    FROM fsi_expected_cashflow ec
                    WHERE ec.fic_mis_date = %s
                      AND ec.v_account_number = sd.n_account_number
                )
                WHERE sd.fic_mis_date = %s
                  AND sd.n_accrued_interest IS NULL
                  AND sd.n_prod_code IS NOT NULL;
            """, [fic_mis_date, fic_mis_date])

            # Step 2: Calculate and update EAD
            cursor.execute("""
                UPDATE fct_stage_determination sd
                SET n_exposure_at_default = (
                    COALESCE(sd.n_carrying_amount_ncy, 0) + COALESCE(sd.n_accrued_interest, 0)
                )
                WHERE sd.fic_mis_date = %s
                  AND sd.n_exposure_at_default IS NULL
                  AND sd.n_prod_code IS NOT NULL;
            """, [fic_mis_date])

        # Log success
        save_log(
            'update_stage_determination_accrued_interest_and_ead',
            'INFO',
            f"Successfully updated accrued interest and EAD for FCT_Stage_Determination with fic_mis_date={fic_mis_date}."
        )
        return 1  # Success

    except Exception as e:
        # Log any error
        save_log(
            'update_stage_determination_accrued_interest_and_ead',
            'ERROR',
            f"Exception during update process for fic_mis_date={fic_mis_date}: {e}"
        )
        return 0  # Failure


# from django.db import transaction
# from django.db.models import Sum
# from decimal import Decimal
# from concurrent.futures import ThreadPoolExecutor, as_completed

# from ..models import FCT_Stage_Determination, FSI_Expected_Cashflow
# from .save_log import save_log


# def precompute_accrued_interest(fic_mis_date):
#     """
#     Precompute the total accrued interest per account from FSI_Expected_Cashflow in a single query.
#     Returns a dictionary: {account_number: accrued_interest_sum}
#     """
#     try:
#         # Aggregate accrued interest by account
#         accrued_qs = (
#             FSI_Expected_Cashflow.objects
#             .filter(fic_mis_date=fic_mis_date)
#             .values('v_account_number')
#             .annotate(total_accrued=Sum('n_accrued_interest'))
#         )

#         # Build a dict for O(1) lookups
#         return {
#             row['v_account_number']: row['total_accrued'] or Decimal(0)
#             for row in accrued_qs
#         }
#     except Exception as e:
#         save_log('precompute_accrued_interest', 'ERROR', f"Error precomputing accrued interest: {e}")
#         return {}


# def calculate_exposure_at_default(carrying_amount, accrued_interest):
#     """
#     Calculate exposure at default (EAD) by summing carrying amount and accrued interest.
#     """
#     try:
#         return carrying_amount + accrued_interest
#     except Exception as e:
#         save_log('calculate_exposure_at_default', 'ERROR', f"Error calculating EAD: {e}")
#         return None


# def process_stage_batch(entries_batch, accrued_interest_dict):
#     """
#     Process a batch of FCT_Stage_Determination entries, calculating accrued interest (if missing)
#     and exposure at default (EAD). Returns a list of updated entries.
#     """
#     updated_entries_local = []
#     for entry in entries_batch:
#         try:
#             # If n_accrued_interest is missing, pull from the precomputed dictionary
#             accrued_interest = (
#                 entry.n_accrued_interest  
#                 if entry.n_accrued_interest is not None
#                 else accrued_interest_dict.get(entry.n_account_number, Decimal(0))
#             )

#             carrying_amount = entry.n_carrying_amount_ncy or Decimal(0)
#             total_exposure = calculate_exposure_at_default(carrying_amount, accrued_interest)

#             if total_exposure is not None:
#                 entry.n_accrued_interest = accrued_interest
#                 entry.n_exposure_at_default = total_exposure
#                 updated_entries_local.append(entry)
#         except Exception as e:
#             save_log(
#                 'process_stage_batch',
#                 'ERROR',
#                 f"Error processing account {entry.n_account_number}: {e}"
#             )
#     return updated_entries_local


# def update_stage_determination_accrued_interest_and_ead(
#     fic_mis_date,
#     read_chunk_size=2000,
#     max_workers=8,
#     update_batch_size=5000
# ):
#     """
#     Update FCT_Stage_Determination with accrued interest and EAD for each account.
#     1) Precompute accrued interest from FSI_Expected_Cashflow in a single aggregation query.
#     2) Fetch Stage Determination entries that need EAD updates.
#     3) Process them in parallel batches, updating n_accrued_interest and n_exposure_at_default.
#     4) Bulk update in sub-batches.

#     :param fic_mis_date: MIS date to filter records.
#     :param read_chunk_size: Number of records read per chunk in Stage Determination.
#     :param max_workers: Number of parallel threads to use.
#     :param update_batch_size: Number of records to update in each bulk update sub-batch.
#     :return: 1 if any updates occur, else 0.
#     """
#     try:
#         # 1) Precompute all accrued interest in one shot
#         accrued_interest_dict = precompute_accrued_interest(fic_mis_date)

#         # 2) Fetch Stage Determination entries that need EAD
#         stage_qs = (
#             FCT_Stage_Determination.objects
#             .filter(
#                 fic_mis_date=fic_mis_date,
#                 n_exposure_at_default__isnull=True
#             )
#             .exclude(n_prod_code__isnull=True)
#             .only('n_account_number', 'n_accrued_interest', 'n_carrying_amount_ncy', 'n_exposure_at_default')
#         )

#         if not stage_qs.exists():
#             save_log(
#                 'update_stage_determination_accrued_interest_and_ead',
#                 'INFO',
#                 f"No records found with NULL EAD for fic_mis_date={fic_mis_date}."
#             )
#             return 0

#         total_count = stage_qs.count()
#         save_log(
#             'update_stage_determination_accrued_interest_and_ead',
#             'INFO',
#             f"Processing {total_count} records for fic_mis_date={fic_mis_date}..."
#         )

#         updated_entries = []
#         error_logs = {}

#         # 3) Chunked parallel processing
#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = []
#             batch = []

#             # Read Stage Determination entries in chunks from DB
#             for entry in stage_qs.iterator(chunk_size=read_chunk_size):
#                 batch.append(entry)
#                 if len(batch) >= read_chunk_size:
#                     futures.append(executor.submit(process_stage_batch, batch, accrued_interest_dict))
#                     batch = []

#             # Process leftover
#             if batch:
#                 futures.append(executor.submit(process_stage_batch, batch, accrued_interest_dict))

#             # Collect results
#             for future in as_completed(futures):
#                 try:
#                     result_batch = future.result()
#                     updated_entries.extend(result_batch)
#                 except Exception as exc:
#                     error_msg = f"Thread error: {exc}"
#                     error_logs[error_msg] = error_logs.get(error_msg, 0) + 1

#         # 4) Bulk update in sub-batches
#         total_updated = len(updated_entries)
#         if total_updated == 0:
#             save_log(
#                 'update_stage_determination_accrued_interest_and_ead',
#                 'INFO',
#                 "No Stage Determination entries were updated."
#             )
#             return 0

#         with transaction.atomic():
#             for i in range(0, total_updated, update_batch_size):
#                 FCT_Stage_Determination.objects.bulk_update(
#                     updated_entries[i : i + update_batch_size],
#                     ['n_accrued_interest', 'n_exposure_at_default']
#                 )

#         save_log(
#             'update_stage_determination_accrued_interest_and_ead',
#             'INFO',
#             f"Successfully updated {total_updated} records with accrued interest and EAD."
#         )

#         # Log any thread errors
#         for err_msg, count in error_logs.items():
#             save_log(
#                 'update_stage_determination_accrued_interest_and_ead',
#                 'ERROR',
#                 f"{err_msg} (Occurred {count} times)"
#             )

#         return 1

#     except Exception as e:
#         save_log(
#             'update_stage_determination_accrued_interest_and_ead',
#             'ERROR',
#             f"Exception during update process for fic_mis_date={fic_mis_date}: {e}"
#         )
#         return 0
