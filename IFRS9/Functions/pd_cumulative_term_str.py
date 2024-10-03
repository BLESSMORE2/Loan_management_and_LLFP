from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db.models import Sum
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


def update_cash_flow_with_pd_buckets(fic_mis_date, max_workers=5, batch_size=1000):
    """
    Optimized function using bulk_update to update cash flow records in batches to reduce database I/O.
    """
    n_run_skey = get_latest_run_skey()
    # Fetch cash flow records in batches to avoid memory overload
    cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

    def process_batch(batch):
        try:
            updates = []
            update_count = 0  # Counter for the number of records updated
            for cash_flow in batch:
                account_data = FCT_Stage_Determination.objects.filter(
                    n_account_number=cash_flow.v_account_number,
                    fic_mis_date=fic_mis_date
                ).first()

                if account_data:
                    pd_records = FSI_PD_Interpolated.objects.filter(
                        v_pd_term_structure_id=account_data.n_pd_term_structure_skey,
                        fic_mis_date=fic_mis_date,
                    )

                    if pd_records.exists():
                        pd_record = None
                        if pd_records.first().v_pd_term_structure_type == 'R':
                            pd_record = pd_records.filter(
                                v_int_rating_code=account_data.n_credit_rating_code,
                                v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id
                            ).first()
                        elif pd_records.first().v_pd_term_structure_type == 'D':
                            pd_record = pd_records.filter(
                                v_delq_band_code=account_data.n_delq_band_code,
                                v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id
                            ).first()

                        if pd_record:
                            # Assign cumulative loss rate and impaired probability
                            cash_flow.n_cumulative_loss_rate = pd_record.n_cumulative_default_prob * account_data.n_lgd_percent
                            cash_flow.n_cumulative_impaired_prob = pd_record.n_cumulative_default_prob

                            # Calculate 12-month cumulative PD based on amortization unit
                            months_to_12m = get_buckets_for_12_months(account_data.v_amrt_term_unit)
                            if cash_flow.n_cash_flow_bucket_id <= months_to_12m:
                                cash_flow.n_12m_cumulative_pd = pd_record.n_cumulative_default_prob
                            else:
                                pd_record_12 = pd_records.filter(v_cash_flow_bucket_id=months_to_12m).first()
                                if pd_record_12:
                                    cash_flow.n_12m_cumulative_pd = pd_record_12.n_cumulative_default_prob

                            updates.append(cash_flow)
                            update_count += 1  # Increment the counter

            # Perform a bulk update for the batch
            if updates:
                fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
                    updates, 
                    ['n_cumulative_loss_rate', 'n_cumulative_impaired_prob', 'n_12m_cumulative_pd']
                )
            return update_count

        except Exception as e:
            print(f"Error updating batch: {e}")
            return 0  # Return 0 if the batch fails

    total_updated_records = 0  # Overall count for all batches

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

    # Print the total records updated for the given run key and mis date
    print(f"Updated records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}: {total_updated_records}")


def get_buckets_for_12_months(v_amrt_term_unit):
    """
    This function returns the number of buckets required to reach 12 months based on the amortization term unit (M, Q, H, Y).
    """
    term_unit_to_buckets = {
        'M': 12,  # Monthly: 12 months = 12 buckets
        'Q': 4,   # Quarterly: 12 months = 4 buckets
        'H': 2,   # Half-yearly: 12 months = 2 buckets
        'Y': 1    # Yearly: 12 months = 1 bucket
    }
    return term_unit_to_buckets.get(v_amrt_term_unit, 12)

