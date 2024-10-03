from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from math import pow
from django.db import transaction
from ..models import *

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
    
def process_discount_records(records, batch_number):
    """
    Function to process a batch of records for discount calculations.
    """
    updated_records = []
    print(f"Processing batch {batch_number} with {len(records)} records...")

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
            print(f"Error processing record for account {record.v_account_number}: {e}")

    print(f"Finished processing batch {batch_number}.")
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
            print(f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
            return
        
        print(f"Fetched {len(records)} records for processing.")

        # Split the records into batches
        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        # Process records in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i, batch in enumerate(chunker(records, batch_size)):
                futures.append(executor.submit(process_discount_records, batch, i + 1))

            # Wait for all threads to complete and gather the results
            updated_batches = []
            for future in futures:
                try:
                    updated_batches.extend(future.result())
                except Exception as e:
                    print(f"Error in thread execution: {e}")

        # Perform a bulk update to save all the records at once
        with transaction.atomic():
            fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
                'n_discount_rate', 
                'n_discount_factor'
            ])
        
        print(f"Successfully updated {len(updated_batches)} records.")

    except Exception as e:
        print(f"Error calculating discount factors for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")



