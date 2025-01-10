import time
from concurrent.futures import ThreadPoolExecutor
from django import db
from django.db import connection, transaction, DatabaseError
from ..models import Dim_Run
from .save_log import save_log

def get_latest_run_skey():
    """Retrieve the latest_run_skey from Dim_Run table."""
    try:
        run_record = Dim_Run.objects.only('latest_run_skey').first()
        if not run_record:
            save_log('get_latest_run_skey', 'ERROR', "No run key is available in the Dim_Run table.")
            return None
        return run_record.latest_run_skey
    except Exception as e:
        save_log('get_latest_run_skey', 'ERROR', str(e))
        return None

def get_buckets_for_12_months(v_amrt_term_unit):
    """Returns the number of buckets required to reach 12 months based on the amortization term unit."""
    term_unit_to_buckets = {
        'M': 12,
        'Q': 4,
        'H': 2,
        'Y': 1
    }
    return term_unit_to_buckets.get(v_amrt_term_unit, 12)

def process_batch_for_term_structure(amrt_unit, fic_mis_date, run_skey, months_to_12m, bucket_limit, term_structure_id, batch_accounts, retries=3, retry_delay=5):
    """Process a single batch of accounts for a specific term structure with retry logic."""
    attempt = 0
    while attempt < retries:
        try:
            db.close_old_connections()  # Ensure fresh connection
            with connection.cursor() as cursor, transaction.atomic():
                # Ratings-based update
                cursor.execute("""
                    UPDATE fsi_financial_cash_flow_cal AS cf
                    JOIN fct_stage_determination AS sd
                      ON sd.fic_mis_date = cf.fic_mis_date
                     AND sd.n_account_number = cf.v_account_number
                     AND sd.v_amrt_term_unit = %s
                    JOIN fsi_pd_interpolated AS pd
                      ON pd.fic_mis_date <= sd.fic_mis_date
                     AND pd.v_pd_term_structure_id = sd.n_pd_term_structure_skey
                     AND pd.v_pd_term_structure_type = 'R'
                     AND pd.v_int_rating_code = sd.n_credit_rating_code
                     AND pd.v_cash_flow_bucket_id = cf.n_cash_flow_bucket_id
                    SET
                      cf.n_cumulative_loss_rate = pd.n_cumulative_default_prob * sd.n_lgd_percent,
                      cf.n_cumulative_impaired_prob = pd.n_cumulative_default_prob
                    WHERE cf.fic_mis_date = %s 
                      AND cf.n_run_skey = %s
                      AND sd.n_pd_term_structure_skey = %s
                      AND sd.n_account_number IN %s;
                """, [amrt_unit, fic_mis_date, run_skey, term_structure_id, tuple(batch_accounts)])

                # Delinquency-based update
                cursor.execute("""
                    UPDATE fsi_financial_cash_flow_cal AS cf
                    JOIN fct_stage_determination AS sd
                      ON sd.fic_mis_date = cf.fic_mis_date
                     AND sd.n_account_number = cf.v_account_number
                     AND sd.v_amrt_term_unit = %s
                    JOIN fsi_pd_interpolated AS pd
                      ON pd.fic_mis_date <= sd.fic_mis_date
                     AND pd.v_pd_term_structure_id = sd.n_pd_term_structure_skey
                     AND pd.v_pd_term_structure_type = 'D'
                     AND pd.v_delq_band_code = sd.n_delq_band_code
                     AND pd.v_cash_flow_bucket_id = cf.n_cash_flow_bucket_id
                    SET
                      cf.n_cumulative_loss_rate = pd.n_cumulative_default_prob * sd.n_lgd_percent,
                      cf.n_cumulative_impaired_prob = pd.n_cumulative_default_prob
                    WHERE cf.fic_mis_date = %s 
                      AND cf.n_run_skey = %s
                      AND sd.n_pd_term_structure_skey = %s
                      AND sd.n_account_number IN %s;
                """, [amrt_unit, fic_mis_date, run_skey, term_structure_id, tuple(batch_accounts)])

                # 12-month PD direct update
                cursor.execute("""
                    UPDATE fsi_financial_cash_flow_cal AS cf
                    JOIN fct_stage_determination AS sd
                      ON sd.fic_mis_date = cf.fic_mis_date
                     AND sd.n_account_number = cf.v_account_number
                     AND sd.v_amrt_term_unit = %s
                    SET cf.n_12m_cumulative_pd = cf.n_cumulative_impaired_prob
                    WHERE cf.fic_mis_date = %s 
                      AND cf.n_run_skey = %s 
                      AND cf.n_cash_flow_bucket_id <= %s
                      AND sd.n_pd_term_structure_skey = %s
                      AND sd.n_account_number IN %s;
                """, [amrt_unit, fic_mis_date, run_skey, months_to_12m, term_structure_id, tuple(batch_accounts)])

                # 12-month PD beyond update --Delinquency-based update
                cursor.execute("""
                    UPDATE fsi_financial_cash_flow_cal AS cf
                    JOIN fct_stage_determination AS sd
                      ON sd.fic_mis_date = cf.fic_mis_date
                     AND sd.n_account_number = cf.v_account_number
                     AND sd.v_amrt_term_unit = %s   
                    JOIN fsi_pd_interpolated AS pd12
                      ON pd12.fic_mis_date <= sd.fic_mis_date
                    AND pd12.v_pd_term_structure_type = 'D'
                     AND pd12.v_pd_term_structure_id = sd.n_pd_term_structure_skey
                    AND pd12.v_delq_band_code = sd.n_delq_band_code
                     AND pd12.v_cash_flow_bucket_id = %s
                    SET cf.n_12m_cumulative_pd = pd12.n_cumulative_default_prob
                    WHERE cf.fic_mis_date = %s 
                      AND cf.n_run_skey = %s 
                      AND cf.n_cash_flow_bucket_id > %s
                      AND sd.n_pd_term_structure_skey = %s
                      AND sd.n_account_number IN %s;
                """, [amrt_unit, months_to_12m, fic_mis_date, run_skey, months_to_12m, term_structure_id, tuple(batch_accounts)])

                # 12-month PD beyond update --Ratind-based update
                cursor.execute("""
                    UPDATE fsi_financial_cash_flow_cal AS cf
                    JOIN fct_stage_determination AS sd
                      ON sd.fic_mis_date = cf.fic_mis_date
                     AND sd.n_account_number = cf.v_account_number
                     AND sd.v_amrt_term_unit = %s      
                    JOIN fsi_pd_interpolated AS pd12
                      ON pd12.fic_mis_date <= sd.fic_mis_date
                    AND pd12.v_pd_term_structure_type = 'R'
                     AND pd12.v_pd_term_structure_id = sd.n_pd_term_structure_skey   
                    AND pd12.v_int_rating_code = sd.n_credit_rating_code
                     AND pd12.v_cash_flow_bucket_id = %s     
                    SET cf.n_12m_cumulative_pd = pd12.n_cumulative_default_prob
                    WHERE cf.fic_mis_date = %s 
                      AND cf.n_run_skey = %s 
                      AND cf.n_cash_flow_bucket_id > %s
                      AND sd.n_pd_term_structure_skey = %s
                      AND sd.n_account_number IN %s;
                """, [amrt_unit, months_to_12m, fic_mis_date, run_skey, months_to_12m, term_structure_id, tuple(batch_accounts)])


            return  # Successful execution exits the function
        except DatabaseError as e:
            if "Lock wait timeout" in str(e):
                attempt += 1
                time.sleep(retry_delay)
            else:
                raise
    raise Exception(f"Failed after {retries} retries due to lock timeouts.")

def update_cash_flow_with_pd_buckets(fic_mis_date, batch_size=5000, max_workers=4):
    """
    Updates cash flow records with PD bucket information in batches of accounts using multithreading.
    """
    try:
        run_skey = get_latest_run_skey()
        if not run_skey:
            save_log('update_cash_flow_with_pd_buckets', 'ERROR', "No valid run_skey found.")
            return 0

        amrt_unit = 'M'
        months_to_12m = get_buckets_for_12_months(amrt_unit)

        # Retrieve distinct account numbers and their term structures
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT n_account_number, n_pd_term_structure_skey 
                FROM fct_stage_determination 
                WHERE fic_mis_date = %s;
            """, [fic_mis_date])
            rows = cursor.fetchall()

        # Group accounts by term_structure_id
        term_structure_map = {}
        for account, term_structure_id in rows:
            term_structure_map.setdefault(term_structure_id, []).append(account)

        futures = []
        executor = ThreadPoolExecutor(max_workers=max_workers)

        # Schedule tasks for each term structure in batches
        for term_structure_id, accounts in term_structure_map.items():
            bucket_limit = months_to_12m  # Simplified; adjust if needed
            for i in range(0, len(accounts), batch_size):
                batch_accounts = accounts[i:i + batch_size]
                if not batch_accounts:
                    continue
                futures.append(
                    executor.submit(
                        process_batch_for_term_structure,
                        amrt_unit,
                        fic_mis_date,
                        run_skey,
                        months_to_12m,
                        bucket_limit,
                        term_structure_id,
                        batch_accounts
                    )
                )

        for future in futures:
            # This will re-raise any exceptions from worker threads
            future.result()

        executor.shutdown()

        save_log('update_cash_flow_with_pd_buckets', 'INFO',
                 f"Set-based PD updates completed for fic_mis_date={fic_mis_date}, run_skey={run_skey}.")
        return 1

    except Exception as e:
        save_log('update_cash_flow_with_pd_buckets', 'ERROR',
                 f"Error updating PD buckets for fic_mis_date={fic_mis_date}: {e}")
        return 0


# from django.db import connection, transaction
# from ..models import Dim_Run
# from .save_log import save_log

# def get_latest_run_skey():
#     """Retrieve the latest_run_skey from Dim_Run table."""
#     try:
#         run_record = Dim_Run.objects.only('latest_run_skey').first()
#         if not run_record:
#             save_log('get_latest_run_skey', 'ERROR', "No run key is available in the Dim_Run table.")
#             return None
#         return run_record.latest_run_skey
#     except Exception as e:
#         save_log('get_latest_run_skey', 'ERROR', str(e))
#         return None

# def get_buckets_for_12_months(v_amrt_term_unit):
#     """Returns the number of buckets required to reach 12 months based on the amortization term unit."""
#     term_unit_to_buckets = {
#         'M': 12,
#         'Q': 4,
#         'H': 2,
#         'Y': 1
#     }
#     return term_unit_to_buckets.get(v_amrt_term_unit, 12)

# def update_cash_flow_with_pd_buckets(fic_mis_date, batch_size=3000):
#     """
#     Updates cash flow records with PD bucket information in batches of accounts.
#     Processes accounts in groups of `batch_size` to avoid updating all at once.
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         if not run_skey:
#             save_log('update_cash_flow_with_pd_buckets', 'ERROR', "No valid run_skey found.")
#             return 0

#         amrt_unit = 'M'
#         months_to_12m = get_buckets_for_12_months(amrt_unit)

#         with connection.cursor() as cursor:
#             # Retrieve distinct account numbers for the given fic_mis_date
#             cursor.execute("""
#                 SELECT DISTINCT n_account_number 
#                 FROM fct_stage_determination 
#                 WHERE fic_mis_date = %s;
#             """, [fic_mis_date])
#             accounts = [row[0] for row in cursor.fetchall()]

#         # Process accounts in batches
#         for i in range(0, len(accounts), batch_size):
#             batch_accounts = accounts[i:i + batch_size]
#             if not batch_accounts:
#                 continue

#             # Use a transaction for each batch
#             with connection.cursor() as cursor, transaction.atomic():
#                 # Ratings-based update for current batch
#                 cursor.execute("""
#                     UPDATE fsi_financial_cash_flow_cal AS cf
#                     JOIN fct_stage_determination AS sd
#                       ON sd.fic_mis_date = cf.fic_mis_date
#                      AND sd.n_account_number = cf.v_account_number
#                      AND sd.v_amrt_term_unit = %s
#                     JOIN fsi_pd_interpolated AS pd
#                       ON pd.fic_mis_date <= sd.fic_mis_date
#                      AND pd.v_pd_term_structure_id = sd.n_pd_term_structure_skey
#                      AND pd.v_pd_term_structure_type = 'R'
#                      AND pd.v_int_rating_code = sd.n_credit_rating_code
#                      AND pd.v_cash_flow_bucket_id = cf.n_cash_flow_bucket_id
#                     SET
#                       cf.n_cumulative_loss_rate = pd.n_cumulative_default_prob * sd.n_lgd_percent,
#                       cf.n_cumulative_impaired_prob = pd.n_cumulative_default_prob
#                     WHERE cf.fic_mis_date = %s 
#                       AND cf.n_run_skey = %s
#                       AND sd.n_account_number IN %s;
#                 """, [amrt_unit, fic_mis_date, run_skey, tuple(batch_accounts)])

#                 # Delinquency-based update for current batch
#                 cursor.execute("""
#                     UPDATE fsi_financial_cash_flow_cal AS cf
#                     JOIN fct_stage_determination AS sd
#                       ON sd.fic_mis_date = cf.fic_mis_date
#                      AND sd.n_account_number = cf.v_account_number
#                      AND sd.v_amrt_term_unit = %s
#                     JOIN fsi_pd_interpolated AS pd
#                       ON pd.fic_mis_date <= sd.fic_mis_date
#                      AND pd.v_pd_term_structure_id = sd.n_pd_term_structure_skey
#                      AND pd.v_pd_term_structure_type = 'D'
#                      AND pd.v_delq_band_code = sd.n_delq_band_code
#                      AND pd.v_cash_flow_bucket_id = cf.n_cash_flow_bucket_id
#                     SET
#                       cf.n_cumulative_loss_rate = pd.n_cumulative_default_prob * sd.n_lgd_percent,
#                       cf.n_cumulative_impaired_prob = pd.n_cumulative_default_prob
#                     WHERE cf.fic_mis_date = %s 
#                       AND cf.n_run_skey = %s
#                       AND sd.n_account_number IN %s;
#                 """, [amrt_unit, fic_mis_date, run_skey, tuple(batch_accounts)])

#                 # 12-month PD direct update (bucket <= months_to_12m) for current batch
#                 cursor.execute("""
#                     UPDATE fsi_financial_cash_flow_cal AS cf
#                     JOIN fct_stage_determination AS sd
#                       ON sd.fic_mis_date = cf.fic_mis_date
#                      AND sd.n_account_number = cf.v_account_number
#                      AND sd.v_amrt_term_unit = %s
#                     SET cf.n_12m_cumulative_pd = cf.n_cumulative_impaired_prob
#                     WHERE cf.fic_mis_date = %s 
#                       AND cf.n_run_skey = %s 
#                       AND cf.n_cash_flow_bucket_id <= %s
#                       AND sd.n_account_number IN %s;
#                 """, [amrt_unit, fic_mis_date, run_skey, months_to_12m, tuple(batch_accounts)])

#                 # 12-month PD beyond update (bucket > months_to_12m) for current batch
#                 cursor.execute("""
#                     UPDATE fsi_financial_cash_flow_cal AS cf
#                     JOIN fct_stage_determination AS sd
#                       ON sd.fic_mis_date = cf.fic_mis_date
#                      AND sd.n_account_number = cf.v_account_number
#                      AND sd.v_amrt_term_unit = %s
#                     JOIN fsi_pd_interpolated AS pd12
#                       ON pd12.fic_mis_date <= sd.fic_mis_date
#                      AND pd12.v_pd_term_structure_id = sd.n_pd_term_structure_skey
#                      AND pd12.v_cash_flow_bucket_id = %s
#                     SET cf.n_12m_cumulative_pd = pd12.n_cumulative_default_prob
#                     WHERE cf.fic_mis_date = %s 
#                       AND cf.n_run_skey = %s 
#                       AND cf.n_cash_flow_bucket_id > %s
#                       AND sd.n_account_number IN %s;
#                 """, [amrt_unit, months_to_12m, fic_mis_date, run_skey, months_to_12m, tuple(batch_accounts)])

#         save_log('update_cash_flow_with_pd_buckets', 'INFO',
#                  f"Set-based PD updates completed for fic_mis_date={fic_mis_date}, run_skey={run_skey}.")
#         return 1

#     except Exception as e:
#         save_log('update_cash_flow_with_pd_buckets', 'ERROR',
#                  f"Error updating PD buckets for fic_mis_date={fic_mis_date}: {e}")
#         return 0


# from django.db import connection, transaction
# from ..models import Dim_Run
# from .save_log import save_log

# def get_latest_run_skey():
#     """
#     Retrieve the latest_run_skey from Dim_Run table.
#     """
#     try:
#         run_record = Dim_Run.objects.only('latest_run_skey').first()
#         if not run_record:
#             save_log('get_latest_run_skey', 'ERROR', "No run key is available in the Dim_Run table.")
#             return None
#         return run_record.latest_run_skey
#     except Exception as e:
#         save_log('get_latest_run_skey', 'ERROR', str(e))
#         return None

# def get_buckets_for_12_months(v_amrt_term_unit):
#     """
#     Returns the number of buckets required to reach 12 months based on the amortization term unit.
#     """
#     term_unit_to_buckets = {
#         'M': 12,
#         'Q': 4,
#         'H': 2,
#         'Y': 1
#     }
#     return term_unit_to_buckets.get(v_amrt_term_unit, 12)

# def update_cash_flow_with_pd_buckets(fic_mis_date):
#     """
#     Set-based approach to update cash flow records with PD bucket information.
#     This function performs multiple SQL updates to set:
#       - n_cumulative_loss_rate
#       - n_cumulative_impaired_prob
#       - n_12m_cumulative_pd
#     based on joined data from FCT_Stage_Determination and FSI_PD_Interpolated.
#     """
#     try:
#         run_skey = get_latest_run_skey()
#         if not run_skey:
#             save_log('update_cash_flow_with_pd_buckets', 'ERROR', "No valid run_skey found.")
#             return 0

#         # For simplicity, assume a single amortization unit 'M' (Monthly) for demonstration.
#         amrt_unit = 'M'
#         months_to_12m = get_buckets_for_12_months(amrt_unit)

#         with connection.cursor() as cursor, transaction.atomic():
#             # Ratings-based update
#             cursor.execute("""
#                 UPDATE fsi_financial_cash_flow_cal AS cf
#                 JOIN fct_stage_determination AS sd
#                   ON sd.fic_mis_date = cf.fic_mis_date
#                  AND sd.n_account_number = cf.v_account_number
#                  AND sd.v_amrt_term_unit = %s
#                 JOIN fsi_pd_interpolated AS pd
#                   ON pd.fic_mis_date <= sd.fic_mis_date
#                  AND pd.v_pd_term_structure_id = sd.n_pd_term_structure_skey
#                  AND pd.v_pd_term_structure_type = 'R'
#                  AND pd.v_int_rating_code = sd.n_credit_rating_code
#                  AND pd.v_cash_flow_bucket_id = cf.n_cash_flow_bucket_id
#                 SET
#                   cf.n_cumulative_loss_rate = pd.n_cumulative_default_prob * sd.n_lgd_percent,
#                   cf.n_cumulative_impaired_prob = pd.n_cumulative_default_prob
#                 WHERE cf.fic_mis_date = %s AND cf.n_run_skey = %s;
#             """, [amrt_unit, fic_mis_date, run_skey])

#             # Delinquency-based update
#             cursor.execute("""
#                 UPDATE fsi_financial_cash_flow_cal AS cf
#                 JOIN fct_stage_determination AS sd
#                   ON sd.fic_mis_date = cf.fic_mis_date
#                  AND sd.n_account_number = cf.v_account_number
#                  AND sd.v_amrt_term_unit = %s
#                 JOIN fsi_pd_interpolated AS pd
#                   ON pd.fic_mis_date <= sd.fic_mis_date
#                  AND pd.v_pd_term_structure_id = sd.n_pd_term_structure_skey
#                  AND pd.v_pd_term_structure_type = 'D'
#                  AND pd.v_delq_band_code = sd.n_delq_band_code
#                  AND pd.v_cash_flow_bucket_id = cf.n_cash_flow_bucket_id
#                 SET
#                   cf.n_cumulative_loss_rate = pd.n_cumulative_default_prob * sd.n_lgd_percent,
#                   cf.n_cumulative_impaired_prob = pd.n_cumulative_default_prob
#                 WHERE cf.fic_mis_date = %s AND cf.n_run_skey = %s;
#             """, [amrt_unit, fic_mis_date, run_skey])

#             # 12-month PD direct update (bucket <= months_to_12m)
#             cursor.execute("""
#                 UPDATE fsi_financial_cash_flow_cal AS cf
#                 JOIN fct_stage_determination AS sd
#                   ON sd.fic_mis_date = cf.fic_mis_date
#                  AND sd.n_account_number = cf.v_account_number
#                  AND sd.v_amrt_term_unit = %s
#                 SET cf.n_12m_cumulative_pd = cf.n_cumulative_impaired_prob
#                 WHERE cf.fic_mis_date = %s AND cf.n_run_skey = %s AND cf.n_cash_flow_bucket_id <= %s;
#             """, [amrt_unit, fic_mis_date, run_skey, months_to_12m])

#             # 12-month PD beyond update (bucket > months_to_12m)
#             cursor.execute("""
#                 UPDATE fsi_financial_cash_flow_cal AS cf
#                 JOIN fct_stage_determination AS sd
#                   ON sd.fic_mis_date = cf.fic_mis_date
#                  AND sd.n_account_number = cf.v_account_number
#                  AND sd.v_amrt_term_unit = %s
#                 JOIN fsi_pd_interpolated AS pd12
#                   ON pd12.fic_mis_date <= sd.fic_mis_date
#                  AND pd12.v_pd_term_structure_id = sd.n_pd_term_structure_skey
#                  AND pd12.v_cash_flow_bucket_id = %s
#                 SET cf.n_12m_cumulative_pd = pd12.n_cumulative_default_prob
#                 WHERE cf.fic_mis_date = %s AND cf.n_run_skey = %s AND cf.n_cash_flow_bucket_id > %s;
#             """, [amrt_unit, months_to_12m, fic_mis_date, run_skey, months_to_12m])

#         save_log('update_cash_flow_with_pd_buckets', 'INFO',
#                  f"Set-based PD updates completed for fic_mis_date={fic_mis_date}, run_skey={run_skey}.")
#         return 1

#     except Exception as e:
#         save_log('update_cash_flow_with_pd_buckets', 'ERROR',
#                  f"Error updating PD buckets for fic_mis_date={fic_mis_date}: {e}")
#         return 0




# from concurrent.futures import ThreadPoolExecutor, as_completed
# from django.db.models import Sum
# from ..models import FCT_Stage_Determination, fsi_Financial_Cash_Flow_Cal, FSI_PD_Interpolated, Dim_Run
# from .save_log import save_log

# def get_latest_run_skey():
#     """
#     Retrieve the latest_run_skey from Dim_Run table.
#     """
#     try:
#         run_record = Dim_Run.objects.first()
#         if not run_record:
#             raise ValueError("No run key is available in the Dim_Run table.")
#         return run_record.latest_run_skey
#     except Dim_Run.DoesNotExist:
#         raise ValueError("Dim_Run table is missing.")

# def update_cash_flow_with_pd_buckets(fic_mis_date, max_workers=5, batch_size=1000):
#     """
#     Updates cash flow records with PD buckets using bulk updates and multi-threading.
#     """
#     try:
#         n_run_skey = get_latest_run_skey()
#         cash_flows = fsi_Financial_Cash_Flow_Cal.objects.filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)

#         if not cash_flows.exists():
#             save_log('update_cash_flow_with_pd_buckets', 'INFO', f"No cash flows found for fic_mis_date {fic_mis_date} and run_skey {n_run_skey}.")
#             return 0

#         total_updated_records = 0

#         def process_batch(batch):
#             try:
#                 updates = []
#                 for cash_flow in batch:
#                     account_data = FCT_Stage_Determination.objects.filter(
#                         n_account_number=cash_flow.v_account_number,
#                         fic_mis_date=fic_mis_date
#                     ).first()

#                     if account_data:
#                         pd_records = FSI_PD_Interpolated.objects.filter(
#                             v_pd_term_structure_id=account_data.n_pd_term_structure_skey,
#                             fic_mis_date=fic_mis_date,
#                         )

#                         if pd_records.exists():
#                             pd_record = None
#                             if pd_records.first().v_pd_term_structure_type == 'R':
#                                 pd_record = pd_records.filter(
#                                     v_int_rating_code=account_data.n_credit_rating_code,
#                                     v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id
#                                 ).first()
#                             elif pd_records.first().v_pd_term_structure_type == 'D':
#                                 pd_record = pd_records.filter(
#                                     v_delq_band_code=account_data.n_delq_band_code,
#                                     v_cash_flow_bucket_id=cash_flow.n_cash_flow_bucket_id
#                                 ).first()

#                             if pd_record:
#                                 cash_flow.n_cumulative_loss_rate = pd_record.n_cumulative_default_prob * account_data.n_lgd_percent
#                                 cash_flow.n_cumulative_impaired_prob = pd_record.n_cumulative_default_prob

#                                 months_to_12m = get_buckets_for_12_months(account_data.v_amrt_term_unit)
#                                 if cash_flow.n_cash_flow_bucket_id <= months_to_12m:
#                                     cash_flow.n_12m_cumulative_pd = pd_record.n_cumulative_default_prob
#                                 else:
#                                     pd_record_12 = pd_records.filter(v_cash_flow_bucket_id=months_to_12m).first()
#                                     if pd_record_12:
#                                         cash_flow.n_12m_cumulative_pd = pd_record_12.n_cumulative_default_prob

#                                 updates.append(cash_flow)

#                 if updates:
#                     fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                         updates, 
#                         ['n_cumulative_loss_rate', 'n_cumulative_impaired_prob', 'n_12m_cumulative_pd']
#                     )
#                 return len(updates)

#             except Exception as e:
#                 save_log('update_cash_flow_with_pd_buckets', 'ERROR', f"Error updating batch: {e}")
#                 return 0

#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = []
#             batch = []
#             for cash_flow in cash_flows.iterator(chunk_size=batch_size):
#                 batch.append(cash_flow)
#                 if len(batch) >= batch_size:
#                     futures.append(executor.submit(process_batch, batch))
#                     batch = []

#             if batch:
#                 futures.append(executor.submit(process_batch, batch))

#             for future in as_completed(futures):
#                 try:
#                     total_updated_records += future.result()
#                 except Exception as exc:
#                     save_log('update_cash_flow_with_pd_buckets', 'ERROR', f"Thread encountered an error: {exc}")
#                     return 0

#         save_log('update_cash_flow_with_pd_buckets', 'INFO', f"Updated {total_updated_records} records for run_skey {n_run_skey} and fic_mis_date {fic_mis_date}.")
#         return 1 if total_updated_records > 0 else 0

#     except Exception as e:
#         save_log('update_cash_flow_with_pd_buckets', 'ERROR', f"Error updating cash flow for fic_mis_date {fic_mis_date}: {e}")
#         return 0

# def get_buckets_for_12_months(v_amrt_term_unit):
#     """
#     Returns the number of buckets required to reach 12 months based on the amortization term unit.
#     """
#     term_unit_to_buckets = {
#         'M': 12,
#         'Q': 4,
#         'H': 2,
#         'Y': 1
#     }
#     return term_unit_to_buckets.get(v_amrt_term_unit, 12)
