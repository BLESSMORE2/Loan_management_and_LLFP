from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from ..models import FCT_Stage_Determination, CollateralLGD, Ldn_LGD_Term_Structure
from .save_log import save_log

def update_lgd_for_stage_determination(mis_date):
    """
    Update n_lgd_percent in FCT_Stage_Determination based on:
    1. Collateral values and EAD.
    2. LGD term structure if n_segment_skey matches v_lgd_term_structure_id.
    """
    try:
        # Fetch entries for the given mis_date
        stage_determination_entries = FCT_Stage_Determination.objects.filter(
        fic_mis_date=mis_date,
        n_lgd_percent__isnull=True  # Only include entries where n_lgd_percent is NULL
        )

        # List to hold the updated entries for bulk update
        entries_to_update = []
        error_occurred = False  # Flag to track errors

        # Process entries in parallel with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_lgd_updates, entry, entries_to_update)
                for entry in stage_determination_entries
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    save_log('update_lgd_for_stage_determination', 'ERROR', f"Thread error: {e}")
                    error_occurred = True  # Set the flag if an error occurs

        # Perform bulk update after all entries have been processed
        if entries_to_update:
            bulk_update_entries(entries_to_update)

        # Log the total number of entries updated only once
        if not error_occurred:
            save_log('update_lgd_for_stage_determination', 'INFO', f"Successfully updated LGD for {len(entries_to_update)} entries.")
        return 1 if not error_occurred else 0  # Return 1 on success, 0 if any thread encountered an error

    except Exception as e:
        save_log('update_lgd_for_stage_determination', 'ERROR', f"Error during LGD update: {e}")
        return 0  # Return 0 in case of any exception


def process_lgd_updates(entry, entries_to_update):
    """
    Process LGD updates for both collateral-based and term-structure-based LGD calculations.
    Append the updated entries to the `entries_to_update` list for bulk update later.
    """
    try:
        update_lgd_based_on_term_structure(entry, entries_to_update)
        update_lgd_based_on_collateral(entry, entries_to_update)
    except Exception as e:
        print(f"Error processing LGD updates for account {entry.n_account_number}: {e}")


def update_lgd_based_on_collateral(entry, entries_to_update):
    """
    Update LGD based on collateral values and exposure at default.
    """
    try:
        collateral_lgd = CollateralLGD.objects.filter(can_calculate_lgd=True).first()
        if collateral_lgd and entry.n_exposure_at_default > 0 and entry.n_collateral_amount > 0:
            lgd = 1 - (entry.n_collateral_amount / entry.n_exposure_at_default)
            lgd = max(Decimal(0), min(Decimal(1), lgd))  # Clamp LGD between 0 and 1
            entry.n_lgd_percent = lgd
            entries_to_update.append(entry)

    except Exception as e:
        print(f"Error updating collateral-based LGD for account {entry.n_account_number}: {e}")


def update_lgd_based_on_term_structure(entry, entries_to_update):
    """
    Update LGD based on the LGD term structure.
    """
    try:
        term_structure = Ldn_LGD_Term_Structure.objects.get(v_lgd_term_structure_id=entry.n_segment_skey)
        entry.n_lgd_percent = term_structure.n_lgd_percent
        entries_to_update.append(entry)
    except Ldn_LGD_Term_Structure.DoesNotExist:
        print(f"No matching term structure found for segment key {entry.n_segment_skey}")
    except Exception as e:
        print(f"Error updating term-structure-based LGD for account {entry.n_account_number}: {e}")


def bulk_update_entries(entries_to_update):
    """
    Perform a bulk update of the n_lgd_percent field for all entries in the list.
    """
    try:
        if entries_to_update:
            FCT_Stage_Determination.objects.bulk_update(entries_to_update, ['n_lgd_percent'])
    except Exception as e:
        print(f"Error during bulk update: {e}")
