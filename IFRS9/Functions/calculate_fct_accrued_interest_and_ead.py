from django.db.models import Sum, Q
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from ..models import FCT_Stage_Determination, FSI_Expected_Cashflow

def calculate_total_exposure_and_accrued_interest(account_number, fic_mis_date, carrying_amount):
    """
    This function calculates the total accrued interest and the exposure at default (EAD) for a specific account.
    The accrued interest is summed, and EAD is calculated using the n_carrying_amount_ncy from FCT_Stage_Determination.
    """
    try:
        # Step 1: Retrieve all cash flow entries for this account from FSI_Expected_Cashflow
        cash_flows = FSI_Expected_Cashflow.objects.filter(v_account_number=account_number, fic_mis_date=fic_mis_date)
        
        if not cash_flows.exists():
            print(f"No cash flow records found for account {account_number} and fic_mis_date {fic_mis_date}")
            return None, None
        
        # Step 2: Sum accrued interest for the account
        total_accrued_interest = cash_flows.aggregate(Sum('n_accrued_interest'))['n_accrued_interest__sum'] or Decimal(0)

        # Step 3: Calculate EAD as the sum of the carrying amount and accrued interest
        total_exposure_at_default = carrying_amount + total_accrued_interest

        print(f"Account {account_number}: Total accrued interest = {total_accrued_interest}, EAD = {total_exposure_at_default}")

        return total_accrued_interest, total_exposure_at_default

    except Exception as e:
        print(f"Error calculating total accrued interest and EAD for account {account_number}: {e}")
        return None, None

def update_stage_determination_accrued_interest_and_ead(fic_mis_date, max_workers=8, batch_size=1000):
    """
    This function updates the FCT_Stage_Determination table with the total accrued interest and exposure at default (EAD)
    for each account. The accrued interest and EAD are calculated from the FSI_Expected_Cashflow table, and EAD is 
    based on the n_carrying_amount_ncy field from FCT_Stage_Determination.
    Only accounts with NULL or zero n_accrued_interest are processed.
    """
    try:
        # Fetch all entries from FCT_Stage_Determination where n_accrued_interest is NULL or 0
        stage_determination_entries = FCT_Stage_Determination.objects.filter(
            fic_mis_date=fic_mis_date
        ).filter(Q(n_accrued_interest__isnull=True) | Q(n_accrued_interest=0)).exclude(n_prod_code__isnull=True)

        if stage_determination_entries.count() == 0:
            print(f"No records found in FCT_Stage_Determination for fic_mis_date {fic_mis_date} with NULL or zero n_accrued_interest.")
            return
        
        # Use ThreadPoolExecutor to process updates in parallel and accumulate bulk updates
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            updated_entries = []
            
            for entry in stage_determination_entries:
                futures.append(executor.submit(process_accrued_interest_and_ead_for_account, entry, updated_entries))
            
            # Wait for all threads to complete
            for future in futures:
                future.result()

            # Perform bulk update
            bulk_update_stage_determination(updated_entries)

        print(f"Successfully updated {stage_determination_entries.count()} records with accrued interest and EAD.")

    except Exception as e:
        print(f"Error during update process: {e}")

def process_accrued_interest_and_ead_for_account(entry, updated_entries):
    """
    Calculate the accrued interest and exposure at default (EAD) for a single entry in FCT_Stage_Determination.
    Add the entry to the updated_entries list if calculations are successful for bulk update.
    """
    try:
        # Calculate total accrued interest and EAD
        total_accrued_interest, total_exposure_at_default = calculate_total_exposure_and_accrued_interest(
            entry.n_account_number, entry.fic_mis_date, entry.n_carrying_amount_ncy
        )

        # Append entry to bulk update list if calculations are successful
        if total_accrued_interest is not None and total_exposure_at_default is not None:
            entry.n_accrued_interest = total_accrued_interest
            entry.n_exposure_at_default = total_exposure_at_default
            updated_entries.append(entry)
            print(f"Prepared update for account {entry.n_account_number}.")

    except Exception as e:
        print(f"Error processing accrued interest and EAD for account {entry.n_account_number}: {e}")

def bulk_update_stage_determination(updated_entries, batch_size=1000):
    """
    Perform a bulk update on FCT_Stage_Determination entries for the fields 'n_accrued_interest' and 'n_exposure_at_default'.
    """
    try:
        # Perform the bulk update in batches
        total_entries = len(updated_entries)
        if total_entries == 0:
            print("No entries to update.")
            return

        for i in range(0, total_entries, batch_size):
            batch = updated_entries[i:i + batch_size]
            FCT_Stage_Determination.objects.bulk_update(batch, ['n_accrued_interest', 'n_exposure_at_default'])
            print(f"Updated {len(batch)} records.")

    except Exception as e:
        print(f"Error during bulk update: {e}")

# Example usage
update_stage_determination_accrued_interest_and_ead(fic_mis_date='2024-09-17')
