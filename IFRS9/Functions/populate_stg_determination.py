import concurrent.futures
from django.db import transaction
from ..models import *

# Function to handle insertion of records in chunks
def insert_records_chunk(records_chunk):
    with transaction.atomic():
        for record in records_chunk:
            try:
                FCT_Stage_Determination.objects.create (
                    fic_mis_date=record.fic_mis_date,
                    n_account_number=record.v_account_number,
                    n_curr_interest_rate=record.n_curr_interest_rate,
                    n_effective_interest_rate=record.n_effective_interest_rate,
                    n_accrued_interest=record.n_accrued_interest,
                    n_twelve_months_pd=record.n_pd_percent,
                    n_lgd_percent=record.n_lgd_percent,
                    d_acct_start_date=record.d_start_date,
                    d_last_payment_date=record.d_last_payment_date,
                    d_next_payment_date=record.d_next_payment_date,
                    d_maturity_date=record.d_maturity_date,
                    v_ccy_code=record.v_ccy_code,
                    n_eop_prin_bal=record.n_eop_curr_prin_bal,
                    n_exposure_at_default=record.n_eop_bal,
                    n_collateral_amount=record.n_collateral_amount,
                    n_delinquent_days=record.n_delinquent_days,
                    v_amrt_repayment_type=record.v_amrt_repayment_type,
                    v_amrt_term_unit=record.v_amrt_term_unit,
                    n_prod_code = record.v_prod_code,
                    n_cust_ref_code=record.v_cust_ref_code,
                    n_loan_type=record.v_loan_type,
                    n_credit_rating_code=record.v_credit_rating_code,
                    n_org_credit_score=record.v_org_credit_score,
                    n_curr_credit_score=record.v_curr_credit_score,
                )
            except Exception as e:
                print(f"Error inserting record: {e}")

            
def insert_fct_stage(fic_mis_date, chunk_size=100):
    # Step 1: Check if data for the given fic_mis_date exists in FCT_Stage_Determination
    if FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date).exists():
        # If exists, delete the records
        FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date).delete()

    # Step 2: Fetch data from Ldn_Financial_Instrument for the given fic_mis_date
    records = list(Ldn_Financial_Instrument.objects.filter(fic_mis_date=fic_mis_date))

    # Print the number of records fetched
    total_records = len(records)
    print(f"Total records fetched for {fic_mis_date}: {total_records}")

    # Step 3: Split the records into chunks for multi-threading
    record_chunks = [records[i:i + chunk_size] for i in range(0, len(records), chunk_size)]

    # Step 4: Use multi-threading with a max of 4 workers to insert records concurrently
    if record_chunks:  # Ensure there are records to process
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(insert_records_chunk, record_chunks)

        print(f"{total_records} records for {fic_mis_date} inserted successfully into FCT_Stage_Determination.")
    else:
        print(f"No records found for {fic_mis_date} in Ldn_Financial_Instrument.")