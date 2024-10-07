from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from ..models import fsi_Financial_Cash_Flow_Cal, FSI_PD_Interpolated, Dim_Run
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

def update_marginal_pd(fic_mis_date, max_workers=5, batch_size=1000):
    """
    Calculates and updates n_per_period_impaired_prob and n_12m_per_period_pd in the 
    fsi_Financial_Cash_Flow_Cal table.
    
    :param fic_mis_date: Financial MIS date used for filtering the records.
    :param max_workers: Maximum number of threads for parallel processing.
    :param batch_size: Size of each batch for processing records in bulk updates.
    """
    try:
        n_run_skey = get_latest_run_skey()
        cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

        if not cash_flows.exists():
            save_log('update_marginal_pd', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date} and run_skey {n_run_skey}.")
            return 0

        total_updated_records = 0

        def process_batch(batch):
            try:
                updates = []
                for cash_flow in batch:
                    if cash_flow.n_cumulative_impaired_prob is not None:
                        if cash_flow.n_cash_flow_bucket_id > 1:
                            previous_cash_flow = fsi_Financial_Cash_Flow_Cal.objects.filter(
                                fic_mis_date=fic_mis_date,
                                n_run_skey=n_run_skey,
                                v_account_number=cash_flow.v_account_number,
                                n_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id - 1
                            ).first()
                            if previous_cash_flow and previous_cash_flow.n_cumulative_impaired_prob is not None:
                                cash_flow.n_per_period_impaired_prob = abs(cash_flow.n_cumulative_impaired_prob - previous_cash_flow.n_cumulative_impaired_prob)
                        else:
                            cash_flow.n_per_period_impaired_prob = abs(cash_flow.n_cumulative_impaired_prob)

                    if cash_flow.n_12m_cumulative_pd is not None:
                        if cash_flow.n_cash_flow_bucket_id > 1:
                            previous_cash_flow = fsi_Financial_Cash_Flow_Cal.objects.filter(
                                fic_mis_date=fic_mis_date,
                                n_run_skey=n_run_skey,
                                v_account_number=cash_flow.v_account_number,
                                n_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id - 1
                            ).first()
                            if previous_cash_flow and previous_cash_flow.n_12m_cumulative_pd is not None:
                                cash_flow.n_12m_per_period_pd = abs(cash_flow.n_12m_cumulative_pd - previous_cash_flow.n_12m_cumulative_pd)
                        else:
                            cash_flow.n_12m_per_period_pd = abs(cash_flow.n_12m_cumulative_pd)

                    updates.append(cash_flow)

                # Bulk update for the current batch
                if updates:
                    fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
                        updates, ['n_per_period_impaired_prob', 'n_12m_per_period_pd']
                    )
                return len(updates)

            except Exception as e:
                save_log('update_marginal_pd', 'ERROR', f"Error updating batch: {e}")
                return 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            batch = []
            for cash_flow in cash_flows.iterator(chunk_size=batch_size):
                batch.append(cash_flow)
                if len(batch) >= batch_size:
                    futures.append(executor.submit(process_batch, batch))
                    batch = []

            if batch:
                futures.append(executor.submit(process_batch, batch))

            for future in as_completed(futures):
                try:
                    total_updated_records += future.result()
                except Exception as exc:
                    save_log('update_marginal_pd', 'ERROR', f"Thread encountered an error: {exc}")
                    return 0

        save_log('update_marginal_pd', 'INFO', f"Total updated records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}: {total_updated_records}")
        return 1 if total_updated_records > 0 else 0

    except Exception as e:
        save_log('update_marginal_pd', 'ERROR', f"Error during marginal PD update process: {e}")
        return 0