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


def process_forward_loss_records(records, batch_number):
    """
    Function to process a batch of records and apply calculations for forward loss fields.
    """
    updated_records = []
    print(f"Processing batch {batch_number} with {len(records)} records...")

    for record in records:
        try:
            # 1. Calculate `n_12m_fwd_expected_loss`
            if record.n_exposure_at_default is not None and record.n_12m_per_period_pd is not None and record.n_lgd_percent is not None:
                record.n_12m_fwd_expected_loss = record.n_exposure_at_default * record.n_12m_per_period_pd * record.n_lgd_percent

            # 2. Calculate `n_forward_expected_loss`
            if record.n_exposure_at_default is not None and record.n_per_period_impaired_prob is not None and record.n_lgd_percent is not None:
                record.n_forward_expected_loss = record.n_exposure_at_default * record.n_per_period_impaired_prob * record.n_lgd_percent

           
            # 4. Calculate Present Value (PV) fields
            if record.n_discount_factor is not None:
                # Calculate `n_forward_expected_loss_pv`
                if record.n_forward_expected_loss is not None:
                    record.n_forward_expected_loss_pv = record.n_discount_factor * record.n_forward_expected_loss

                # Calculate `n_12m_fwd_expected_loss_pv`
                if record.n_12m_fwd_expected_loss is not None:
                    record.n_12m_fwd_expected_loss_pv = record.n_discount_factor * record.n_12m_fwd_expected_loss

               
            # Add the updated record to the list
            updated_records.append(record)

        except Exception as e:
            print(f"Error processing record for account {record.v_account_number}: {e}")

    print(f"Finished processing batch {batch_number}.")
    return updated_records


def calculate_forward_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
    """
    Main function to calculate forward loss fields with multithreading and bulk update.
    """
    try:
        # Get the latest run key from Dim_Run table
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
                futures.append(executor.submit(process_forward_loss_records, batch, i + 1))

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
                'n_12m_fwd_expected_loss', 
                'n_forward_expected_loss',  
                'n_forward_expected_loss_pv', 
                'n_12m_fwd_expected_loss_pv'
            ])

        print(f"Successfully updated {len(updated_batches)} records.")
        return 1  # Return 1 on successful completion

    except Exception as e:
        print(f"Error calculating forward loss fields for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
        return 0  # Return 0 in case of any exception