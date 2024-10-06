from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from django.db import transaction
from ..models import *
from ..Functions import save_log

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

def process_records(records, batch_number):
    """
    Function to process a batch of records and apply calculations.
    """
    updated_records = []
    print(f"Processing batch {batch_number} with {len(records)} records...")
    
    for record in records:
        try:
            # 1. Calculate `n_expected_cash_flow_rate`
            if record.n_cumulative_loss_rate is not None:
                record.n_expected_cash_flow_rate = Decimal(1) - record.n_cumulative_loss_rate
            else:
                record.n_expected_cash_flow_rate = record.n_expected_cash_flow_rate  # Keep existing value if cumulative loss rate is missing

            # 2. Calculate `n_12m_exp_cash_flow` using 12-month cumulative PD and LGD
            if record.n_12m_cumulative_pd is not None and record.n_lgd_percent is not None:
                record.n_12m_exp_cash_flow = (record.n_cash_flow_amount or Decimal(0)) * (Decimal(1) - (record.n_12m_cumulative_pd * record.n_lgd_percent))
            else:
                record.n_12m_exp_cash_flow = record.n_12m_exp_cash_flow  # Keep existing value

            # 3. Calculate `n_expected_cash_flow` using the expected cash flow rate
            if record.n_expected_cash_flow_rate is not None:
                record.n_expected_cash_flow = (record.n_cash_flow_amount or Decimal(0)) * record.n_expected_cash_flow_rate
            else:
                record.n_expected_cash_flow = record.n_expected_cash_flow  # Keep existing value

            # Add the updated record to the list
            updated_records.append(record)
        except Exception as e:
            print(f"Error processing record for account {record.v_account_number}: {e}")
    
    print(f"Finished processing batch {batch_number}.")
    return updated_records


def calculate_expected_cash_flow(fic_mis_date, batch_size=1000, num_threads=4):
    """
    Main function to calculate expected cash flow with multithreading and bulk update.
    """
    try:
        run_skey = get_latest_run_skey()
        # Fetch the relevant records for the run_skey
        records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))
        
        if not records:
            print(f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
            return 0  # Return 0 if no records are found
        
        print(f"Fetched {len(records)} records for processing.")

        # Split the records into batches
        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        # Process records in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i, batch in enumerate(chunker(records, batch_size)):
                futures.append(executor.submit(process_records, batch, i+1))

            # Wait for all threads to complete and gather the results
            updated_batches = []
            for future in futures:
                try:
                    updated_batches.extend(future.result())
                except Exception as e:
                    print(f"Error in thread execution: {e}")
                    return 0  # Return 0 if any thread encounters an error

        # Perform a bulk update to save all the records at once
        with transaction.atomic():
            fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
                'n_expected_cash_flow_rate', 
                'n_12m_exp_cash_flow', 
                'n_expected_cash_flow'
            ])
        
        print(f"Successfully updated {len(updated_batches)} records.")
        return 1  # Return 1 on successful completion

    except Exception as e:
        print(f"Error calculating expected cash flows for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
        return 0  # Return 0 in case of any exception
