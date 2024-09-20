from django.db import transaction
from concurrent.futures import ThreadPoolExecutor

def update_cash_flow_with_account_pd_buckets(fic_mis_date, n_run_skey):
    """
    This function updates the fsi_Financial_Cash_Flow_Cal table using account-level PD values from 
    FSI_PD_Account_Interpolated. It directly aligns the PD values to the cash flow buckets of each account.
    
    It accounts for multiple cash flow buckets that extend to the maturity date and ensures that the first 12 months
    are handled separately. For buckets that fall beyond the 12-month period, we will use the PD value from bucket 12.
    
    No need for additional conversion, bucket adjustment, or delinquent bands. We handle the 12-month calculation
    based on the `v_amrt_term_unit` using the `get_buckets_for_12_months` function.
    """

    # Fetch the cash flow records that need to be updated
    cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

    def update_single_cash_flow(cash_flow):
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

                    cash_flow.save()

        except Exception as e:
            print(f"Error updating account {cash_flow.v_account_number}: {e}")

    # Use multi-threading to speed up the process
    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(update_single_cash_flow, cash_flows)

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


# Example usage:
update_cash_flow_with_account_pd_buckets(fic_mis_date='2024-09-17', n_run_skey=12345)
