from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from django.db import transaction
from ..models import *
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

def process_records(records):
    """
    Function to process a batch of records and apply calculations.
    """
    updated_records = []
    
    for record in records:
        try:
            # 1. Calculate `n_expected_cash_flow_rate`
            if record.n_cumulative_loss_rate is not None:
                record.n_expected_cash_flow_rate = Decimal(1) - record.n_cumulative_loss_rate

            # 2. Calculate `n_12m_exp_cash_flow` using 12-month cumulative PD and LGD
            if record.n_12m_cumulative_pd is not None and record.n_lgd_percent is not None:
                record.n_12m_exp_cash_flow = (record.n_cash_flow_amount or Decimal(0)) * (Decimal(1) - (record.n_12m_cumulative_pd * record.n_lgd_percent))

            # 3. Calculate `n_expected_cash_flow` using the expected cash flow rate
            if record.n_expected_cash_flow_rate is not None:
                record.n_expected_cash_flow = (record.n_cash_flow_amount or Decimal(0)) * record.n_expected_cash_flow_rate

            # Add the updated record to the list
            updated_records.append(record)
        except Exception as e:
            save_log('process_records', 'ERROR', f"Error processing record for account {record.v_account_number}: {e}")
    
    return updated_records

def calculate_expected_cash_flow(fic_mis_date, batch_size=1000, num_threads=4):
    """
    Main function to calculate expected cash flow with multithreading and bulk update.
    """
    try:
        run_skey = get_latest_run_skey()
        records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))
        
        if not records:
            save_log('calculate_expected_cash_flow', 'INFO', f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
            return 0
        
        total_updated_records = 0

        # Helper to chunk the records into smaller batches
        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for batch in chunker(records, batch_size):
                futures.append(executor.submit(process_records, batch))

            updated_batches = []
            for future in futures:
                try:
                    updated_records = future.result()
                    updated_batches.extend(updated_records)
                    total_updated_records += len(updated_records)
                except Exception as e:
                    save_log('calculate_expected_cash_flow', 'ERROR', f"Error in thread execution: {e}")
                    return 0

        # Perform a single bulk update for all processed records
        with transaction.atomic():
            fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
                'n_expected_cash_flow_rate', 
                'n_12m_exp_cash_flow', 
                'n_expected_cash_flow'
            ])
        
        save_log('calculate_expected_cash_flow', 'INFO', f"Successfully updated {total_updated_records} records.")
        return 1

    except Exception as e:
        save_log('calculate_expected_cash_flow', 'ERROR', f"Error calculating expected cash flows for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
        return 0
