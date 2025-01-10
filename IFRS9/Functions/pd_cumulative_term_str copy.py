from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from ..models import *
from ..Functions import save_log


def update_cash_flow_with_pd_buckets(fic_mis_date, n_run_skey, max_workers=5):
    """
    This function updates the fsi_Financial_Cash_Flow_Cal table using PD values from FSI_PD_Interpolated.
    It accounts for multiple cash flow buckets that extend to the maturity date, aligning bucket IDs between 
    cash flow terms and PD interpolation. The function selects whether to use the PD values based on the
    rating or delinquency band and assigns them to the cash flow records.
    
    For buckets that fall beyond the 12-month period, we will use the PD value from bucket 12.
    The amortization term unit (M, Q, H, Y) is taken into account when calculating the number of buckets to reach 12 months.
    
    Multi-threaded to speed up processing by handling multiple accounts concurrently.
    """
    try:
        # Fetch the cash flow records that need to be updated
        cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

        if not cash_flows.exists():
            print(f"No cash flows found for fic_mis_date {fic_mis_date} and run_skey {n_run_skey}.")
            return 0  # Return 0 if no records are found

        def process_cash_flow(cash_flow):
            try:
                # Fetch the related FCT_Stage_Determination entry for the account
                account_data = FCT_Stage_Determination.objects.filter(
                    n_account_number=cash_flow.v_account_number,
                    fic_mis_date=fic_mis_date
                ).first()

                if account_data:
                    # Step 1: Map n_pd_term_structure_skey to v_pd_term_structure_id in FSI_PD_Interpolated
                    pd_records = FSI_PD_Interpolated.objects.filter(
                        v_pd_term_structure_id=account_data.n_pd_term_structure_skey,
                        fic_mis_date=fic_mis_date,
                    )

                    if pd_records.exists():
                        # Step 2: Use V_PD_TERM_STRUCTURE_TYPE to determine if rating-based (R) or delinquency band-based (D)
                        if pd_records.first().v_pd_term_structure_type == 'R':
                            # PD based on Rating (for Rating-based PDs)
                            pd_record = pd_records.filter(
                                v_int_rating_code=account_data.n_credit_rating_code,
                                v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id
                            ).first()
                        elif pd_records.first().v_pd_term_structure_type == 'D':
                            # PD based on Delinquency Band (use n_delq_band_code directly)
                            pd_record = pd_records.filter(
                                v_delq_band_code=account_data.n_delq_band_code,
                                v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id
                            ).first()

                        # Step 3: Assign PD values to cash flow records for the given bucket
                        if pd_record:
                            # Assign cumulative loss rate and impaired probability
                            cash_flow.n_cumulative_loss_rate = pd_record.n_cumulative_default_prob * account_data.n_lgd_percent
                            cash_flow.n_cumulative_impaired_prob = pd_record.n_cumulative_default_prob

                            # Calculate 12-month cumulative PD based on amortization unit
                            months_to_12m = get_buckets_for_12_months(account_data.v_amrt_term_unit)
                            if cash_flow.n_cash_flow_bucket_id <= months_to_12m:
                                # Use corresponding bucket's PD for the first 12 months
                                cash_flow.n_12m_cumulative_pd = pd_record.n_cumulative_default_prob
                            else:
                                # Use the PD from the last bucket within the first 12 months (the 12m equivalent)
                                pd_record_12 = pd_records.filter(v_cash_flow_bucket_id=months_to_12m).first()
                                if pd_record_12:
                                    cash_flow.n_12m_cumulative_pd = pd_record_12.n_cumulative_default_prob

                            cash_flow.save()

            except Exception as e:
                print(f"Error updating account {cash_flow.v_account_number}: {e}")

        # Using ThreadPoolExecutor for multi-threading
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_cash_flow, cash_flow) for cash_flow in cash_flows]

            for future in as_completed(futures):
                # Check for exceptions raised during execution
                try:
                    future.result()
                except Exception as exc:
                    print(f"Error occurred in thread: {exc}")
                    return 0  # Return 0 if any thread encounters an error

        print(f"Updated {cash_flows.count()} records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}")
        return 1  # Return 1 on successful completion

    except Exception as e:
        print(f"Error updating cash flow for fic_mis_date {fic_mis_date}: {e}")
        return 0  # Return 0 in case of any exception

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



