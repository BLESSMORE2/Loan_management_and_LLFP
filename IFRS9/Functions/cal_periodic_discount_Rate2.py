from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from math import pow
from django.db import transaction
from ..models import fsi_Financial_Cash_Flow_Cal, Dim_Run
from .save_log import save_log

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.first()
        if not run_record:
            raise ValueError("No run key is available in the Dim_Run table.")
        return run_record.latest_run_skey
    except Dim_Run.DoesNotExist:
        raise ValueError("Dim_Run table is missing.")
    
def process_discount_records(records):
    """
    Function to process a batch of records for discount calculations.
    """
    updated_records = []

    for record in records:
        try:
            # 1. Calculate `n_discount_rate` based on the condition
            cond_10 = 10 if record.n_effective_interest_rate is not None else 11
            if cond_10 == 10:
                record.n_discount_rate = record.n_effective_interest_rate
            else:
                record.n_discount_rate = record.n_discount_rate  # Keep existing value

            # 2. Calculate `n_discount_factor` using the discount rate and cash flow bucket ID
            if record.n_discount_rate is not None and record.n_cash_flow_bucket_id is not None:
                record.n_discount_factor = Decimal(1) / Decimal(pow((1 + record.n_discount_rate / 100), (record.n_cash_flow_bucket_id / 12)))
            else:
                record.n_discount_factor = record.n_discount_factor  # Keep existing value

            # Add the updated record to the list
            updated_records.append(record)
        except Exception as e:
            save_log('process_discount_records', 'ERROR', f"Error processing record {record.v_account_number}: {e}")

    return updated_records


def calculate_discount_factors(fic_mis_date, batch_size=1000, num_threads=4):
    """
    Main function to calculate discount rates and factors with multithreading and bulk update.
    """
    try:
        run_skey = get_latest_run_skey()
        # Fetch the relevant records for the run_skey
        records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))
        
        if not records:
            save_log('calculate_discount_factors', 'INFO', f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
            return 0  # Return 0 if no records are found
        
        save_log('calculate_discount_factors', 'INFO', f"Fetched {len(records)} records for processing.")

        # Split the records into batches
        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        # Process records in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(process_discount_records, batch) for batch in chunker(records, batch_size)]

            # Gather results from all threads
            updated_batches = []
            for future in futures:
                try:
                    updated_batches.extend(future.result())
                except Exception as e:
                    save_log('calculate_discount_factors', 'ERROR', f"Error in thread execution: {e}")
                    return 0  # Return 0 if any thread encounters an error

        # Perform a bulk update to save all the records at once
        with transaction.atomic():
            fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
                'n_discount_rate', 
                'n_discount_factor'
            ])
        
        save_log('calculate_discount_factors', 'INFO', f"Successfully updated {len(updated_batches)} records.")
        return 1  # Return 1 on successful completion

    except Exception as e:
        save_log('calculate_discount_factors', 'ERROR', f"Error calculating discount factors for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
        return 0  # Return 0 in case of any exception
