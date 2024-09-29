from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from math import pow
from ..models import FCT_Stage_Determination

def calculate_eir_for_stage(entry):
    """
    Calculate the Effective Interest Rate (EIR) for a specific FCT_Stage_Determination entry.
    """
    try:
        # Get the nominal interest rate and the amortization term unit
        nominal_rate = Decimal(entry.n_curr_interest_rate) if entry.n_curr_interest_rate else None
        v_amrt_term_unit = entry.v_amrt_term_unit
        
        # Map amortization unit (M, Q, H, Y) to compounding periods per year
        term_unit_map = {
            'M': 12,  # Monthly compounding
            'Q': 4,   # Quarterly compounding
            'H': 2,   # Semi-annual compounding
            'Y': 1    # Annual compounding
        }
        
        # If the nominal rate is not available, return None
        if nominal_rate is None or v_amrt_term_unit not in term_unit_map:
            print(f"Skipping account {entry.n_account_number} due to missing interest rate or term unit.")
            return None
        
        # Get the compounding frequency based on the term unit (e.g., monthly = 12, quarterly = 4)
        compounding_frequency = term_unit_map[v_amrt_term_unit]
        
        # Calculate the Effective Interest Rate (EIR) using the formula
        eir = Decimal(pow((1 + float(nominal_rate / compounding_frequency)), compounding_frequency) - 1)
        
        # Return the calculated EIR
        return eir
    
    except Exception as e:
        print(f"Error calculating EIR for account {entry.n_account_number}: {e}")
        return None

# Function to update FCT_Stage_Determination with calculated EIRs
def update_stage_determination_eir(fic_mis_date, max_workers=8, batch_size=1000):
    """
    Update the Effective Interest Rate (EIR) for accounts in the FCT_Stage_Determination table.
    """
    try:
        # Fetch all entries with missing EIR for the given fic_mis_date
        stage_determination_entries = FCT_Stage_Determination.objects.filter(
            fic_mis_date=fic_mis_date, 
            n_effective_interest_rate__isnull=True
        )
        
        total_entries = stage_determination_entries.count()
        if total_entries == 0:
            print(f"No entries found for fic_mis_date {fic_mis_date} requiring EIR update.")
            return

        # Process entries in batches
        batches = [stage_determination_entries[i:i + batch_size] for i in range(0, total_entries, batch_size)]
        print(f"Processing {total_entries} entries in {len(batches)} batches...")

        def process_batch(batch):
            bulk_updates = []
            for entry in batch:
                try:
                    # Calculate the EIR for each entry
                    eir = calculate_eir_for_stage(entry)
                    
                    if eir is not None:
                        # Update the EIR field in the entry
                        entry.n_effective_interest_rate = eir
                        bulk_updates.append(entry)
                        print(f"EIR calculated for account {entry.n_account_number}: {eir:.8f}")
                
                except Exception as e:
                    print(f"Error processing account {entry.n_account_number}: {e}")
            
            # Perform bulk update for the current batch
            if bulk_updates:
                try:
                    FCT_Stage_Determination.objects.bulk_update(bulk_updates, ['n_effective_interest_rate'])
                    print(f"Successfully updated {len(bulk_updates)} records.")
                except Exception as e:
                    print(f"Error during bulk update: {e}")

        # Use ThreadPoolExecutor to process batches in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_batch, batch) for batch in batches]

            # Wait for all threads to complete
            for future in futures:
                try:
                    future.result()
                except Exception as exc:
                    print(f"Thread encountered an error: {exc}")

        print(f"Successfully processed {total_entries} records.")

    except Exception as e:
        print(f"Error during EIR update process: {e}")

# Example usage

