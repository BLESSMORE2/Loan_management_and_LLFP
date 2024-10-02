from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from ..models import FCT_Stage_Determination, FCT_Reporting_Lines, Dim_Run

# Helper function to split data into chunks
def chunk_data(data, chunk_size):
    """Split data into chunks of size chunk_size."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

def process_chunk(stage_determination_chunk, last_run_skey):
    """Process a chunk of FCT_Stage_Determination records and perform bulk insert into FCT_Reporting_Lines."""
    reporting_lines_records = []

    # Map data from FCT_Stage_Determination to FCT_Reporting_Lines for the chunk
    for record in stage_determination_chunk:
        reporting_line = FCT_Reporting_Lines(
            n_run_key=last_run_skey,  # Use last_run_skey from Dim_Run for n_run_key
            fic_mis_date=record.fic_mis_date,
            n_account_number=record.n_account_number,
            d_acct_start_date=record.d_acct_start_date,
            d_last_payment_date=record.d_last_payment_date,
            d_next_payment_date=record.d_next_payment_date,
            d_maturity_date=record.d_maturity_date,
            n_acct_classification=record.n_acct_classification,
            n_cust_ref_code=record.n_cust_ref_code,
            n_partner_name=record.n_partner_name,
            n_party_type=record.n_party_type,
            n_accrual_basis_code=record.n_accrual_basis_code,
            n_curr_interest_rate=record.n_curr_interest_rate,
            n_effective_interest_rate=record.n_effective_interest_rate,
            v_interest_freq_unit=record.v_interest_freq_unit,
            v_interest_method=record.v_interest_method,
            n_accrued_interest=record.n_accrued_interest,
            n_rate_chg_min=record.n_rate_chg_min,
            n_carrying_amount_ncy=record.n_carrying_amount_ncy,
            n_exposure_at_default_ncy=record.n_exposure_at_default,
            n_lgd_percent=record.n_lgd_percent,
            n_pd_percent=record.n_pd_percent,
            n_twelve_months_orig_pd=record.n_twelve_months_orig_pd,
            n_lifetime_orig_pd=record.n_lifetime_orig_pd,
            n_twelve_months_pd=record.n_twelve_months_pd,
            n_lifetime_pd=record.n_lifetime_pd,
            n_pd_term_structure_skey=record.n_pd_term_structure_skey,
            n_pd_term_structure_name=record.n_pd_term_structure_name,
            n_pd_term_structure_desc=record.n_pd_term_structure_desc,
            n_12m_pd_change=record.n_12m_pd_change,
            v_amrt_repayment_type=record.v_amrt_repayment_type,
            n_remain_no_of_pmts=record.n_remain_no_of_pmts,
            n_amrt_term=record.n_amrt_term,
            v_amrt_term_unit=record.v_amrt_term_unit,
            v_ccy_code=record.v_ccy_code,
            n_delinquent_days=record.n_delinquent_days,
            n_delq_band_code=record.n_delq_band_code,
            n_stage_descr=record.n_stage_descr,
            n_curr_ifrs_stage_skey=record.n_curr_ifrs_stage_skey,
            n_prev_ifrs_stage_skey=record.n_prev_ifrs_stage_skey,
            d_cooling_start_date=record.d_cooling_start_date,
            n_target_ifrs_stage_skey=record.n_target_ifrs_stage_skey,
            n_in_cooling_period_flag=record.n_in_cooling_period_flag,
            n_cooling_period_duration=record.n_cooling_period_duration,
            n_country=record.n_country,
            n_segment_skey=record.n_segment_skey,
            n_prod_segment=record.n_prod_segment,
            n_prod_code=record.n_prod_code,
            n_prod_name=record.n_prod_name,
            n_prod_type=record.n_prod_type,
            n_prod_desc=record.n_prod_desc,
            n_credit_rating_code=record.n_credit_rating_code,
            n_org_credit_score=record.n_org_credit_score,
            n_curr_credit_score=record.n_curr_credit_score,
            n_acct_rating_movement=record.n_acct_rating_movement,
            n_party_rating_movement=record.n_party_rating_movement,
            n_conditionally_cancel_flag=record.n_conditionally_cancel_flag,
            n_collateral_amount=record.n_collateral_amount,
            n_loan_type=record.n_loan_type
        )
        reporting_lines_records.append(reporting_line)

    # Perform bulk insert for the current chunk
    with transaction.atomic():
        FCT_Reporting_Lines.objects.bulk_create(reporting_lines_records)

def populate_fct_reporting_lines(mis_date, chunk_size=1000):
    """
    Populate data in FCT_Reporting_Lines from FCT_Stage_Determination for the given mis_date.
    Use last_run_skey from Dim_Run for n_run_key. Multi-threaded with bulk insert.
    :param mis_date: The fic_mis_date used to filter records in FCT_Stage_Determination.
    :param chunk_size: The size of data chunks to process in each thread.
    """
    try:
        # Fetch the last_run_skey from Dim_Run
        dim_run = Dim_Run.objects.latest('latest_run_skey')
        last_run_skey = dim_run.latest_run_skey

        # Fetch records from FCT_Stage_Determination where fic_mis_date matches the provided date
        stage_determination_records = list(FCT_Stage_Determination.objects.filter(fic_mis_date=mis_date))

        # Split the records into chunks
        chunks = list(chunk_data(stage_determination_records, chunk_size))

        # Use ThreadPoolExecutor to process each chunk in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_chunk, chunk, last_run_skey) for chunk in chunks]

            # Wait for all threads to complete
            for future in futures:
                future.result()

        print(f"Successfully populated FCT_Reporting_Lines for {len(stage_determination_records)} records.")

    except Exception as e:
        print(f"Error populating FCT_Reporting_Lines: {e}")
