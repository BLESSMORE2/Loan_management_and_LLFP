from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from ..models import *
from decimal import Decimal
from ..Functions import save_log

def update_lgd_for_stage_determination(mis_date):
    """
    Update n_lgd_percent in FCT_Stage_Determination based on two approaches:
    1. Using collateral values and exposure at default (EAD).
    2. Using the LGD value from the term structure (Ldn_LGD_Term_Structure) if n_segment_skey matches v_lgd_term_structure_id.
    
    Multithreading is used to process entries in parallel, and a bulk update is used to improve performance.
    
    :param mis_date: The mis_date (fic_mis_date) for which the update will be processed.
    """
    try:
        # Fetch all entries for the given mis_date where exposure and collateral are available
        stage_determination_entries = FCT_Stage_Determination.objects.filter(
            fic_mis_date=mis_date
        ).exclude(n_exposure_at_default__isnull=True).exclude(n_collateral_amount__isnull=True)

        if not stage_determination_entries.exists():
            print(f"No records found for mis_date {mis_date} with exposure and collateral.")
            return 0  # Return 0 if no records are found

        # List to hold the updated entries for bulk update
        entries_to_update = []

        # Use multithreading to process entries in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_lgd_updates, entry, entries_to_update)
                for entry in stage_determination_entries
            ]

            # Wait for all threads to complete
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Thread encountered an error: {e}")
                    return 0  # Return 0 if any thread encounters an error

        # Perform bulk update after all entries have been processed
        if entries_to_update:
            bulk_update_entries(entries_to_update)

        print(f"Successfully updated LGD for {len(entries_to_update)} entries.")
        return 1  # Return 1 on successful completion

    except Exception as e:
        print(f"Error during LGD update: {e}")
        return 0  # Return 0 in case of any exception



def process_lgd_updates(entry, entries_to_update):
    """
    Process LGD updates for both collateral-based and term-structure-based LGD calculations.
    Append the updated entries to the `entries_to_update` list for bulk update later.
    """
    # First approach: Update LGD based on term structure if n_segment_skey matches v_lgd_term_structure_id
    update_lgd_based_on_term_structure(entry, entries_to_update)
    # Second approach: Calculate LGD based on collateral and exposure if allowed
    update_lgd_based_on_collateral(entry, entries_to_update)

    

def update_lgd_based_on_collateral(entry, entries_to_update):
    """
    Update LGD in FCT_Stage_Determination based on collateral values and exposure at default.
    Only updates if can_calculate_lgd is True in CollateralLGD.
    """
    try:
        # Check if LGD calculation is allowed for this customer (v_cust_ref_code) in CollateralLGD table
        collateral_lgd = CollateralLGD.objects.get(can_calculate_lgd=True)

        # Ensure that both exposure and collateral amount are non-zero to avoid division errors
        if entry.n_exposure_at_default > 0 and entry.n_collateral_amount > 0:
            # Calculate LGD = 1 - (Collateral Value / Exposure at Default)
            lgd = 1 - (entry.n_collateral_amount / entry.n_exposure_at_default)

            # LGD should not exceed 1 or fall below 0 (as a safeguard)
            lgd = max(Decimal(0), min(Decimal(1), lgd))

            # Update n_lgd_percent with the calculated LGD
            entry.n_lgd_percent = lgd

            # Append the updated entry to the list for bulk update
            entries_to_update.append(entry)

            print(f"Updated collateral-based LGD for account {entry.n_account_number}: LGD={lgd}")
        else:
            print(f"Skipping account {entry.n_account_number} due to zero exposure or collateral.")

    except CollateralLGD.DoesNotExist:
        print(f"LGD calculation not allowed for customer {entry.n_cust_ref_code}")
    except Exception as e:
        print(f"Error updating collateral-based LGD for entry {entry.n_account_number}: {e}")


def update_lgd_based_on_term_structure(entry, entries_to_update):
    """
    Update LGD in FCT_Stage_Determination based on the LGD term structure.
    Updates if n_segment_skey matches v_lgd_term_structure_id in Ldn_LGD_Term_Structure.
    """
    try:
        # Fetch the term structure where v_lgd_term_structure_id matches n_segment_skey
        term_structure = Ldn_LGD_Term_Structure.objects.get(v_lgd_term_structure_id=entry.n_segment_skey)

        # Update n_lgd_percent with the LGD from the term structure
        entry.n_lgd_percent = term_structure.n_lgd_percent

        # Append the updated entry to the list for bulk update
        entries_to_update.append(entry)

        print(f"Updated term-structure-based LGD for account {entry.n_account_number}: LGD={entry.n_lgd_percent}")

    except Ldn_LGD_Term_Structure.DoesNotExist:
        print(f"No matching term structure found for segment key {entry.n_segment_skey}")
    except Exception as e:
        print(f"Error updating term-structure-based LGD for entry {entry.n_account_number}: {e}")


def bulk_update_entries(entries_to_update):
    """
    Perform a bulk update of the n_lgd_percent field for all entries in the list.
    """
    try:
        # Bulk update the n_lgd_percent field in the FCT_Stage_Determination table
        FCT_Stage_Determination.objects.bulk_update(entries_to_update, ['n_lgd_percent'])
        print(f"Bulk updated {len(entries_to_update)} entries with updated LGD.")
    except Exception as e:
        print(f"Error during bulk update: {e}")