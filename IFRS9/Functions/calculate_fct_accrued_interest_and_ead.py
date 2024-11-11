from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import FCT_Stage_Determination, FSI_Expected_Cashflow
from .save_log import save_log

def calculate_accrued_interest(account_number, fic_mis_date):
    """
    Calculate total accrued interest for a specific account by summing values from FSI_Expected_Cashflow.
    """
    try:
        cash_flows = FSI_Expected_Cashflow.objects.filter(v_account_number=account_number, fic_mis_date=fic_mis_date)
        
        if not cash_flows.exists():
            save_log('calculate_accrued_interest', 'INFO', f"No cash flow records found for account {account_number} and fic_mis_date {fic_mis_date}")
            return Decimal(0)
        
        total_accrued_interest = cash_flows.aggregate(Sum('n_accrued_interest'))['n_accrued_interest__sum'] or Decimal(0)
        return total_accrued_interest

    except Exception as e:
        save_log('calculate_accrued_interest', 'ERROR', f"Error calculating accrued interest for account {account_number}: {e}")
        return Decimal(0)

def calculate_exposure_at_default(carrying_amount, accrued_interest):
    """
    Calculate exposure at default (EAD) by summing carrying amount and accrued interest.
    """
    try:
        return carrying_amount + accrued_interest
    except Exception as e:
        save_log('calculate_exposure_at_default', 'ERROR', f"Error calculating EAD: {e}")
        return None

def process_accrued_interest_and_ead_for_account(entry):
    """
    Calculate accrued interest and exposure at default (EAD) for a single entry in FCT_Stage_Determination.
    """
    try:
        total_accrued_interest = entry.n_accrued_interest or calculate_accrued_interest(entry.n_account_number, entry.fic_mis_date)
        total_exposure_at_default = calculate_exposure_at_default(entry.n_carrying_amount_ncy, total_accrued_interest)

        if total_exposure_at_default is not None:
            entry.n_accrued_interest = total_accrued_interest
            entry.n_exposure_at_default = total_exposure_at_default
            return entry  # Return the updated entry for bulk update
    except Exception as e:
        save_log('process_accrued_interest_and_ead_for_account', 'ERROR', f"Error processing account {entry.n_account_number}: {e}")
    return None

def update_stage_determination_accrued_interest_and_ead(fic_mis_date):
    """
    Update FCT_Stage_Determination table with accrued interest and exposure at default (EAD) for each account.
    """
    try:
        stage_determination_entries = FCT_Stage_Determination.objects.filter(
            fic_mis_date=fic_mis_date,
            n_exposure_at_default__isnull=True
        ).exclude(n_prod_code__isnull=True)

        if not stage_determination_entries.exists():
            save_log('update_stage_determination_accrued_interest_and_ead', 'INFO', f"No records found in FCT_Stage_Determination for fic_mis_date {fic_mis_date} with NULL exposure at default.")
            return 0
        
        updated_entries = []
        error_logs = {}  # Dictionary to capture unique errors

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(process_accrued_interest_and_ead_for_account, entry): entry for entry in stage_determination_entries}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        updated_entries.append(result)
                except Exception as e:
                    error_message = f"Error processing entry {futures[future].n_account_number}: {e}"
                    if error_message not in error_logs:
                        error_logs[error_message] = 1

        # Perform bulk update in batches of 5000
        batch_size = 5000
        if updated_entries:
            with transaction.atomic():
                for i in range(0, len(updated_entries), batch_size):
                    FCT_Stage_Determination.objects.bulk_update(
                        updated_entries[i:i + batch_size], ['n_accrued_interest', 'n_exposure_at_default']
                    )
            save_log('update_stage_determination_accrued_interest_and_ead', 'INFO', f"Successfully updated {len(updated_entries)} records with accrued interest and EAD.")
        else:
            save_log('update_stage_determination_accrued_interest_and_ead', 'INFO', "No records were updated.")

        # Log each unique error once
        for error_message in error_logs:
            save_log('update_stage_determination_accrued_interest_and_ead', 'ERROR', error_message)

        return 1

    except Exception as e:
        save_log('update_stage_determination_accrued_interest_and_ead', 'ERROR', f"Error during update process for fic_mis_date {fic_mis_date}: {str(e)}")
        return 0
    
    

# from django.db.models import Sum, Q
# from decimal import Decimal
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from ..models import FCT_Stage_Determination, FSI_Expected_Cashflow
# from .save_log import save_log

# def calculate_accrued_interest(account_number, fic_mis_date):
#     """
#     This function calculates the total accrued interest for a specific account.
#     The accrued interest is summed from the FSI_Expected_Cashflow table.
#     """
#     try:
#         cash_flows = FSI_Expected_Cashflow.objects.filter(v_account_number=account_number, fic_mis_date=fic_mis_date)
        
#         if not cash_flows.exists():
#             save_log('calculate_accrued_interest', 'INFO', f"No cash flow records found for account {account_number} and fic_mis_date {fic_mis_date}")
#             return Decimal(0)
        
#         total_accrued_interest = cash_flows.aggregate(Sum('n_accrued_interest'))['n_accrued_interest__sum'] or Decimal(0)
#         return total_accrued_interest

#     except Exception as e:
#         save_log('calculate_accrued_interest', 'ERROR', f"Error calculating accrued interest for account {account_number}: {e}")
#         return Decimal(0)

# def calculate_exposure_at_default(carrying_amount, accrued_interest):
#     """
#     This function calculates the exposure at default (EAD) by summing the carrying amount and accrued interest.
#     """
#     try:
#         return carrying_amount + accrued_interest
#     except Exception as e:
#         save_log('calculate_exposure_at_default', 'ERROR', f"Error calculating EAD: {e}")
#         return None

# def process_accrued_interest_and_ead_for_account(entry):
#     """
#     Calculate the accrued interest and exposure at default (EAD) for a single entry in FCT_Stage_Determination.
#     """
#     try:
#         total_accrued_interest = entry.n_accrued_interest or calculate_accrued_interest(entry.n_account_number, entry.fic_mis_date)
#         total_exposure_at_default = calculate_exposure_at_default(entry.n_carrying_amount_ncy, total_accrued_interest)

#         if total_exposure_at_default is not None:
#             entry.n_accrued_interest = total_accrued_interest
#             entry.n_exposure_at_default = total_exposure_at_default
#             return entry  # Return the updated entry for bulk update
#     except Exception as e:
#         save_log('process_accrued_interest_and_ead_for_account', 'ERROR', f"Error processing account {entry.n_account_number}: {e}")
#     return None

# def update_stage_determination_accrued_interest_and_ead(fic_mis_date):
#     """
#     This function updates the FCT_Stage_Determination table with the total accrued interest and exposure at default (EAD)
#     for each account. The accrued interest and EAD are calculated from the FSI_Expected_Cashflow table, and EAD is 
#     based on the n_carrying_amount_ncy field from FCT_Stage_Determination.
#     """
#     try:
#         stage_determination_entries = FCT_Stage_Determination.objects.filter(
#             fic_mis_date=fic_mis_date,
#             n_exposure_at_default__isnull=True
#         ).exclude(n_prod_code__isnull=True)

#         if not stage_determination_entries.exists():
#             save_log('update_stage_determination_accrued_interest_and_ead', 'INFO', f"No records found in FCT_Stage_Determination for fic_mis_date {fic_mis_date} with NULL exposure at default.")
#             return 0
        
#         updated_entries = []

#         with ThreadPoolExecutor(max_workers=4) as executor:
#             futures = [executor.submit(process_accrued_interest_and_ead_for_account, entry) for entry in stage_determination_entries]

#             for future in as_completed(futures):
#                 result = future.result()
#                 if result:
#                     updated_entries.append(result)

#         if updated_entries:
#             # Perform a single bulk update for all updated entries
#             FCT_Stage_Determination.objects.bulk_update(updated_entries, ['n_accrued_interest', 'n_exposure_at_default'])
#             save_log('update_stage_determination_accrued_interest_and_ead', 'INFO', f"Successfully updated {len(updated_entries)} records with accrued interest and EAD.")
#         else:
#             save_log('update_stage_determination_accrued_interest_and_ead', 'INFO', "No records were updated.")

#         return 1
#     except Exception as e:
#         save_log('update_stage_determination_accrued_interest_and_ead', 'ERROR', f"Error during update process: {e}")
#         return 0
