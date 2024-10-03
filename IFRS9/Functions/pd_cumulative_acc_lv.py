from django.db import transaction
from concurrent.futures import ThreadPoolExecutor
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



def update_cash_flow_with_account_pd_buckets(fic_mis_date, batch_size=1000, max_workers=8):
    """
    This function updates the fsi_Financial_Cash_Flow_Cal table using account-level PD values from 
    FSI_PD_Account_Interpolated. It directly aligns the PD values to the cash flow buckets of each account.
    
    It accounts for multiple cash flow buckets that extend to the maturity date and ensures that the first 12 months
    are handled separately. For buckets that fall beyond the 12-month period, we will use the PD value from bucket 12.
    
    No need for additional conversion, bucket adjustment, or delinquent bands. We handle the 12-month calculation
    based on the `v_amrt_term_unit` using the `get_buckets_for_12_months` function.
    """
    n_run_skey = get_latest_run_skey()
    # Fetch the cash flow records that need to be updated in batches
    cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

    def process_batch(batch):
        updates = []
        for cash_flow in batch:
            try:
                # Fetch the account-level interpolated PD records
                account_pd_records = FSI_PD_Account_Interpolated.objects.filter(
                    v_account_number=cash_flow.v_account_number,
                    fic_mis_date=fic_mis_date
                )

                if account_pd_records.exists():
                    # Step 1: Fetch the relevant PD record based on the corresponding bucket ID
                    pd_record = account_pd_records.filter(v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id).first()

                    # Step 2: Assign PD values to cash flow records for the given bucket
                    if pd_record:
                        cash_flow.n_cumulative_loss_rate = pd_record.n_cumulative_default_prob * cash_flow.n_lgd_percent
                        cash_flow.n_cumulative_impaired_prob = pd_record.n_cumulative_default_prob

                        # Calculate 12-month cumulative PD based on the amortization term unit
                        months_to_12m = get_buckets_for_12_months(cash_flow.v_amrt_term_unit)
                        if cash_flow.n_cash_flow_bucket_id <= months_to_12m:
                            # Use the corresponding bucket's PD for the first 12 months
                            cash_flow.n_12m_cumulative_pd = pd_record.n_cumulative_default_prob
                        else:
                            # Use the PD from the last bucket within the first 12 months (the 12m equivalent)
                            pd_record_12 = account_pd_records.filter(v_cash_flow_bucket_id=months_to_12m).first()
                            if pd_record_12:
                                cash_flow.n_12m_cumulative_pd = pd_record_12.n_cumulative_default_prob

                        # Add the updated cash flow to the list for bulk update
                        updates.append(cash_flow)

            except Exception as e:
                print(f"Error updating account {cash_flow.v_account_number}: {e}")

        # Perform bulk update after processing the batch
        if updates:
            fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
                updates, 
                ['n_cumulative_loss_rate', 'n_cumulative_impaired_prob', 'n_12m_cumulative_pd']
            )

    # Using ThreadPoolExecutor for multi-threading
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        batch = []
        futures = []
        for cash_flow in cash_flows.iterator(chunk_size=batch_size):
            batch.append(cash_flow)
            if len(batch) >= batch_size:
                futures.append(executor.submit(process_batch, batch))
                batch = []  # Clear batch after submitting

        # Process any remaining batch
        if batch:
            futures.append(executor.submit(process_batch, batch))

        for future in futures:
            future.result()  # Check for exceptions in threads

    print(f"Updated {cash_flows.count()} records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}")


def get_buckets_for_12_months(v_amrt_term_unit):
    """
    This function returns the number of buckets required to reach 12 months based on the amortization term unit (M, Q, H, Y).
    For example, for quarterly (Q) accounts, it returns 4 buckets, as 4 quarters are needed for 12 months.
    """
    term_unit_to_buckets = {
        'M': 12,  # Monthly: 12 months = 12 buckets
        'Q': 4,   # Quarterly: 12 months = 4 buckets
        'H': 2,   # Half-yearly: 12 months = 2 buckets
        'Y': 1    # Yearly: 12 months = 1 bucket
    }
    return term_unit_to_buckets.get(v_amrt_term_unit, 12)  # Default to 12 months for monthly if not found



