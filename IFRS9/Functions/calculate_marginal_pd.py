from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from ..models import fsi_Financial_Cash_Flow_Cal, FSI_PD_Interpolated, Dim_Run
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

def update_marginal_pd(fic_mis_date, max_workers=5, batch_size=1000):
    """
    This function calculates and updates n_per_period_impaired_prob and n_12m_per_period_pd in the 
    fsi_Financial_Cash_Flow_Cal table.
    
    :param fic_mis_date: Financial MIS date used for filtering the records.
    :param max_workers: Maximum number of threads for parallel processing.
    :param batch_size: Size of each batch for processing records in bulk updates.
    """
    try:
        n_run_skey = get_latest_run_skey()
        # Fetch the cash flow records in batches for the given fic_mis_date and n_run_skey
        cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

        if not cash_flows.exists():
            print(f"No cash flows found for fic_mis_date {fic_mis_date} and run_skey {n_run_skey}.")
            return 0  # Return 0 if no records are found

        def process_batch(batch):
            try:
                updates = []
                update_count = 0  # Counter for the number of records updated

                for cash_flow in batch:
                    # Validate that cumulative impaired probabilities are not None before subtraction
                    if cash_flow.n_cumulative_impaired_prob is not None:
                        if cash_flow.n_cash_flow_bucket_id > 1:
                            previous_cash_flow = fsi_Financial_Cash_Flow_Cal.objects.filter(
                                fic_mis_date=fic_mis_date,
                                n_run_skey=n_run_skey,
                                v_account_number=cash_flow.v_account_number,
                                n_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id - 1
                            ).first()
                            if previous_cash_flow and previous_cash_flow.n_cumulative_impaired_prob is not None:
                                # Ensure marginal PD is always positive
                                cash_flow.n_per_period_impaired_prob = abs(cash_flow.n_cumulative_impaired_prob - previous_cash_flow.n_cumulative_impaired_prob)
                        else:
                            # For the first bucket, marginal PD is the same as cumulative PD
                            cash_flow.n_per_period_impaired_prob = abs(cash_flow.n_cumulative_impaired_prob)

                    # Validate that 12-month cumulative PD is not None before subtraction
                    if cash_flow.n_12m_cumulative_pd is not None:
                        if cash_flow.n_cash_flow_bucket_id > 1:
                            previous_cash_flow = fsi_Financial_Cash_Flow_Cal.objects.filter(
                                fic_mis_date=fic_mis_date,
                                n_run_skey=n_run_skey,
                                v_account_number=cash_flow.v_account_number,
                                n_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id - 1
                            ).first()
                            if previous_cash_flow and previous_cash_flow.n_12m_cumulative_pd is not None:
                                # Ensure marginal 12-month PD is always positive
                                cash_flow.n_12m_per_period_pd = abs(cash_flow.n_12m_cumulative_pd - previous_cash_flow.n_12m_cumulative_pd)
                        else:
                            # For the first bucket, 12-month marginal PD is the same as 12-month cumulative PD
                            cash_flow.n_12m_per_period_pd = abs(cash_flow.n_12m_cumulative_pd)

                    updates.append(cash_flow)
                    update_count += 1  # Increment the counter for successfully updated records

                # Perform a bulk update for the batch
                if updates:
                    fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
                        updates, ['n_per_period_impaired_prob', 'n_12m_per_period_pd']
                    )

                return update_count

            except Exception as e:
                print(f"Error updating batch: {e}")
                return 0  # Return 0 if an error occurs

        total_updated_records = 0  # Counter for total records updated

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

            # Process the results
            for future in as_completed(futures):
                try:
                    updated_count = future.result()
                    total_updated_records += updated_count
                    print(f"Batch updated {updated_count} records.")
                except Exception as exc:
                    print(f"Error occurred in thread: {exc}")
                    return 0  # Return 0 if any thread encounters an error

        # Print the total records updated for the given run key and mis date
        print(f"Updated records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}: {total_updated_records}")
        return 1  # Return 1 on successful completion

    except Exception as e:
        print(f"Error during marginal PD update process: {e}")
        return 0  # Return 0 in case of any exception
