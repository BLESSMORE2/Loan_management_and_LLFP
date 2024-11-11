from decimal import Decimal, InvalidOperation
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import pow
from ..models import FCT_Stage_Determination
from .save_log import save_log

MAX_EIR = Decimal('999.99999999999')  # Max value with 15 digits and 11 decimal places
MIN_EIR = Decimal('0')  # EIR should not be negative, so we set the minimum at zero

def calculate_eir_for_stage(entry):
    """
    Calculate the Effective Interest Rate (EIR) for a specific FCT_Stage_Determination entry.
    """
    try:
        nominal_rate = Decimal(entry.n_curr_interest_rate/100) if entry.n_curr_interest_rate else None
        v_amrt_term_unit = entry.v_amrt_term_unit
        
        term_unit_map = {
        'D': 365,  # Daily compounding
        'W': 52,   # Weekly compounding
        'M': 12,   # Monthly compounding
        'Q': 4,    # Quarterly compounding
        'H': 2,    # Semi-annual compounding
        'Y': 1     # Annual compounding
        }
        
        if nominal_rate is None or v_amrt_term_unit not in term_unit_map:
            return None
        
        compounding_frequency = term_unit_map[v_amrt_term_unit]
        eir = Decimal(pow((1 + float(nominal_rate / compounding_frequency)), compounding_frequency) - 1)

        # Clamp and quantize EIR to fit within max_digits=15 and decimal_places=11
        eir = max(MIN_EIR, min(MAX_EIR, eir)).quantize(Decimal('1.00000000000'))
        
        return eir
    
    except (InvalidOperation, OverflowError) as e:
        save_log('calculate_eir_for_stage', 'ERROR', f"Error calculating EIR for account {entry.n_account_number}: {e}")
        return None

def update_stage_determination_eir(fic_mis_date, max_workers=8, batch_size=5000):
    """
    Update the Effective Interest Rate (EIR) for accounts in the FCT_Stage_Determination table.
    """
    try:
        stage_determination_entries = FCT_Stage_Determination.objects.filter(
            fic_mis_date=fic_mis_date, 
            n_effective_interest_rate__isnull=True
        )
        
        total_entries = stage_determination_entries.count()
        batches = [stage_determination_entries[i:i + batch_size] for i in range(0, total_entries, batch_size)]
        save_log('update_stage_determination_eir', 'INFO', f"Processing {total_entries} entries in {len(batches)} batches...")

        error_logs = {}

        def process_batch(batch):
            bulk_updates = []
            for entry in batch:
                try:
                    eir = calculate_eir_for_stage(entry)
                    
                    if eir is not None:
                        entry.n_effective_interest_rate = eir
                        bulk_updates.append(entry)
                
                except Exception as e:
                    error_message = f"Error processing account {entry.n_account_number}: {e}"
                    error_logs[error_message] = 1  # Record unique errors
            
            # Perform bulk update for the current batch
            if bulk_updates:
                try:
                    FCT_Stage_Determination.objects.bulk_update(bulk_updates, ['n_effective_interest_rate'])
                except Exception as e:
                    error_logs[f"Bulk update error: {e}"] = 1

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_batch, batch) for batch in batches]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    error_logs[f"Thread encountered an error: {exc}"] = 1

        for error_message in error_logs:
            save_log('update_stage_determination_eir', 'ERROR', error_message)

        if not error_logs:
            save_log('update_stage_determination_eir', 'INFO', f"Successfully processed {total_entries} records.")
        return 1 if not error_logs else 0

    except Exception as e:
        save_log('update_stage_determination_eir', 'ERROR', f"Error during EIR update process: {e}")
        return 0



# from decimal import Decimal
# from concurrent.futures import ThreadPoolExecutor
# from math import pow
# from ..models import FCT_Stage_Determination
# from ..Functions import save_log

# def calculate_eir_for_stage(entry):
#     """
#     Calculate the Effective Interest Rate (EIR) for a specific FCT_Stage_Determination entry.
#     """
#     try:
#         # Get the nominal interest rate and the amortization term unit
#         nominal_rate = Decimal(entry.n_curr_interest_rate) if entry.n_curr_interest_rate else None
#         v_amrt_term_unit = entry.v_amrt_term_unit
        
#         # Map amortization unit (M, Q, H, Y) to compounding periods per year
#         term_unit_map = {
#             'M': 12,  # Monthly compounding
#             'Q': 4,   # Quarterly compounding
#             'H': 2,   # Semi-annual compounding
#             'Y': 1    # Annual compounding
#         }
        
#         # If the nominal rate is not available, return None
#         if nominal_rate is None or v_amrt_term_unit not in term_unit_map:
#             print(f"Skipping account {entry.n_account_number} due to missing interest rate or term unit.")
#             return None
        
#         # Get the compounding frequency based on the term unit (e.g., monthly = 12, quarterly = 4)
#         compounding_frequency = term_unit_map[v_amrt_term_unit]
        
#         # Calculate the Effective Interest Rate (EIR) using the formula
#         eir = Decimal(pow((1 + float(nominal_rate / compounding_frequency)), compounding_frequency) - 1)
        
#         # Return the calculated EIR
#         return eir
    
#     except Exception as e:
#         print(f"Error calculating EIR for account {entry.n_account_number}: {e}")
#         return None

# # Function to update FCT_Stage_Determination with calculated EIRs
# def update_stage_determination_eir(fic_mis_date, max_workers=8, batch_size=1000):
#     """
#     Update the Effective Interest Rate (EIR) for accounts in the FCT_Stage_Determination table.
#     """
#     try:
#         # Fetch all entries with missing EIR for the given fic_mis_date
#         stage_determination_entries = FCT_Stage_Determination.objects.filter(
#             fic_mis_date=fic_mis_date, 
#             n_effective_interest_rate__isnull=True
#         )
        
#         total_entries = stage_determination_entries.count()
       
#         # Process entries in batches
#         batches = [stage_determination_entries[i:i + batch_size] for i in range(0, total_entries, batch_size)]
#         print(f"Processing {total_entries} entries in {len(batches)} batches...")

#         def process_batch(batch):
#             bulk_updates = []
#             for entry in batch:
#                 try:
#                     # Calculate the EIR for each entry
#                     eir = calculate_eir_for_stage(entry)
                    
#                     if eir is not None:
#                         # Update the EIR field in the entry
#                         entry.n_effective_interest_rate = eir
#                         bulk_updates.append(entry)
#                         print(f"EIR calculated for account {entry.n_account_number}: {eir:.8f}")
                
#                 except Exception as e:
#                     print(f"Error processing account {entry.n_account_number}: {e}")
            
#             # Perform bulk update for the current batch
#             if bulk_updates:
#                 try:
#                     FCT_Stage_Determination.objects.bulk_update(bulk_updates, ['n_effective_interest_rate'])
#                     print(f"Successfully updated {len(bulk_updates)} records.")
#                 except Exception as e:
#                     print(f"Error during bulk update: {e}")
#                     return 0  # Return 0 if bulk update fails

#         # Use ThreadPoolExecutor to process batches in parallel
#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = [executor.submit(process_batch, batch) for batch in batches]

#             # Wait for all threads to complete
#             for future in futures:
#                 try:
#                     future.result()
#                 except Exception as exc:
#                     print(f"Thread encountered an error: {exc}")
#                     return 0  # Return 0 if any thread encounters an error

#         print(f"Successfully processed {total_entries} records.")
#         return 1  # Return 1 on successful completion

#     except Exception as e:
#         print(f"Error during EIR update process: {e}")
#         return 0  # Return 0 in case of any exception
