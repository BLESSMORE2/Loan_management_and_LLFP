from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from ..models import fsi_Financial_Cash_Flow_Cal, FSI_PD_Interpolated


def update_marginal_pd(fic_mis_date, n_run_skey, max_workers=5, batch_size=1000):
    """
    This function calculates and updates n_per_period_impaired_prob and n_12m_per_period_pd in the 
    fsi_Financial_Cash_Flow_Cal table.
    
    :param fic_mis_date: Financial MIS date used for filtering the records.
    :param n_run_skey: Run key used for filtering the financial cash flow records.
    :param max_workers: Maximum number of threads for parallel processing.
    :param batch_size: Size of each batch for processing records in bulk updates.
    """

    # Fetch the cash flow records in batches for the given fic_mis_date and n_run_skey
    cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

    def process_batch(batch):
        try:
            updates = []
            for cash_flow in batch:
                # Calculate n_per_period_impaired_prob (Marginal PD)
                if cash_flow.n_cash_flow_bucket_id > 1:
                    # Get the previous PD record for the prior bucket
                    previous_cash_flow = fsi_Financial_Cash_Flow_Cal.objects.filter(
                        fic_mis_date=fic_mis_date,
                        n_run_skey=n_run_skey,
                        v_account_number=cash_flow.v_account_number,
                        n_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id - 1
                    ).first()
                    if previous_cash_flow:
                        cash_flow.n_per_period_impaired_prob = cash_flow.n_cumulative_impaired_prob - previous_cash_flow.n_cumulative_impaired_prob
                else:
                    # For the first bucket, marginal PD is the same as cumulative PD
                    cash_flow.n_per_period_impaired_prob = cash_flow.n_cumulative_impaired_prob

                # Calculate n_12m_per_period_pd (Marginal 12-Month PD)
                if cash_flow.n_cash_flow_bucket_id > 1:
                    previous_cash_flow = fsi_Financial_Cash_Flow_Cal.objects.filter(
                        fic_mis_date=fic_mis_date,
                        n_run_skey=n_run_skey,
                        v_account_number=cash_flow.v_account_number,
                        n_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id - 1
                    ).first()
                    if previous_cash_flow:
                        cash_flow.n_12m_per_period_pd = cash_flow.n_12m_cumulative_pd - previous_cash_flow.n_12m_cumulative_pd
                else:
                    # For the first bucket, 12-month marginal PD is the same as 12-month cumulative PD
                    cash_flow.n_12m_per_period_pd = cash_flow.n_12m_cumulative_pd

                updates.append(cash_flow)

            # Perform a bulk update for the batch
            if updates:
                fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
                    updates, ['n_per_period_impaired_prob', 'n_12m_per_period_pd']
                )

        except Exception as e:
            print(f"Error updating batch: {e}")

    # Using ThreadPoolExecutor for multi-threading
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        batch = []
        for cash_flow in cash_flows.iterator(chunk_size=batch_size):
            batch.append(cash_flow)
            if len(batch) >= batch_size:
                futures.append(executor.submit(process_batch, batch))
                batch = []  # Clear batch after submitting

        # Submit any remaining batch
        if batch:
            futures.append(executor.submit(process_batch, batch))

        # Collect the results
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print(f"Error occurred in thread: {exc}")

    print(f"Updated records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}")


# Example usage:
