from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from decimal import Decimal
from ..models import FCT_Stage_Determination, CollateralLGD, Ldn_LGD_Term_Structure
from .save_log import save_log

def update_lgd_for_stage_determination_term_structure(mis_date):
    """
    Update `n_lgd_percent` in `FCT_Stage_Determination` based on LGD term structure.
    """
    try:
        # Cache term structure data for fast lookup
        term_structure_cache = {ts.v_lgd_term_structure_id: ts.n_lgd_percent for ts in Ldn_LGD_Term_Structure.objects.all()}

        # Get entries with NULL `n_lgd_percent` for the given MIS date
        stage_determination_entries = FCT_Stage_Determination.objects.filter(
            fic_mis_date=mis_date,
            n_lgd_percent__isnull=True
        )

        if not stage_determination_entries.exists():
            save_log('update_lgd_for_stage_determination_term_structure', 'INFO', f"No entries found for fic_mis_date {mis_date} with NULL LGD percent.")
            return 0

        entries_to_update = []
        no_update_reasons = {}  # Store unique reasons for entries not updated
        error_logs = {}  # Store unique errors

        # Process entries in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(update_lgd_based_on_term_structure, entry, entries_to_update, term_structure_cache, no_update_reasons)
                for entry in stage_determination_entries
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    error_message = f"Thread error: {e}"
                    error_logs[error_message] = error_logs.get(error_message, 0) + 1  # Store unique error

        # Perform batch updates in batches of 5000
        if entries_to_update:
            bulk_update_entries_in_batches(entries_to_update, batch_size=5000)
            save_log('update_lgd_for_stage_determination_term_structure', 'INFO', f"Successfully updated LGD for {len(entries_to_update)} entries based on term structure.")
        else:
            # Log detailed reasons if no updates were made
            if no_update_reasons:
                for reason, count in no_update_reasons.items():
                    save_log('update_lgd_for_stage_determination_term_structure', 'INFO', f"{reason} occurred for {count} entries.")
            if error_logs:
                for error_message, count in error_logs.items():
                    save_log('update_lgd_for_stage_determination_term_structure', 'ERROR', f"{error_message} occurred {count} times.")

        return 1 if entries_to_update else 0

    except Exception as e:
        save_log('update_lgd_for_stage_determination_term_structure', 'ERROR', f"Error during LGD update based on term structure: {e}")
        return 0


def update_lgd_based_on_term_structure(entry, entries_to_update, term_structure_cache, no_update_reasons):
    """
    Update LGD based on the LGD term structure and track reasons for no updates.
    """
    try:
        lgd_percent = term_structure_cache.get(entry.n_segment_skey)
        if lgd_percent is not None:
            entry.n_lgd_percent = lgd_percent
            entries_to_update.append(entry)
        else:
            reason = f"No matching term structure found for segment key {entry.n_segment_skey}"
            no_update_reasons[reason] = no_update_reasons.get(reason, 0) + 1
    except Exception as e:
        reason = f"Error updating term-structure-based LGD for account {entry.n_account_number}: {e}"
        no_update_reasons[reason] = no_update_reasons.get(reason, 0) + 1


def update_lgd_for_stage_determination_collateral(mis_date):
    """
    Update `n_lgd_percent` in `FCT_Stage_Determination` based on collateral values and exposure at default.
    """
    try:
        collateral_lgd = CollateralLGD.objects.filter(can_calculate_lgd=True).first()
        if not collateral_lgd:
            save_log('update_lgd_for_stage_determination_collateral', 'INFO', "Collateral-based LGD calculation is not enabled.")
            return 0

        stage_determination_entries = FCT_Stage_Determination.objects.filter(
            fic_mis_date=mis_date,
            n_collateral_amount__isnull=False
        )

        if not stage_determination_entries.exists():
            save_log('update_lgd_for_stage_determination_collateral', 'INFO', f"No entries found for fic_mis_date {mis_date} with NULL LGD percent.")
            return 0

        entries_to_update = []
        no_update_reasons = {}
        error_logs = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(update_lgd_based_on_collateral, entry, entries_to_update, no_update_reasons)
                for entry in stage_determination_entries
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    error_message = f"Thread error: {e}"
                    error_logs[error_message] = error_logs.get(error_message, 0) + 1

        if entries_to_update:
            bulk_update_entries_in_batches(entries_to_update, batch_size=5000)
            save_log('update_lgd_for_stage_determination_collateral', 'INFO', f"Successfully updated LGD for {len(entries_to_update)} entries based on collateral.")
        else:
            if no_update_reasons:
                for reason, count in no_update_reasons.items():
                    save_log('update_lgd_for_stage_determination_collateral', 'INFO', f"{reason} occurred for {count} entries.")
            if error_logs:
                for error_message, count in error_logs.items():
                    save_log('update_lgd_for_stage_determination_collateral', 'ERROR', f"{error_message} occurred {count} times.")

        return 1 if entries_to_update else 0

    except Exception as e:
        save_log('update_lgd_for_stage_determination_collateral', 'ERROR', f"Error during LGD update based on collateral: {e}")
        return 0


def update_lgd_based_on_collateral(entry, entries_to_update, no_update_reasons):
    """
    Update LGD based on collateral values and exposure at default, with reasons tracking.
    """
    try:
        if entry.n_exposure_at_default > 0 and entry.n_collateral_amount > 0:
            lgd = 1 - (entry.n_collateral_amount / entry.n_exposure_at_default)
            lgd = max(Decimal(0), min(Decimal(1), lgd))  # Clamp LGD between 0 and 1
            entry.n_lgd_percent = lgd
            entries_to_update.append(entry)
        else:
            reason = f"Insufficient exposure or collateral for account {entry.n_account_number}"
            no_update_reasons[reason] = no_update_reasons.get(reason, 0) + 1
    except Exception as e:
        reason = f"Error updating collateral-based LGD for account {entry.n_account_number}: {e}"
        no_update_reasons[reason] = no_update_reasons.get(reason, 0) + 1


def bulk_update_entries_in_batches(entries_to_update, batch_size=5000):
    """
    Perform a bulk update of the `n_lgd_percent` field for all entries in batches of 5000.
    """
    try:
        with transaction.atomic():
            for i in range(0, len(entries_to_update), batch_size):
                FCT_Stage_Determination.objects.bulk_update(
                    entries_to_update[i:i + batch_size], ['n_lgd_percent']
                )
    except Exception as e:
        print(f"Error during bulk update: {e}")




# from concurrent.futures import ThreadPoolExecutor, as_completed
# from decimal import Decimal
# from ..models import FCT_Stage_Determination, CollateralLGD, Ldn_LGD_Term_Structure
# from .save_log import save_log

# def update_lgd_for_stage_determination(mis_date):
#     """
#     Update n_lgd_percent in FCT_Stage_Determination based on:
#     1. Collateral values and EAD.
#     2. LGD term structure if n_segment_skey matches v_lgd_term_structure_id.
#     """
#     try:
#         # Fetch entries for the given mis_date
#         stage_determination_entries = FCT_Stage_Determination.objects.filter(
#         fic_mis_date=mis_date,
#         n_lgd_percent__isnull=True  # Only include entries where n_lgd_percent is NULL
#         )

#         # List to hold the updated entries for bulk update
#         entries_to_update = []
#         error_occurred = False  # Flag to track errors

#         # Process entries in parallel with ThreadPoolExecutor
#         with ThreadPoolExecutor(max_workers=4) as executor:
#             futures = [
#                 executor.submit(process_lgd_updates, entry, entries_to_update)
#                 for entry in stage_determination_entries
#             ]

#             for future in as_completed(futures):
#                 try:
#                     future.result()
#                 except Exception as e:
#                     save_log('update_lgd_for_stage_determination', 'ERROR', f"Thread error: {e}")
#                     error_occurred = True  # Set the flag if an error occurs

#         # Perform bulk update after all entries have been processed
#         if entries_to_update:
#             bulk_update_entries(entries_to_update)

#         # Log the total number of entries updated only once
#         if not error_occurred:
#             save_log('update_lgd_for_stage_determination', 'INFO', f"Successfully updated LGD for {len(entries_to_update)} entries.")
#         return 1 if not error_occurred else 0  # Return 1 on success, 0 if any thread encountered an error

#     except Exception as e:
#         save_log('update_lgd_for_stage_determination', 'ERROR', f"Error during LGD update: {e}")
#         return 0  # Return 0 in case of any exception


# def process_lgd_updates(entry, entries_to_update):
#     """
#     Process LGD updates for both collateral-based and term-structure-based LGD calculations.
#     Append the updated entries to the `entries_to_update` list for bulk update later.
#     """
#     try:
#         update_lgd_based_on_term_structure(entry, entries_to_update)
#         update_lgd_based_on_collateral(entry, entries_to_update)
#     except Exception as e:
#         print(f"Error processing LGD updates for account {entry.n_account_number}: {e}")


# def update_lgd_based_on_collateral(entry, entries_to_update):
#     """
#     Update LGD based on collateral values and exposure at default.
#     """
#     try:
#         collateral_lgd = CollateralLGD.objects.filter(can_calculate_lgd=True).first()
#         if collateral_lgd and entry.n_exposure_at_default > 0 and entry.n_collateral_amount > 0:
#             lgd = 1 - (entry.n_collateral_amount / entry.n_exposure_at_default)
#             lgd = max(Decimal(0), min(Decimal(1), lgd))  # Clamp LGD between 0 and 1
#             entry.n_lgd_percent = lgd
#             entries_to_update.append(entry)

#     except Exception as e:
#         print(f"Error updating collateral-based LGD for account {entry.n_account_number}: {e}")


# def update_lgd_based_on_term_structure(entry, entries_to_update):
#     """
#     Update LGD based on the LGD term structure.
#     """
#     try:
#         term_structure = Ldn_LGD_Term_Structure.objects.get(v_lgd_term_structure_id=entry.n_segment_skey)
#         entry.n_lgd_percent = term_structure.n_lgd_percent
#         entries_to_update.append(entry)
#     except Ldn_LGD_Term_Structure.DoesNotExist:
#         print(f"No matching term structure found for segment key {entry.n_segment_skey}")
#     except Exception as e:
#         print(f"Error updating term-structure-based LGD for account {entry.n_account_number}: {e}")


# def bulk_update_entries(entries_to_update):
#     """
#     Perform a bulk update of the n_lgd_percent field for all entries in the list.
#     """
#     try:
#         if entries_to_update:
#             FCT_Stage_Determination.objects.bulk_update(entries_to_update, ['n_lgd_percent'])
#     except Exception as e:
#         print(f"Error during bulk update: {e}")
