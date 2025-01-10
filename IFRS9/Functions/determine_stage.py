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
            save_log('get_latest_run_skey', 'ERROR', "No run key is available.")
            return None
        return run_record.latest_run_skey
    except Exception as e:
        save_log('get_latest_run_skey', 'ERROR', str(e))
        return None

def update_stage(mis_date):
    """
    Set-based updates for determining stages using credit ratings and DPD mappings.
    """
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            # Update stages using credit ratings
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN fsi_creditrating_stage AS crs 
                  ON crs.credit_rating = sd.n_credit_rating_code
                SET 
                    sd.n_stage_descr = crs.stage,
                    sd.n_curr_ifrs_stage_skey = 
                        CASE crs.stage
                            WHEN 'Stage 1' THEN 1
                            WHEN 'Stage 2' THEN 2
                            WHEN 'Stage 3' THEN 3
                            ELSE NULL
                        END
                WHERE sd.fic_mis_date = %s;
            """, [mis_date])

            # Update stages using DPD stage mappings
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN fsi_dpd_stage_mapping AS dpd
                  ON dpd.payment_frequency = sd.v_amrt_term_unit
                SET 
                    sd.n_stage_descr = 
                        CASE 
                            WHEN sd.n_delinquent_days <= dpd.stage_1_threshold THEN 'Stage 1'
                            WHEN sd.n_delinquent_days > dpd.stage_1_threshold 
                              AND sd.n_delinquent_days <= dpd.stage_2_threshold THEN 'Stage 2'
                            ELSE 'Stage 3'
                        END,
                    sd.n_curr_ifrs_stage_skey = 
                        CASE 
                            WHEN sd.n_delinquent_days <= dpd.stage_1_threshold THEN 1
                            WHEN sd.n_delinquent_days > dpd.stage_1_threshold 
                              AND sd.n_delinquent_days <= dpd.stage_2_threshold THEN 2
                            ELSE 3
                        END
                WHERE sd.fic_mis_date = %s 
                  AND sd.n_credit_rating_code IS NULL;
            """, [mis_date])

            # Update previous IFRS stage
            cursor.execute("""
                UPDATE fct_stage_determination AS sd
                JOIN (
                    SELECT 
                        n_account_number, 
                        MAX(fic_mis_date) AS prev_date,
                        n_curr_ifrs_stage_skey AS prev_stage
                    FROM fct_stage_determination
                    WHERE fic_mis_date < %s
                    GROUP BY n_account_number
                ) AS prev_sd
                  ON prev_sd.n_account_number = sd.n_account_number
                SET sd.n_prev_ifrs_stage_skey = prev_sd.prev_stage
                WHERE sd.fic_mis_date = %s;
            """, [mis_date, mis_date])

        save_log('update_stages_set_based', 'INFO', f"Set-based stage update completed for mis_date={mis_date}.")
        return 1

    except Exception as e:
        save_log('update_stages_set_based', 'ERROR', f"Error during set-based update for mis_date={mis_date}: {e}")
        return 0


# from django.db import transaction
# from ..models import FSI_CreditRating_Stage, FSI_DPD_Stage_Mapping, FCT_Stage_Determination
# from .save_log import save_log

# def determine_stage_for_account(account, credit_rating_cache, dpd_stage_mapping_cache):
#     """
#     Determine the stage for an account based on credit rating or DPD.
#     Priority is given to the credit rating if available, otherwise, DPD is used.
#     """
#     credit_rating_code = account.n_credit_rating_code
#     if credit_rating_code in credit_rating_cache:
#         return credit_rating_cache[credit_rating_code]  # Return the cached stage based on the credit rating
    
#     # Fallback to DPD stage determination if no valid credit rating found
#     return determine_stage_by_dpd(account, dpd_stage_mapping_cache)

# def determine_stage_by_dpd(account, dpd_stage_mapping_cache):
#     """
#     Determine the stage for an account based on Days Past Due (DPD) and payment frequency.
#     """
#     delinquent_days = account.n_delinquent_days
#     payment_frequency = account.v_amrt_term_unit

#     if delinquent_days is None or not payment_frequency:
#         return 'Unknown Stage', f"Missing DPD or payment frequency for account {account.n_account_number}"

#     dpd_stage_mapping = dpd_stage_mapping_cache.get(payment_frequency)
#     if not dpd_stage_mapping:
#         return 'Unknown Stage', f"DPD stage mapping not found for payment frequency {payment_frequency} in account {account.n_account_number}"

#     # Determine stage based on thresholds
#     if delinquent_days <= dpd_stage_mapping['stage_1_threshold']:
#         return 'Stage 1', None
#     elif dpd_stage_mapping['stage_1_threshold'] < delinquent_days <= dpd_stage_mapping['stage_2_threshold']:
#         return 'Stage 2', None
#     else:
#         return 'Stage 3', None

# def update_stage_for_account(account, fic_mis_date, credit_rating_cache, dpd_stage_mapping_cache, previous_stages):
#     """
#     Update the stage of a single account, setting both the stage description and the numeric value.
#     """
#     stage, error = determine_stage_for_account(account, credit_rating_cache, dpd_stage_mapping_cache)

#     if stage:
#         account.n_stage_descr = stage
#         account.n_curr_ifrs_stage_skey = {'Stage 1': 1, 'Stage 2': 2, 'Stage 3': 3}.get(stage)

#         # Get previous stage from the cached dictionary
#         previous_stage = previous_stages.get((account.n_account_number, fic_mis_date))
#         account.n_prev_ifrs_stage_skey = previous_stage if previous_stage else None

#         return account, error
#     return None, error

# def update_stage(fic_mis_date):
#     """
#     Update the stage of accounts in the FCT_Stage_Determination table for the provided fic_mis_date.
#     """
#     try:
#         accounts_to_update = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date)
#         if not accounts_to_update.exists():
#             save_log('update_stage', 'INFO', f"No accounts found for fic_mis_date {fic_mis_date}.")
#             return 0

#         # Cache related data for fast lookup to avoid repetitive queries
#         credit_rating_cache = {cr.credit_rating: cr.stage for cr in FSI_CreditRating_Stage.objects.all()}
#         dpd_stage_mapping_cache = {
#             mapping.payment_frequency: {
#                 'stage_1_threshold': mapping.stage_1_threshold,
#                 'stage_2_threshold': mapping.stage_2_threshold
#             }
#             for mapping in FSI_DPD_Stage_Mapping.objects.all()
#         }
        
#         # Cache previous stages by account number and `fic_mis_date`
#         previous_stages = {
#             (entry.n_account_number, entry.fic_mis_date): entry.n_curr_ifrs_stage_skey
#             for entry in FCT_Stage_Determination.objects.filter(fic_mis_date__lt=fic_mis_date).order_by('n_account_number', '-fic_mis_date')
#         }

#         # Initialize a dictionary to log unique errors
#         error_logs = {}

#         # Update stages for each account
#         updated_accounts = []
#         for account in accounts_to_update:
#             updated_account, error = update_stage_for_account(account, fic_mis_date, credit_rating_cache, dpd_stage_mapping_cache, previous_stages)
#             if updated_account:
#                 updated_accounts.append(updated_account)
#             if error and error not in error_logs:
#                 error_logs[error] = 1

#         # Perform a bulk update for all updated accounts in batches of 5000
#         batch_size = 5000
#         if updated_accounts:
#             with transaction.atomic():
#                 for i in range(0, len(updated_accounts), batch_size):
#                     FCT_Stage_Determination.objects.bulk_update(
#                         updated_accounts[i:i + batch_size], ['n_stage_descr', 'n_curr_ifrs_stage_skey', 'n_prev_ifrs_stage_skey']
#                     )
#             save_log('update_stage', 'INFO', f"Successfully updated stages for {len(updated_accounts)} accounts on fic_mis_date {fic_mis_date}.")
#         else:
#             save_log('update_stage', 'WARNING', f"No stages were updated for accounts on fic_mis_date {fic_mis_date}.")

#         # Log each unique error once
#         for error_message in error_logs:
#             save_log('update_stage', 'WARNING', error_message)

#         return 1

#     except Exception as e:
#         save_log('update_stage', 'ERROR', f"Error during stage update process for fic_mis_date {fic_mis_date}: {str(e)}")
#         return 0


