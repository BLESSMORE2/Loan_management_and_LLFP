from django.db import connection, transaction
from ..models import FCT_Stage_Determination
from .save_log import save_log

def update_stage_determination_EAD_w_ACCR(fic_mis_date):
    """
    Set-based SQL approach to update the n_exposure_at_default field in FCT_Stage_Determination
    by adding n_accrued_interest to n_carrying_amount_ncy.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Perform the set-based update
            cursor.execute("""
                UPDATE fct_stage_determination
                SET n_exposure_at_default = n_carrying_amount_ncy + n_accrued_interest
                WHERE fic_mis_date = %s
                  AND n_exposure_at_default IS NULL
                  AND n_carrying_amount_ncy IS NOT NULL
                  AND n_accrued_interest IS NOT NULL;
            """, [fic_mis_date])

        # Log success
        save_log(
            'update_stage_determination_EAD',
            'INFO',
            f"Successfully updated n_exposure_at_default for fic_mis_date={fic_mis_date}."
        )
        return 1  # Success

    except Exception as e:
        # Log any error
        save_log(
            'update_stage_determination_EAD',
            'ERROR',
            f"Exception during EAD update for fic_mis_date={fic_mis_date}: {e}"
        )
        return 0  # Failure



# from django.db import transaction
# from decimal import Decimal
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from ..models import FCT_Stage_Determination
# from .save_log import save_log


# def calculate_exposure_at_default(entry):
#     """
#     Calculate EAD for a single entry by summing carrying amount and accrued interest.
#     """
#     try:
#         # Ensure both fields are non-null (already filtered, but just in case)
#         carrying_amount = entry.n_carrying_amount_ncy or Decimal(0)
#         accrued_interest = entry.n_accrued_interest or Decimal(0)

#         # Calculate EAD
#         ead = carrying_amount + accrued_interest
#         entry.n_exposure_at_default = ead
#         return entry

#     except Exception as e:
#         save_log('calculate_exposure_at_default', 'ERROR',
#                  f"Error calculating EAD for account {entry.n_account_number}: {e}")
#         return None


# def process_batch(entries_batch):
#     """
#     Process a batch of FCT_Stage_Determination entries to update their EAD.
#     Returns a list of updated entries.
#     """
#     updated_entries_local = []
#     for entry in entries_batch:
#         updated_entry = calculate_exposure_at_default(entry)
#         if updated_entry:
#             updated_entries_local.append(updated_entry)
#     return updated_entries_local


# def update_stage_determination_EAD_w_ACCR(
#     fic_mis_date,
#     read_chunk_size=2000,
#     max_workers=8,
#     update_batch_size=5000
# ):
#     """
#     Update the n_exposure_at_default field in FCT_Stage_Determination by adding 
#     n_accrued_interest to n_carrying_amount_ncy. Uses multi-threading and bulk updates 
#     for maximum efficiency.

#     :param fic_mis_date: The MIS date for filtering.
#     :param read_chunk_size: Size of DB read chunks (iterator).
#     :param max_workers: Number of parallel threads to use.
#     :param update_batch_size: Size of each bulk update sub-batch.
#     :return: 1 if updates occurred, else 0.
#     """
#     try:
#         # Filter only needed records & fields
#         stage_entries = (
#             FCT_Stage_Determination.objects
#             .filter(
#                 fic_mis_date=fic_mis_date,
#                 n_exposure_at_default__isnull=True
#             )
#             .exclude(n_carrying_amount_ncy__isnull=True)
#             .exclude(n_accrued_interest__isnull=True)
#             .only(
#                 'n_account_number',
#                 'n_carrying_amount_ncy',
#                 'n_accrued_interest',
#                 'n_exposure_at_default'
#             )
#         )

#         # If no records, log and exit
#         if not stage_entries.exists():
#             save_log(
#                 'update_stage_determination_EAD',
#                 'INFO',
#                 f"No records found (NULL EAD) for fic_mis_date={fic_mis_date}."
#             )
#             return 0

#         total_count = stage_entries.count()
#         save_log(
#             'update_stage_determination_EAD',
#             'INFO',
#             f"Processing {total_count} records for fic_mis_date={fic_mis_date}..."
#         )

#         # Parallel processing
#         updated_entries = []
#         error_logs = {}

#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = []
#             batch = []

#             # Read DB in chunks
#             for entry in stage_entries.iterator(chunk_size=read_chunk_size):
#                 batch.append(entry)
#                 if len(batch) >= read_chunk_size:
#                     futures.append(executor.submit(process_batch, batch))
#                     batch = []

#             # Handle leftover
#             if batch:
#                 futures.append(executor.submit(process_batch, batch))

#             # Collect results
#             for future in as_completed(futures):
#                 try:
#                     result_batch = future.result()
#                     updated_entries.extend(result_batch)
#                 except Exception as exc:
#                     error_msg = f"Thread error: {exc}"
#                     error_logs[error_msg] = error_logs.get(error_msg, 0) + 1

#         # Bulk update results
#         total_updated = len(updated_entries)
#         if total_updated == 0:
#             save_log(
#                 'update_stage_determination_EAD',
#                 'INFO',
#                 "No Stage Determination entries were updated."
#             )
#             return 0

#         with transaction.atomic():
#             for start in range(0, total_updated, update_batch_size):
#                 end = start + update_batch_size
#                 FCT_Stage_Determination.objects.bulk_update(
#                     updated_entries[start:end],
#                     ['n_exposure_at_default']
#                 )

#         save_log(
#             'update_stage_determination_EAD',
#             'INFO',
#             f"Successfully updated {total_updated} records with EAD."
#         )

#         # Log any thread errors
#         for error_message, count in error_logs.items():
#             save_log(
#                 'update_stage_determination_EAD',
#                 'ERROR',
#                 f"{error_message} (occurred {count} times)"
#             )

#         return 1

#     except Exception as e:
#         save_log(
#             'update_stage_determination_EAD',
#             'ERROR',
#             f"Exception during EAD update for fic_mis_date={fic_mis_date}: {e}"
#         )
#         return 0
