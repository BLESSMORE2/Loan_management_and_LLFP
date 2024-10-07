import concurrent.futures
from django.db import transaction
from ..models import *
from .save_log import save_log

# Function to handle insertion of records in chunks
def insert_records_chunk(records_chunk):
    """
    Inserts a chunk of records into FCT_Stage_Determination.
    """
    inserted_count = 0
    with transaction.atomic():
        bulk_records = []
        for record in records_chunk:
            try:
                bulk_records.append(FCT_Stage_Determination(
                    fic_mis_date=record.fic_mis_date,
                    n_account_number=record.v_account_number,
                    n_curr_interest_rate=record.n_curr_interest_rate,
                    n_effective_interest_rate=record.n_effective_interest_rate,
                    n_accrued_interest=record.n_accrued_interest,
                    n_rate_chg_min=record.n_interest_changing_rate,
                    n_accrual_basis_code=record.v_day_count_ind,
                    n_pd_percent=record.n_pd_percent,
                    n_lgd_percent=record.n_lgd_percent,
                    d_acct_start_date=record.d_start_date,
                    d_last_payment_date=record.d_last_payment_date,
                    d_next_payment_date=record.d_next_payment_date,
                    d_maturity_date=record.d_maturity_date,
                    v_ccy_code=record.v_ccy_code,
                    n_eop_prin_bal=record.n_eop_curr_prin_bal,
                    n_carrying_amount_ncy=record.n_eop_bal,
                    n_collateral_amount=record.n_collateral_amount,
                    n_delinquent_days=record.n_delinquent_days,
                    v_amrt_repayment_type=record.v_amrt_repayment_type,
                    v_amrt_term_unit=record.v_amrt_term_unit,
                    n_prod_code=record.v_prod_code,
                    n_cust_ref_code=record.v_cust_ref_code,
                    n_loan_type=record.v_loan_type,
                    n_acct_rating_movement=record.v_acct_rating_movement,
                    n_credit_rating_code=record.v_credit_rating_code,
                    n_org_credit_score=record.v_org_credit_score,
                    n_curr_credit_score=record.n_curr_credit_score,
                ))
                inserted_count += 1
            except Exception as e:
                save_log('insert_records_chunk', 'ERROR', f"Error inserting record for account {record.v_account_number}: {e}")
        FCT_Stage_Determination.objects.bulk_create(bulk_records)

    return inserted_count

def insert_fct_stage(fic_mis_date, chunk_size=100):
    """
    Inserts data into FCT_Stage_Determination table from Ldn_Financial_Instrument based on the given fic_mis_date.
    Deletes existing records for the same fic_mis_date before inserting. Uses multi-threading to process records in chunks.
    :param fic_mis_date: The date to filter records in both FCT_Stage_Determination and Ldn_Financial_Instrument.
    :param chunk_size: The size of the data chunks to process concurrently.
    """
    try:
        # Step 1: Delete existing records for the given fic_mis_date
        if FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date).exists():
            FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date).delete()
            save_log('insert_fct_stage', 'INFO', f"Deleted existing records for {fic_mis_date} in FCT_Stage_Determination.")

        # Step 2: Fetch data from Ldn_Financial_Instrument for the given fic_mis_date
        records = list(Ldn_Financial_Instrument.objects.filter(fic_mis_date=fic_mis_date))
        total_records = len(records)
        save_log('insert_fct_stage', 'INFO', f"Total records fetched for {fic_mis_date}: {total_records}")

        if total_records == 0:
            save_log('insert_fct_stage', 'INFO', f"No records found for {fic_mis_date} in Ldn_Financial_Instrument.")
            return '0'  # Return '0' if no records are found

        # Step 3: Split the records into chunks for multi-threading
        record_chunks = [records[i:i + chunk_size] for i in range(0, total_records, chunk_size)]

        # Step 4: Use multi-threading to insert records concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(insert_records_chunk, chunk) for chunk in record_chunks]

            total_inserted_count = 0
            for future in concurrent.futures.as_completed(futures):
                try:
                    chunk_inserted_count = future.result()
                    total_inserted_count += chunk_inserted_count
                except Exception as exc:
                    save_log('insert_fct_stage', 'ERROR', f"Error occurred during record insertion: {exc}")
                    return '0'  # Return '0' if any thread encounters an error

        save_log('insert_fct_stage', 'INFO', f"Successfully inserted {total_inserted_count} records for {fic_mis_date} into FCT_Stage_Determination.")
        return '1'  # Return '1' on successful completion

    except Exception as e:
        save_log('insert_fct_stage', 'ERROR', f"Error during FCT_Stage_Determination insertion process: {e}")
        return '0'  # Return '0' in case of any exception
