from django.db import connection, transaction
from ..models import Dim_Run, ECLMethod
from .save_log import save_log

# ------------------------------------------------------------------------
# 1) Retrieve Latest Run Key
# ------------------------------------------------------------------------
def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT latest_run_skey FROM dim_run LIMIT 1;")
            result = cursor.fetchone()
            if result:
                return result[0]
            save_log('get_latest_run_skey', 'ERROR', "No run key is available in the Dim_Run table.")
            return None
    except Exception as e:
        save_log('get_latest_run_skey', 'ERROR', f"Error fetching run key: {e}")
        return None

# ------------------------------------------------------------------------
# 2) Main Dispatcher
# ------------------------------------------------------------------------
def calculate_ecl_based_on_method(fic_mis_date):
    """
    Dispatch to the correct SQL-based ECL calculation method.
    """
    try:
        # Get the latest run key
        n_run_key = get_latest_run_skey()
        if not n_run_key:
            return '0'

        # Fetch the ECL method
        with connection.cursor() as cursor:
            cursor.execute("SELECT method_name, uses_discounting FROM dim_ecl_method LIMIT 1;")
            result = cursor.fetchone()
            if not result:
                save_log('calculate_ecl_based_on_method', 'ERROR', "No ECL method is defined in the dim_ecl_method table.")
                return '0'

            method_name, uses_discounting = result
            save_log(
                'calculate_ecl_based_on_method',
                'INFO',
                f"Using ECL Method: {method_name}, Discounting: {uses_discounting}, Run Key: {n_run_key}"
            )

        # Dispatch to the correct method
        if method_name == 'forward_exposure':
            update_ecl_based_on_forward_loss_sql(n_run_key, fic_mis_date, uses_discounting)
        elif method_name == 'cash_flow':
            update_ecl_based_on_cash_shortfall_sql(n_run_key, fic_mis_date, uses_discounting)
        elif method_name == 'simple_ead':
            update_ecl_based_on_internal_calculations_sql(n_run_key, fic_mis_date)
        else:
            save_log('calculate_ecl_based_on_method', 'ERROR', f"Unknown ECL method: {method_name}")
            return '0'

        save_log('calculate_ecl_based_on_method', 'INFO', "ECL calculation completed successfully.")
        return '1'

    except Exception as e:
        save_log('calculate_ecl_based_on_method', 'ERROR', f"Error calculating ECL: {e}")
        return '0'

# ------------------------------------------------------------------------
# 3) ECL Calculation: Cash Shortfall
# ------------------------------------------------------------------------
def update_ecl_based_on_cash_shortfall_sql(n_run_key, fic_mis_date, uses_discounting):
    """
    SQL-based update of ECL based on cash shortfall or present value.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            if uses_discounting:
                cursor.execute("""
                    UPDATE fct_reporting_lines rl
                    SET
                        rl.n_lifetime_ecl_ncy = COALESCE(cf.total_cash_shortfall_pv, 0),
                        rl.n_12m_ecl_ncy = COALESCE(cf.total_12m_cash_shortfall_pv, 0)
                    FROM (
                        SELECT
                            v_account_number,
                            SUM(n_cash_shortfall_pv) AS total_cash_shortfall_pv,
                            SUM(n_12m_cash_shortfall_pv) AS total_12m_cash_shortfall_pv
                        FROM fsi_financial_cash_flow_cal
                        WHERE n_run_skey = %s AND fic_mis_date = %s
                        GROUP BY v_account_number
                    ) cf
                    WHERE rl.n_account_number = cf.v_account_number
                      AND rl.n_run_key = %s
                      AND rl.fic_mis_date = %s;
                """, [n_run_key, fic_mis_date, n_run_key, fic_mis_date])
            else:
                cursor.execute("""
                    UPDATE fct_reporting_lines rl
                    SET
                        rl.n_lifetime_ecl_ncy = COALESCE(cf.total_cash_shortfall, 0),
                        rl.n_12m_ecl_ncy = COALESCE(cf.total_12m_cash_shortfall, 0)
                    FROM (
                        SELECT
                            v_account_number,
                            SUM(n_cash_shortfall) AS total_cash_shortfall,
                            SUM(n_12m_cash_shortfall) AS total_12m_cash_shortfall
                        FROM fsi_financial_cash_flow_cal
                        WHERE n_run_skey = %s AND fic_mis_date = %s
                        GROUP BY v_account_number
                    ) cf
                    WHERE rl.n_account_number = cf.v_account_number
                      AND rl.n_run_key = %s
                      AND rl.fic_mis_date = %s;
                """, [n_run_key, fic_mis_date, n_run_key, fic_mis_date])

        save_log(
            'update_ecl_based_on_cash_shortfall_sql',
            'INFO',
            f"Successfully updated ECL based on cash shortfall for run key {n_run_key}, date {fic_mis_date}."
        )
    except Exception as e:
        save_log('update_ecl_based_on_cash_shortfall_sql', 'ERROR', f"Error: {e}")

# ------------------------------------------------------------------------
# 4) ECL Calculation: Forward Loss
# ------------------------------------------------------------------------
def update_ecl_based_on_forward_loss_sql(n_run_key, fic_mis_date, uses_discounting):
    """
    SQL-based update of ECL based on forward loss or present value.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            if uses_discounting:
                cursor.execute("""
                    UPDATE fct_reporting_lines rl
                    SET
                        rl.n_lifetime_ecl_ncy = COALESCE(fwd.total_fwd_loss_pv, 0),
                        rl.n_12m_ecl_ncy = COALESCE(fwd.total_12m_fwd_loss_pv, 0)
                    FROM (
                        SELECT
                            v_account_number,
                            SUM(n_forward_expected_loss_pv) AS total_fwd_loss_pv,
                            SUM(n_12m_fwd_expected_loss_pv) AS total_12m_fwd_loss_pv
                        FROM fsi_financial_cash_flow_cal
                        WHERE n_run_skey = %s AND fic_mis_date = %s
                        GROUP BY v_account_number
                    ) fwd
                    WHERE rl.n_account_number = fwd.v_account_number
                      AND rl.n_run_key = %s
                      AND rl.fic_mis_date = %s;
                """, [n_run_key, fic_mis_date, n_run_key, fic_mis_date])
            else:
                cursor.execute("""
                    UPDATE fct_reporting_lines rl
                    SET
                        rl.n_lifetime_ecl_ncy = COALESCE(fwd.total_fwd_loss, 0),
                        rl.n_12m_ecl_ncy = COALESCE(fwd.total_12m_fwd_loss, 0)
                    FROM (
                        SELECT
                            v_account_number,
                            SUM(n_forward_expected_loss) AS total_fwd_loss,
                            SUM(n_12m_fwd_expected_loss) AS total_12m_fwd_loss
                        FROM fsi_financial_cash_flow_cal
                        WHERE n_run_skey = %s AND fic_mis_date = %s
                        GROUP BY v_account_number
                    ) fwd
                    WHERE rl.n_account_number = fwd.v_account_number
                      AND rl.n_run_key = %s
                      AND rl.fic_mis_date = %s;
                """, [n_run_key, fic_mis_date, n_run_key, fic_mis_date])

        save_log(
            'update_ecl_based_on_forward_loss_sql',
            'INFO',
            f"Successfully updated ECL based on forward loss for run key {n_run_key}, date {fic_mis_date}."
        )
    except Exception as e:
        save_log('update_ecl_based_on_forward_loss_sql', 'ERROR', f"Error: {e}")

# ------------------------------------------------------------------------
# 5) ECL Calculation: Internal Formula
# ------------------------------------------------------------------------
def update_ecl_based_on_internal_calculations_sql(n_run_key, fic_mis_date):
    """
    SQL-based update of ECL using internal formula: EAD * PD * LGD.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("""
                UPDATE fct_reporting_lines
                SET
                    n_lifetime_ecl_ncy = COALESCE(n_exposure_at_default_ncy, 0) * COALESCE(n_lifetime_pd, 0) * COALESCE(n_lgd_percent, 0),
                    n_12m_ecl_ncy = COALESCE(n_exposure_at_default_ncy, 0) * COALESCE(n_twelve_months_pd, 0) * COALESCE(n_lgd_percent, 0)
                WHERE n_run_key = %s AND fic_mis_date = %s;
            """, [n_run_key, fic_mis_date])

        save_log(
            'update_ecl_based_on_internal_calculations_sql',
            'INFO',
            f"Successfully updated ECL using internal formula for run key {n_run_key}, date {fic_mis_date}."
        )
    except Exception as e:
        save_log('update_ecl_based_on_internal_calculations_sql', 'ERROR', f"Error: {e}")


# from concurrent.futures import ThreadPoolExecutor, as_completed
# from django.db import transaction
# from django.db.models import Sum
# from decimal import Decimal

# from ..models import (
#     FCT_Reporting_Lines,
#     fsi_Financial_Cash_Flow_Cal,
#     ECLMethod,
#     Dim_Run
# )
# from .save_log import save_log

# BATCH_SIZE = 5000  # Bulk update batch size

# # ------------------------------------------------------------------------
# # 1) Retrieve Latest Run Key
# # ------------------------------------------------------------------------
# def get_latest_run_skey():
#     """
#     Retrieve the latest_run_skey from Dim_Run table.
#     """
#     try:
#         run_record = Dim_Run.objects.first()
#         if not run_record:
#             save_log('get_latest_run_skey', 'ERROR', "No run key is available in the Dim_Run table.")
#             return None
#         return run_record.latest_run_skey
#     except Dim_Run.DoesNotExist:
#         save_log('get_latest_run_skey', 'ERROR', "Dim_Run table is missing.")
#         return None


# # ------------------------------------------------------------------------
# # 2) Main Dispatcher: Determines Which ECL Method to Use
# # ------------------------------------------------------------------------
# def calculate_ecl_based_on_method(fic_mis_date):
#     """
#     Fetches the ECL method from ECLMethod table and calls the appropriate update function.
#     """
#     try:
#         # Get the latest run key
#         n_run_key = get_latest_run_skey()
#         if not n_run_key:
#             return '0'

#         # Get the ECL method record
#         ecl_method_record = ECLMethod.objects.first()
#         if not ecl_method_record:
#             save_log('calculate_ecl_based_on_method', 'ERROR', "No ECL method is defined in the ECLMethod table.")
#             return '0'

#         method_name = ecl_method_record.method_name
#         uses_discounting = ecl_method_record.uses_discounting

#         save_log(
#             'calculate_ecl_based_on_method',
#             'INFO',
#             f"Using ECL Method: {method_name}, Discounting: {uses_discounting}, Run Key: {n_run_key}"
#         )

#         # Dispatch to the appropriate method
#         if method_name == 'forward_exposure':
#             update_ecl_based_on_forward_loss(n_run_key, fic_mis_date, uses_discounting)
#         elif method_name == 'cash_flow':
#             update_ecl_based_on_cash_shortfall(n_run_key, fic_mis_date, uses_discounting)
#         elif method_name == 'simple_ead':
#             update_ecl_based_on_internal_calculations(n_run_key, fic_mis_date)
#         else:
#             save_log('calculate_ecl_based_on_method', 'ERROR', f"Unknown ECL method: {method_name}")
#             return '0'

#         save_log('calculate_ecl_based_on_method', 'INFO', "ECL calculation completed successfully.")
#         return '1'

#     except Exception as e:
#         save_log('calculate_ecl_based_on_method', 'ERROR', f"Error calculating ECL: {e}")
#         return '0'


# # ------------------------------------------------------------------------
# # 3) Method A: ECL Based on Cash Shortfall
# # ------------------------------------------------------------------------

# def fetch_cash_flows_by_account(run_key, fic_mis_date):
#     """
#     Fetch all relevant cash flow rows in one query, group them by v_account_number.

#     Returns a dict:
#     {
#       'ACCOUNT1': [
#         {
#           'n_cash_shortfall_pv': ...,
#           'n_12m_cash_shortfall_pv': ...,
#           'n_cash_shortfall': ...,
#           'n_12m_cash_shortfall': ...
#         },
#         ...
#       ],
#       'ACCOUNT2': [...],
#       ...
#     }
#     """
#     flows = (
#         fsi_Financial_Cash_Flow_Cal.objects
#         .filter(n_run_skey=run_key, fic_mis_date=fic_mis_date)
#         .values(
#             'v_account_number',
#             'n_cash_shortfall_pv',
#             'n_12m_cash_shortfall_pv',
#             'n_cash_shortfall',
#             'n_12m_cash_shortfall'
#         )
#     )

#     flow_dict = {}
#     for row in flows:
#         acc = row['v_account_number']
#         if acc not in flow_dict:
#             flow_dict[acc] = []
#         flow_dict[acc].append({
#             'n_cash_shortfall_pv': row['n_cash_shortfall_pv'],
#             'n_12m_cash_shortfall_pv': row['n_12m_cash_shortfall_pv'],
#             'n_cash_shortfall': row['n_cash_shortfall'],
#             'n_12m_cash_shortfall': row['n_12m_cash_shortfall']
#         })
#     return flow_dict


# def process_entry_for_cash_flow(entry, cash_flow_cache, uses_discounting):
#     """
#     Compute ECL from cached cash flow data for a single FCT_Reporting_Lines entry.
#     """
#     records = cash_flow_cache.get(entry.n_account_number, [])
#     if uses_discounting:
#         total_cash_shortfall_pv = sum(r['n_cash_shortfall_pv'] or 0 for r in records)
#         total_12m_cash_shortfall_pv = sum(r['n_12m_cash_shortfall_pv'] or 0 for r in records)
#         entry.n_lifetime_ecl_ncy = total_cash_shortfall_pv
#         entry.n_12m_ecl_ncy = total_12m_cash_shortfall_pv
#     else:
#         total_cash_shortfall = sum(r['n_cash_shortfall'] or 0 for r in records)
#         total_12m_cash_shortfall = sum(r['n_12m_cash_shortfall'] or 0 for r in records)
#         entry.n_lifetime_ecl_ncy = total_cash_shortfall
#         entry.n_12m_ecl_ncy = total_12m_cash_shortfall
#     return entry


# def update_ecl_based_on_cash_shortfall(n_run_key, fic_mis_date, uses_discounting):
#     """
#     Updates ECL fields based on cash shortfall or present value of cash shortfall.
#     """
#     try:
#         # Fetch reporting lines in memory
#         reporting_lines = list(
#             FCT_Reporting_Lines.objects
#             .filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)
#             .only('n_account_number', 'n_lifetime_ecl_ncy', 'n_12m_ecl_ncy')
#         )

#         # Single query to fetch all CF data, grouped by account
#         cash_flow_cache = fetch_cash_flows_by_account(n_run_key, fic_mis_date)

#         # Process in parallel
#         updated_entries = []
#         with ThreadPoolExecutor(max_workers=5) as executor:
#             futures = [
#                 executor.submit(process_entry_for_cash_flow, rl, cash_flow_cache, uses_discounting)
#                 for rl in reporting_lines
#             ]
#             for f in as_completed(futures):
#                 updated_entries.append(f.result())

#         # Bulk update in sub-batches
#         with transaction.atomic():
#             for i in range(0, len(updated_entries), BATCH_SIZE):
#                 FCT_Reporting_Lines.objects.bulk_update(
#                     updated_entries[i:i + BATCH_SIZE],
#                     ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy']
#                 )

#         save_log(
#             'update_ecl_based_on_cash_shortfall',
#             'INFO',
#             f"Successfully updated {len(updated_entries)} records for run key {n_run_key}, date {fic_mis_date}."
#         )
#     except Exception as e:
#         save_log('update_ecl_based_on_cash_shortfall', 'ERROR', f"Error: {e}")


# # ------------------------------------------------------------------------
# # 4) Method B: ECL Based on Forward Loss
# # ------------------------------------------------------------------------

# def fetch_forward_loss_sums(run_key, fic_mis_date):
#     """
#     Fetch sums of forward expected losses in a single DB query, grouped by account.

#     Returns a dict:
#     {
#       'ACCOUNT1': {
#         'fwd_loss_pv': ...,
#         'fwd_loss_12m_pv': ...,
#         'fwd_loss': ...,
#         'fwd_loss_12m': ...
#       },
#       'ACCOUNT2': {...},
#       ...
#     }
#     """
#     qs = (
#         fsi_Financial_Cash_Flow_Cal.objects
#         .filter(n_run_skey=run_key, fic_mis_date=fic_mis_date)
#         .values('v_account_number')
#         .annotate(
#             total_fwd_loss_pv=Sum('n_forward_expected_loss_pv'),
#             total_12m_fwd_loss_pv=Sum('n_12m_fwd_expected_loss_pv'),
#             total_fwd_loss=Sum('n_forward_expected_loss'),
#             total_12m_fwd_loss=Sum('n_12m_fwd_expected_loss')
#         )
#     )
#     result = {}
#     for row in qs:
#         acc = row['v_account_number']
#         result[acc] = {
#             'fwd_loss_pv': row['total_fwd_loss_pv'] or 0,
#             'fwd_loss_12m_pv': row['total_12m_fwd_loss_pv'] or 0,
#             'fwd_loss': row['total_fwd_loss'] or 0,
#             'fwd_loss_12m': row['total_12m_fwd_loss'] or 0
#         }
#     return result


# def process_entry_forward_loss(entry, forward_loss_dict, uses_discounting):
#     """
#     Update ECL fields for a single FCT_Reporting_Lines entry using forward loss sums.
#     """
#     sums = forward_loss_dict.get(entry.n_account_number, {})
#     if uses_discounting:
#         entry.n_lifetime_ecl_ncy = sums.get('fwd_loss_pv', 0)
#         entry.n_12m_ecl_ncy = sums.get('fwd_loss_12m_pv', 0)
#     else:
#         entry.n_lifetime_ecl_ncy = sums.get('fwd_loss', 0)
#         entry.n_12m_ecl_ncy = sums.get('fwd_loss_12m', 0)
#     return entry


# def update_ecl_based_on_forward_loss(n_run_key, fic_mis_date, uses_discounting):
#     """
#     Updates ECL using forward expected loss sums or present value of forward expected loss.
#     """
#     try:
#         # Fetch reporting lines in memory
#         reporting_lines = list(
#             FCT_Reporting_Lines.objects
#             .filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)
#             .only('n_account_number', 'n_lifetime_ecl_ncy', 'n_12m_ecl_ncy')
#         )

#         # Single query to fetch forward loss sums, grouped by account
#         forward_loss_dict = fetch_forward_loss_sums(n_run_key, fic_mis_date)

#         # Process in parallel
#         with ThreadPoolExecutor(max_workers=20) as executor:
#             updated_entries = list(
#                 executor.map(
#                     lambda rl: process_entry_forward_loss(rl, forward_loss_dict, uses_discounting),
#                     reporting_lines
#                 )
#             )

#         # Bulk update in sub-batches
#         with transaction.atomic():
#             updated_count = 0
#             for i in range(0, len(updated_entries), BATCH_SIZE):
#                 batch = updated_entries[i:i + BATCH_SIZE]
#                 FCT_Reporting_Lines.objects.bulk_update(
#                     batch, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy']
#                 )
#                 updated_count += len(batch)

#         save_log(
#             'update_ecl_based_on_forward_loss',
#             'INFO',
#             f"Successfully updated {updated_count} records (forward loss) for run key {n_run_key}, date {fic_mis_date}."
#         )
#     except Exception as e:
#         save_log('update_ecl_based_on_forward_loss', 'ERROR', f"Error: {e}")


# # ------------------------------------------------------------------------
# # 5) Method C: ECL Based on Internal Calculations (Simple EAD)
# # ------------------------------------------------------------------------

# def process_internal_ecl(entry):
#     """
#     For 'simple_ead' method, calculate ECL using n_exposure_at_default_ncy, PD, and LGD.
#     """
#     # lifetime
#     if entry.n_exposure_at_default_ncy and entry.n_lifetime_pd and entry.n_lgd_percent:
#         entry.n_lifetime_ecl_ncy = entry.n_exposure_at_default_ncy * entry.n_lifetime_pd * entry.n_lgd_percent

#     # 12-month
#     if entry.n_exposure_at_default_ncy and entry.n_twelve_months_pd and entry.n_lgd_percent:
#         entry.n_12m_ecl_ncy = entry.n_exposure_at_default_ncy * entry.n_twelve_months_pd * entry.n_lgd_percent

#     return entry


# def update_ecl_based_on_internal_calculations(n_run_key, fic_mis_date):
#     """
#     Update ECL based on internal formula: EAD * PD * LGD.
#     """
#     try:
#         # Fetch reporting lines in memory
#         reporting_lines = list(
#             FCT_Reporting_Lines.objects
#             .filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)
#             .only(
#                 'n_exposure_at_default_ncy', 'n_lifetime_pd', 'n_lgd_percent',
#                 'n_twelve_months_pd', 'n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'
#             )
#         )

#         # Parallel process
#         with ThreadPoolExecutor(max_workers=5) as executor:
#             updated_entries = list(executor.map(process_internal_ecl, reporting_lines))

#         # Bulk update in sub-batches
#         with transaction.atomic():
#             total_updated = 0
#             for i in range(0, len(updated_entries), BATCH_SIZE):
#                 batch = updated_entries[i:i + BATCH_SIZE]
#                 FCT_Reporting_Lines.objects.bulk_update(
#                     batch, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy']
#                 )
#                 total_updated += len(batch)

#         save_log(
#             'update_ecl_based_on_internal_calculations',
#             'INFO',
#             f"Successfully updated {total_updated} records with internal ECL calculations for run key {n_run_key}, date {fic_mis_date}."
#         )
#     except Exception as e:
#         save_log('update_ecl_based_on_internal_calculations', 'ERROR', f"Error: {e}")

# from concurrent.futures import ThreadPoolExecutor
# from django.db.models import Sum
# from django.db import transaction
# from ..models import FCT_Reporting_Lines, fsi_Financial_Cash_Flow_Cal, ECLMethod, Dim_Run
# from .save_log import save_log

# def get_latest_run_skey():
#     """
#     Retrieve the latest_run_skey from Dim_Run table.
#     """
#     try:
#         run_record = Dim_Run.objects.first()
#         if not run_record:
#             save_log('get_latest_run_skey', 'ERROR', "No run key is available in the Dim_Run table.")
#             return None
#         return run_record.latest_run_skey
#     except Dim_Run.DoesNotExist:
#         save_log('get_latest_run_skey', 'ERROR', "Dim_Run table is missing.")
#         return None

# def calculate_ecl_based_on_method(fic_mis_date):
#     """
#     Determines the ECL calculation method from the ECLMethod table and applies it.
#     Applies discounting if required by the method, using the latest run key.
#     """
#     try:
#         n_run_key = get_latest_run_skey()
#         if not n_run_key:
#             return '0'

#         ecl_method_record = ECLMethod.objects.first()
#         if not ecl_method_record:
#             save_log('calculate_ecl_based_on_method', 'ERROR', "No ECL method is defined in the ECLMethod table.")
#             return '0'

#         method_name = ecl_method_record.method_name
#         uses_discounting = ecl_method_record.uses_discounting

#         save_log('calculate_ecl_based_on_method', 'INFO', f"Using ECL Method: {method_name}, Discounting: {uses_discounting}, Run Key: {n_run_key}")

#         if method_name == 'forward_exposure':
#             update_ecl_based_on_forward_loss(n_run_key, fic_mis_date, uses_discounting)
#         elif method_name == 'cash_flow':
#             update_ecl_based_on_cash_shortfall(n_run_key, fic_mis_date, uses_discounting)
#         elif method_name == 'simple_ead':
#             update_ecl_based_on_internal_calculations(n_run_key, fic_mis_date)
#         else:
#             save_log('calculate_ecl_based_on_method', 'ERROR', f"Unknown ECL method: {method_name}")
#             return '0'

#         save_log('calculate_ecl_based_on_method', 'INFO', "ECL calculation completed successfully.")
#         return '1'

#     except Exception as e:
#         save_log('calculate_ecl_based_on_method', 'ERROR', f"Error calculating ECL: {e}")
#         return '0'

# def update_ecl_based_on_cash_shortfall(n_run_key, fic_mis_date, uses_discounting):
#     """
#     Updates ECL based on cash shortfall or cash shortfall present value using multi-threading and bulk update.
#     If uses_discounting is True, it uses present value fields.
#     """
#     try:
#         reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)

#         def process_entry(entry):
#             cash_flow_records = fsi_Financial_Cash_Flow_Cal.objects.filter(
#                 n_run_skey=n_run_key,
#                 fic_mis_date=fic_mis_date,
#                 v_account_number=entry.n_account_number
#             )

#             if uses_discounting:
#                 total_cash_shortfall_pv = cash_flow_records.aggregate(Sum('n_cash_shortfall_pv'))['n_cash_shortfall_pv__sum'] or 0
#                 total_12m_cash_shortfall_pv = cash_flow_records.aggregate(Sum('n_12m_cash_shortfall_pv'))['n_12m_cash_shortfall_pv__sum'] or 0
#                 entry.n_lifetime_ecl_ncy = total_cash_shortfall_pv
#                 entry.n_12m_ecl_ncy = total_12m_cash_shortfall_pv
#             else:
#                 total_cash_shortfall = cash_flow_records.aggregate(Sum('n_cash_shortfall'))['n_cash_shortfall__sum'] or 0
#                 total_12m_cash_shortfall = cash_flow_records.aggregate(Sum('n_12m_cash_shortfall'))['n_12m_cash_shortfall__sum'] or 0
#                 entry.n_lifetime_ecl_ncy = total_cash_shortfall
#                 entry.n_12m_ecl_ncy = total_12m_cash_shortfall

#             return entry

#         with ThreadPoolExecutor(max_workers=20) as executor:
#             updated_entries = list(executor.map(process_entry, reporting_lines))

#         with transaction.atomic():
#             updated_count = FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

#         save_log('update_ecl_based_on_cash_shortfall', 'INFO', f"Successfully updated {updated_count} records for ECL based on cash shortfall for run key {n_run_key} and MIS date {fic_mis_date}.")
#     except Exception as e:
#         save_log('update_ecl_based_on_cash_shortfall', 'ERROR', f"Error updating ECL based on cash shortfall: {e}")

# def update_ecl_based_on_forward_loss(n_run_key, fic_mis_date, uses_discounting):
#     """
#     Updates ECL based on forward expected loss or forward expected loss present value using multi-threading and bulk update.
#     If uses_discounting is True, it uses present value fields.
#     """
#     try:
#         reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)

#         def process_entry(entry):
#             cash_flow_records = fsi_Financial_Cash_Flow_Cal.objects.filter(
#                 n_run_skey=n_run_key,
#                 fic_mis_date=fic_mis_date,
#                 v_account_number=entry.n_account_number
#             )

#             if uses_discounting:
#                 total_forward_expected_loss_pv = cash_flow_records.aggregate(Sum('n_forward_expected_loss_pv'))['n_forward_expected_loss_pv__sum'] or 0
#                 total_12m_fwd_expected_loss_pv = cash_flow_records.aggregate(Sum('n_12m_fwd_expected_loss_pv'))['n_12m_fwd_expected_loss_pv__sum'] or 0
#                 entry.n_lifetime_ecl_ncy = total_forward_expected_loss_pv
#                 entry.n_12m_ecl_ncy = total_12m_fwd_expected_loss_pv
#             else:
#                 total_forward_expected_loss = cash_flow_records.aggregate(Sum('n_forward_expected_loss'))['n_forward_expected_loss__sum'] or 0
#                 total_12m_fwd_expected_loss = cash_flow_records.aggregate(Sum('n_12m_fwd_expected_loss'))['n_12m_fwd_expected_loss__sum'] or 0
#                 entry.n_lifetime_ecl_ncy = total_forward_expected_loss
#                 entry.n_12m_ecl_ncy = total_12m_fwd_expected_loss

#             return entry

#         with ThreadPoolExecutor(max_workers=20) as executor:
#             updated_entries = list(executor.map(process_entry, reporting_lines))

#         with transaction.atomic():
#             updated_count = FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

#         save_log('update_ecl_based_on_forward_loss', 'INFO', f"Successfully updated {updated_count} records for ECL based on forward expected loss for run key {n_run_key} and MIS date {fic_mis_date}.")
#     except Exception as e:
#         save_log('update_ecl_based_on_forward_loss', 'ERROR', f"Error updating ECL based on forward expected loss: {e}")

# def update_ecl_based_on_internal_calculations(n_run_key, fic_mis_date):
#     """
#     Updates ECL based on simple internal calculations: EAD * PD * LGD using multi-threading and bulk update.
#     This method does not use discounting.
#     """
#     try:
#         reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)

#         def process_entry(entry):
#             if entry.n_exposure_at_default_ncy and entry.n_lifetime_pd and entry.n_lgd_percent:
#                 entry.n_lifetime_ecl_ncy = entry.n_exposure_at_default_ncy * entry.n_lifetime_pd * entry.n_lgd_percent

#             if entry.n_exposure_at_default_ncy and entry.n_twelve_months_pd and entry.n_lgd_percent:
#                 entry.n_12m_ecl_ncy = entry.n_exposure_at_default_ncy * entry.n_twelve_months_pd * entry.n_lgd_percent

#             return entry

#         with ThreadPoolExecutor(max_workers=20) as executor:
#             updated_entries = list(executor.map(process_entry, reporting_lines))

#         with transaction.atomic():
#             updated_count = FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

#         save_log('update_ecl_based_on_internal_calculations', 'INFO', f"Successfully updated {updated_count} records for ECL based on internal calculations for run key {n_run_key} and MIS date {fic_mis_date}.")
#     except Exception as e:
#         save_log('update_ecl_based_on_internal_calculations', 'ERROR', f"Error updating ECL based on internal calculations: {e}")
