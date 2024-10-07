from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
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

def process_12m_expected_loss(records):
    """
    Function to process a batch of records and apply calculations for 12-month forward loss fields.
    """
    updated_records = []

    for record in records:
        try:
            # Calculate `n_12m_fwd_expected_loss`
            if record.n_exposure_at_default is not None and record.n_12m_per_period_pd is not None and record.n_lgd_percent is not None:
                record.n_12m_fwd_expected_loss = record.n_exposure_at_default * record.n_12m_per_period_pd * record.n_lgd_percent

            # Calculate `n_12m_fwd_expected_loss_pv`
            if record.n_discount_factor is not None and record.n_12m_fwd_expected_loss is not None:
                record.n_12m_fwd_expected_loss_pv = record.n_discount_factor * record.n_12m_fwd_expected_loss

            updated_records.append(record)

        except Exception as e:
            save_log('process_12m_expected_loss', 'ERROR', f"Error processing record {record.v_account_number}: {e}")

    return updated_records

def process_forward_expected_loss(records):
    """
    Function to process a batch of records and apply calculations for forward loss fields.
    """
    updated_records = []

    for record in records:
        try:
            # Calculate `n_forward_expected_loss`
            if record.n_exposure_at_default is not None and record.n_per_period_impaired_prob is not None and record.n_lgd_percent is not None:
                record.n_forward_expected_loss = record.n_exposure_at_default * record.n_per_period_impaired_prob * record.n_lgd_percent

            # Calculate `n_forward_expected_loss_pv`
            if record.n_discount_factor is not None and record.n_forward_expected_loss is not None:
                record.n_forward_expected_loss_pv = record.n_discount_factor * record.n_forward_expected_loss

            updated_records.append(record)

        except Exception as e:
            save_log('process_forward_expected_loss', 'ERROR', f"Error processing record {record.v_account_number}: {e}")

    return updated_records

def calculate_12m_expected_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
    """
    Calculate 12-month expected loss fields with multithreading and bulk update.
    """
    try:
        run_skey = get_latest_run_skey()
        records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))

        if not records:
            save_log('calculate_12m_expected_loss_fields', 'INFO', f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
            return 0

        save_log('calculate_12m_expected_loss_fields', 'INFO', f"Fetched {len(records)} records for processing.")

        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(process_12m_expected_loss, batch) for batch in chunker(records, batch_size)]
            updated_batches = []
            for future in futures:
                try:
                    updated_batches.extend(future.result())
                except Exception as e:
                    save_log('calculate_12m_expected_loss_fields', 'ERROR', f"Error in thread execution: {e}")
                    return 0

        with transaction.atomic():
            fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
                'n_12m_fwd_expected_loss', 
                'n_12m_fwd_expected_loss_pv'
            ])

        save_log('calculate_12m_expected_loss_fields', 'INFO', f"Successfully updated {len(updated_batches)} records.")
        return 1

    except Exception as e:
        save_log('calculate_12m_expected_loss_fields', 'ERROR', f"Error calculating 12-month forward loss fields for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
        return 0

def calculate_forward_expected_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
    """
    Calculate forward expected loss fields with multithreading and bulk update.
    """
    try:
        run_skey = get_latest_run_skey()
        records = list(fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=run_skey))

        if not records:
            save_log('calculate_forward_expected_loss_fields', 'INFO', f"No records found for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}.")
            return 0

        save_log('calculate_forward_expected_loss_fields', 'INFO', f"Fetched {len(records)} records for processing.")

        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(process_forward_expected_loss, batch) for batch in chunker(records, batch_size)]
            updated_batches = []
            for future in futures:
                try:
                    updated_batches.extend(future.result())
                except Exception as e:
                    save_log('calculate_forward_expected_loss_fields', 'ERROR', f"Error in thread execution: {e}")
                    return 0

        with transaction.atomic():
            fsi_Financial_Cash_Flow_Cal.objects.bulk_update(updated_batches, [
                'n_forward_expected_loss',  
                'n_forward_expected_loss_pv'
            ])

        save_log('calculate_forward_expected_loss_fields', 'INFO', f"Successfully updated {len(updated_batches)} records.")
        return 1

    except Exception as e:
        save_log('calculate_forward_expected_loss_fields', 'ERROR', f"Error calculating forward loss fields for fic_mis_date {fic_mis_date} and n_run_skey {run_skey}: {e}")
        return 0

def calculate_forward_loss_fields(fic_mis_date, batch_size=1000, num_threads=4):
    """
    Main function to calculate forward loss fields in two stages.
    """
    result = calculate_12m_expected_loss_fields(fic_mis_date, batch_size, num_threads)
    if result == 1:
        return calculate_forward_expected_loss_fields(fic_mis_date, batch_size, num_threads)
    else:
        save_log('calculate_forward_loss_fields', 'ERROR', f"Failed to complete 12-month expected loss calculation for fic_mis_date {fic_mis_date}.")
        return 0
