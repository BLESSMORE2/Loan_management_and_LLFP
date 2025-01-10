from django.db import connection, transaction
from .save_log import save_log

def insert_fct_stage(fic_mis_date):
    """
    Inserts data into FCT_Stage_Determination table from Ldn_Financial_Instrument based on the given fic_mis_date.
    Deletes existing records for the same fic_mis_date before inserting. Uses a set-based SQL approach.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Step 1: Delete existing records for the given fic_mis_date
            cursor.execute("""
                DELETE FROM fct_stage_determination
                WHERE fic_mis_date = %s;
            """, [fic_mis_date])
            save_log('insert_fct_stage', 'INFO', f"Deleted existing records for {fic_mis_date} in FCT_Stage_Determination.", status='SUCCESS')

            # Step 2: Insert new records from Ldn_Financial_Instrument
            cursor.execute("""
                INSERT INTO fct_stage_determination (
                    fic_mis_date,
                    n_account_number,
                    n_curr_interest_rate,
                    n_effective_interest_rate,
                    n_accrued_interest,
                    n_rate_chg_min,
                    n_accrual_basis_code,
                    n_pd_percent,
                    n_lgd_percent,
                    d_acct_start_date,
                    d_last_payment_date,
                    d_next_payment_date,
                    d_maturity_date,
                    v_ccy_code,
                    n_eop_prin_bal,
                    n_carrying_amount_ncy,
                    n_collateral_amount,
                    n_delinquent_days,
                    v_amrt_repayment_type,
                    v_amrt_term_unit,
                    n_prod_code,
                    n_cust_ref_code,
                    n_loan_type,
                    n_acct_rating_movement,
                    n_credit_rating_code,
                    n_org_credit_score,
                    n_curr_credit_score
                )
                SELECT 
                    fic_mis_date,
                    v_account_number,
                    n_curr_interest_rate,
                    n_effective_interest_rate,
                    n_accrued_interest,
                    n_interest_changing_rate,
                    v_day_count_ind,
                    n_pd_percent,
                    n_lgd_percent,
                    d_start_date,
                    d_last_payment_date,
                    d_next_payment_date,
                    d_maturity_date,
                    v_ccy_code,
                    n_eop_curr_prin_bal,
                    n_eop_bal,
                    n_collateral_amount,
                    n_delinquent_days,
                    v_amrt_repayment_type,
                    v_amrt_term_unit,
                    v_prod_code,
                    v_cust_ref_code,
                    v_loan_type,
                    v_acct_rating_movement,
                    v_credit_rating_code,
                    v_org_credit_score,
                    v_curr_credit_score
                FROM ldn_financial_instrument
                WHERE fic_mis_date = %s;
            """, [fic_mis_date])

            # Log success
            save_log('insert_fct_stage', 'INFO', f"Records for {fic_mis_date} inserted successfully into FCT_Stage_Determination.", status='SUCCESS')
            return '1'  # Return '1' on successful completion

    except Exception as e:
        save_log('insert_fct_stage', 'ERROR', f"Error during FCT_Stage_Determination insertion process: {e}", status='FAILURE')
        return '0'  # Return '0' in case of any exception


# import concurrent.futures
# from django.db import transaction
# from ..models import *
# from .save_log import save_log

# # Function to handle bulk insertion of records in chunks
# def insert_records_chunk(records_chunk):
#     # Prepare list for bulk insert
#     bulk_records = []
#     for record in records_chunk:
#         bulk_records.append(FCT_Stage_Determination(
#             fic_mis_date=record.fic_mis_date,
#             n_account_number=record.v_account_number,
#             n_curr_interest_rate=record.n_curr_interest_rate,
#             n_effective_interest_rate=record.n_effective_interest_rate,
#             n_accrued_interest=record.n_accrued_interest,
#             n_rate_chg_min=record.n_interest_changing_rate,
#             n_accrual_basis_code=record.v_day_count_ind,
#             n_pd_percent=record.n_pd_percent,
#             n_lgd_percent=record.n_lgd_percent,
#             d_acct_start_date=record.d_start_date,
#             d_last_payment_date=record.d_last_payment_date,
#             d_next_payment_date=record.d_next_payment_date,
#             d_maturity_date=record.d_maturity_date,
#             v_ccy_code=record.v_ccy_code,
#             n_eop_prin_bal=record.n_eop_curr_prin_bal,
#             n_carrying_amount_ncy=record.n_eop_bal,
#             n_collateral_amount=record.n_collateral_amount,
#             n_delinquent_days=record.n_delinquent_days,
#             v_amrt_repayment_type=record.v_amrt_repayment_type,
#             v_amrt_term_unit=record.v_amrt_term_unit,
#             n_prod_code=record.v_prod_code,
#             n_cust_ref_code=record.v_cust_ref_code,
#             n_loan_type=record.v_loan_type,
#             n_acct_rating_movement=record.v_acct_rating_movement,
#             n_credit_rating_code=record.v_credit_rating_code,
#             n_org_credit_score=record.v_org_credit_score,
#             n_curr_credit_score=record.v_curr_credit_score,
#         ))

#     # Perform bulk insert
#     try:
#         with transaction.atomic():
#             FCT_Stage_Determination.objects.bulk_create(bulk_records)
#     except Exception as e:
#         save_log('insert_records_chunk', 'ERROR', f"Error inserting records: {e}", status='FAILURE')

            
# def insert_fct_stage(fic_mis_date, chunk_size=100):
#     """
#     Inserts data into FCT_Stage_Determination table from Ldn_Financial_Instrument based on the given fic_mis_date.
#     Deletes existing records for the same fic_mis_date before inserting. Uses multi-threading to process records in chunks.
#     :param fic_mis_date: The date to filter records in both FCT_Stage_Determination and Ldn_Financial_Instrument.
#     :param chunk_size: The size of the data chunks to process concurrently.
#     """
#     try:
#         # Step 1: Check if data for the given fic_mis_date exists in FCT_Stage_Determination
#         if FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date).exists():
#             # If exists, delete the records
#             FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date).delete()
#             save_log('insert_fct_stage', 'INFO', f"Deleted existing records for {fic_mis_date} in FCT_Stage_Determination.", status='SUCCESS')

#         # Step 2: Fetch data from Ldn_Financial_Instrument for the given fic_mis_date
#         records = list(Ldn_Financial_Instrument.objects.filter(fic_mis_date=fic_mis_date))

#         # Log the number of records fetched
#         total_records = len(records)
#         save_log('insert_fct_stage', 'INFO', f"Total records fetched for {fic_mis_date}: {total_records}", status='SUCCESS')

#         if total_records == 0:
#             save_log('insert_fct_stage', 'INFO', f"No records found for {fic_mis_date} in Ldn_Financial_Instrument.", status='SUCCESS')
#             return '0'  # Return '0' if no records are found

#         # Step 3: Split the records into chunks for multi-threading
#         record_chunks = [records[i:i + chunk_size] for i in range(0, len(records), chunk_size)]

#         # Step 4: Use multi-threading with a max of 4 workers to insert records concurrently
#         with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
#             # Map the chunks to the insert_records_chunk function
#             futures = [executor.submit(insert_records_chunk, chunk) for chunk in record_chunks]

#             # Process the results of each chunk
#             for future in futures:
#                 try:
#                     future.result()  # Raises any exception encountered during execution
#                 except Exception as exc:
#                     save_log('insert_fct_stage', 'ERROR', f"Error occurred during record insertion: {exc}", status='FAILURE')
#                     return '0'  # Return '0' if any thread encounters an error

#         save_log('insert_fct_stage', 'INFO', f"{total_records} records for {fic_mis_date} inserted successfully into FCT_Stage_Determination.", status='SUCCESS')
#         return '1'  # Return '1' on successful completion

#     except Exception as e:
#         save_log('insert_fct_stage', 'ERROR', f"Error during FCT_Stage_Determination insertion process: {e}", status='FAILURE')
#         return '0'  # Return '0' in case of any exception
