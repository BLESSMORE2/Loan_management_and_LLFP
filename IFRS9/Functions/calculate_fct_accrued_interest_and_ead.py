from django.db.models import Sum, Q
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from ..models import FCT_Stage_Determination, FSI_Expected_Cashflow

def calculate_accrued_interest(account_number, fic_mis_date):
    """
    This function calculates the total accrued interest for a specific account.
    The accrued interest is summed from the FSI_Expected_Cashflow table.
    """
    try:
        # Step 1: Retrieve all cash flow entries for this account from FSI_Expected_Cashflow
        cash_flows = FSI_Expected_Cashflow.objects.filter(v_account_number=account_number, fic_mis_date=fic_mis_date)
        
        if not cash_flows.exists():
            print(f"No cash flow records found for account {account_number} and fic_mis_date {fic_mis_date}")
            return Decimal(0)
        
        # Step 2: Sum accrued interest for the account
        total_accrued_interest = cash_flows.aggregate(Sum('n_accrued_interest'))['n_accrued_interest__sum'] or Decimal(0)

        print(f"Account {account_number}: Total accrued interest = {total_accrued_interest}")
        return total_accrued_interest

    except Exception as e:
        print(f"Error calculating accrued interest for account {account_number}: {e}")
        return Decimal(0)


def calculate_exposure_at_default(carrying_amount, accrued_interest):
    """
    This function calculates the exposure at default (EAD) by summing the carrying amount and accrued interest.
    """
    try:
        # Step 3: Calculate EAD as the sum of the carrying amount and accrued interest
        total_exposure_at_default = carrying_amount + accrued_interest
        return total_exposure_at_default

    except Exception as e:
        print(f"Error calculating EAD: {e}")
        return None


def update_stage_determination_accrued_interest_and_ead(fic_mis_date, max_workers=8, batch_size=1000):
    """
    This function updates the FCT_Stage_Determination table with the total accrued interest and exposure at default (EAD)
    for each account. The accrued interest and EAD are calculated from the FSI_Expected_Cashflow table, and EAD is 
    based on the n_carrying_amount_ncy field from FCT_Stage_Determination.
    """
    try:
        # Fetch all entries from FCT_Stage_Determination where n_exposure_at_default is NULL
        stage_determination_entries = FCT_Stage_Determination.objects.filter(
            fic_mis_date=fic_mis_date
        ).filter(Q(n_exposure_at_default__isnull=True)).exclude(n_prod_code__isnull=True)

        if stage_determination_entries.count() == 0:
            print(f"No records found in FCT_Stage_Determination for fic_mis_date {fic_mis_date} with NULL exposure at default.")
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

        print(f"Successfully updated {len(updated_entries)} records with accrued interest and EAD.")

    except Exception as e:
        print(f"Error during update process: {e}")


def process_accrued_interest_and_ead_for_account(entry, updated_entries):
    """
    Calculate the accrued interest and exposure at default (EAD) for a single entry in FCT_Stage_Determination.
    Add the entry to the updated_entries list if calculations are successful for bulk update.
    """
    try:
        # Step 1: If n_accrued_interest is null, calculate accrued interest
        total_accrued_interest = entry.n_accrued_interest or calculate_accrued_interest(entry.n_account_number, entry.fic_mis_date)

        # Step 2: Calculate EAD using the existing carrying amount and the accrued interest
        total_exposure_at_default = calculate_exposure_at_default(entry.n_carrying_amount_ncy, total_accrued_interest)

        # Append entry to bulk update list if calculations are successful
        if total_exposure_at_default is not None:
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
