from django.db import connection, transaction
from ..models import Dim_Run
from .save_log import save_log

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.only('latest_run_skey').first()
        if not run_record:
            raise ValueError("No run key is available in the Dim_Run table.")
        return run_record.latest_run_skey
    except Dim_Run.DoesNotExist:
        raise ValueError("Dim_Run table is missing.")


def update_financial_cash_flow(fic_mis_date):
    """
    Use a single raw SQL UPDATE with JOIN to update n_effective_interest_rate and n_lgd_percent
    in fsi_financial_cash_flow_cal, leveraging a set-based approach for MariaDB/MySQL.
    """
    try:
        run_skey = get_latest_run_skey()
        if not run_skey:
            save_log('update_financial_cash_flow_fast', 'ERROR', "No valid run_skey found.")
            return '0'

        with transaction.atomic():
            with connection.cursor() as cursor:
                # Single UPDATE..JOIN statement
                sql = f"""
                    UPDATE fsi_financial_cash_flow_cal AS cf
                    JOIN fct_stage_determination AS sd
                      ON cf.fic_mis_date = sd.fic_mis_date
                     AND cf.v_account_number = sd.n_account_number
                    SET
                      cf.n_effective_interest_rate = sd.n_effective_interest_rate,
                      cf.n_lgd_percent = sd.n_lgd_percent
                    WHERE
                      cf.n_run_skey = {run_skey}
                      AND cf.fic_mis_date = '{fic_mis_date}'
                """
                cursor.execute(sql)
                updated_count = cursor.rowcount  # Number of rows actually changed

        if updated_count > 0:
            save_log(
                'update_financial_cash_flow_fast_mariadb',
                'INFO',
                f"Successfully updated {updated_count} rows for fic_mis_date={fic_mis_date}, run_skey={run_skey}."
            )
            return '1'
        else:
            save_log(
                'update_financial_cash_flow_fast_mariadb',
                'INFO',
                f"No rows matched for fic_mis_date={fic_mis_date}, run_skey={run_skey}."
            )
            return '0'

    except Exception as e:
        save_log(
            'update_financial_cash_flow_fast_mariadb',
            'ERROR',
            f"Error executing fast update for fic_mis_date={fic_mis_date}: {e}"
        )
        return '0'



# from django.db import transaction
# from concurrent.futures import ThreadPoolExecutor, as_completed

# from ..models import (
#     FCT_Stage_Determination,
#     fsi_Financial_Cash_Flow_Cal,
#     Dim_Run
# )
# from .save_log import save_log

# UPDATE_SUB_BATCH_SIZE = 5000  # Sub-batch size for final bulk update

# def get_latest_run_skey():
#     """
#     Retrieve the latest_run_skey from Dim_Run table.
#     """
#     try:
#         run_record = Dim_Run.objects.only('latest_run_skey').first()
#         if not run_record:
#             raise ValueError("No run key is available in the Dim_Run table.")
#         return run_record.latest_run_skey
#     except Dim_Run.DoesNotExist:
#         raise ValueError("Dim_Run table is missing.")


# def prefetch_stage_determination(fic_mis_date):
#     """
#     Fetch and cache all relevant stage determination data for the given date, 
#     keyed by (fic_mis_date, n_account_number) for O(1) lookups.
#     """
#     stage_qs = (
#         FCT_Stage_Determination.objects
#         .filter(fic_mis_date=fic_mis_date)
#         .only('fic_mis_date', 'n_account_number', 'n_effective_interest_rate', 'n_lgd_percent')
#     )
#     return {
#         (entry.fic_mis_date, entry.n_account_number): entry
#         for entry in stage_qs
#     }


# def process_batch(batch, stage_determination_dict):
#     """
#     Process a batch of cash flow records, setting n_effective_interest_rate and n_lgd_percent 
#     from the stage_determination_dict in memory. No DB write here; return updated records.
#     """
#     updated_batch = []
#     for cf in batch:
#         try:
#             stage_key = (cf.fic_mis_date, cf.v_account_number)
#             stage_entry = stage_determination_dict.get(stage_key)
#             if stage_entry:
#                 cf.n_effective_interest_rate = stage_entry.n_effective_interest_rate
#                 cf.n_lgd_percent = stage_entry.n_lgd_percent
#                 updated_batch.append(cf)
#         except Exception as e:
#             save_log('update_financial_cash_flow', 'ERROR', f"Error processing account={cf.v_account_number}: {e}")
#     return updated_batch


# def update_financial_cash_flow(fic_mis_date, max_workers=5, batch_size=1000):
#     """
#     Updates the `n_effective_interest_rate` and `n_lgd_percent` fields in the `fsi_Financial_Cash_Flow_Cal`
#     table using values from the `FCT_Stage_Determination` table, based on matching `v_account_number`, `fic_mis_date`,
#     and `n_run_skey`.
#     """
#     try:
#         # 1) Get run_skey
#         n_run_skey = get_latest_run_skey()
#         if not n_run_skey:
#             save_log('update_financial_cash_flow', 'ERROR', "No valid run_skey found in Dim_Run.")
#             return '0'

#         # 2) Pre-fetch stage determination in a dictionary
#         stage_determination_dict = prefetch_stage_determination(fic_mis_date)

#         # 3) Fetch only the fields needed from cash flow
#         cash_flows_qs = (
#             fsi_Financial_Cash_Flow_Cal.objects
#             .filter(fic_mis_date=fic_mis_date, n_run_skey=n_run_skey)
#             .only('v_account_number', 'fic_mis_date', 'n_effective_interest_rate', 'n_lgd_percent')
#         )
#         total_cash_flows = cash_flows_qs.count()
#         if total_cash_flows == 0:
#             save_log(
#                 'update_financial_cash_flow',
#                 'INFO',
#                 f"No financial cash flows found for fic_mis_date={fic_mis_date} and n_run_skey={n_run_skey}."
#             )
#             return '0'

#         save_log(
#             'update_financial_cash_flow',
#             'INFO',
#             f"Processing {total_cash_flows} records for date={fic_mis_date}, run_skey={n_run_skey}."
#         )

#         # 4) Stream the cash flows in chunks (iterator + chunk)
#         def chunk_iterator(qs, size):
#             start = 0
#             while True:
#                 batch_list = list(qs[start:start + size])
#                 if not batch_list:
#                     break
#                 yield batch_list
#                 start += size

#         updated_entries_all = []

#         # 5) Parallel processing of chunked data
#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = []
#             for cf_batch in chunk_iterator(cash_flows_qs, batch_size):
#                 futures.append(executor.submit(process_batch, cf_batch, stage_determination_dict))

#             for future in as_completed(futures):
#                 try:
#                     updated_entries_all.extend(future.result())
#                 except Exception as exc:
#                     save_log('update_financial_cash_flow', 'ERROR', f"Thread error: {exc}")
#                     return '0'

#         total_updated = len(updated_entries_all)
#         if total_updated == 0:
#             save_log(
#                 'update_financial_cash_flow',
#                 'INFO',
#                 "No records needed updating after matching stage determination."
#             )
#             return '0'

#         # 6) Bulk update in sub-batches
#         with transaction.atomic():
#             start_index = 0
#             while start_index < total_updated:
#                 end_index = start_index + UPDATE_SUB_BATCH_SIZE
#                 sub_batch = updated_entries_all[start_index:end_index]
#                 fsi_Financial_Cash_Flow_Cal.objects.bulk_update(
#                     sub_batch,
#                     ['n_effective_interest_rate', 'n_lgd_percent']
#                 )
#                 start_index = end_index

#         # 7) Final log
#         save_log(
#             'update_financial_cash_flow',
#             'INFO',
#             f"Successfully updated {total_updated} of {total_cash_flows} financial cash flow records for date={fic_mis_date}, run_skey={n_run_skey}."
#         )
#         return '1'

#     except Exception as e:
#         save_log(
#             'update_financial_cash_flow',
#             'ERROR',
#             f"Error updating financial cash flow records for fic_mis_date={fic_mis_date}, run_skey={n_run_skey}: {e}"
#         )
#         return '0'
