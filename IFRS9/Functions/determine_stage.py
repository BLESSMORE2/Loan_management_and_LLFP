import concurrent.futures
from ..models import FSI_CreditRating_Stage, FSI_DPD_Stage_Mapping, FCT_Stage_Determination
from ..Functions import save_log

def determine_stage_for_account(account):
    """
    Determine the stage for an account based on credit rating or DPD.
    Priority is given to the credit rating if available, otherwise, DPD is used.
    """
    credit_rating_code = account.n_credit_rating_code
    if credit_rating_code:
        try:
            credit_rating_stage = FSI_CreditRating_Stage.objects.get(credit_rating=credit_rating_code)
            return credit_rating_stage.stage  # Return the stage based on the credit rating
        except FSI_CreditRating_Stage.DoesNotExist:
            save_log('determine_stage_for_account', 'WARNING', f"Credit rating {credit_rating_code} not found for account {account.n_account_number}. Falling back to DPD.")

    # Fallback to DPD stage determination if no valid credit rating found
    return determine_stage_by_dpd(account)

def determine_stage_by_dpd(account):
    """
    Determine the stage for an account based on Days Past Due (DPD) and payment frequency.
    """
    delinquent_days = account.n_delinquent_days
    payment_frequency = account.v_amrt_term_unit

    if delinquent_days is None or not payment_frequency:
        save_log('determine_stage_by_dpd', 'WARNING', f"Missing DPD or payment frequency for account {account.n_account_number}. Cannot determine stage.")
        return 'Unknown Stage'

    try:
        dpd_stage_mapping = FSI_DPD_Stage_Mapping.objects.get(payment_frequency=payment_frequency)
        if delinquent_days <= dpd_stage_mapping.stage_1_threshold:
            return 'Stage 1'
        elif delinquent_days <= dpd_stage_mapping.stage_2_threshold:
            return 'Stage 2'
        else:
            return 'Stage 3'
    except FSI_DPD_Stage_Mapping.DoesNotExist:
        save_log('determine_stage_by_dpd', 'WARNING', f"DPD stage mapping not found for payment frequency {payment_frequency} in account {account.n_account_number}.")
        return 'Unknown Stage'

def get_latest_previous_fic_mis_date(account, current_fic_mis_date):
    """
    Get the latest previous fic_mis_date for the given account, excluding the current fic_mis_date.
    """
    return FCT_Stage_Determination.objects.filter(
        n_account_number=account.n_account_number,
        fic_mis_date__lt=current_fic_mis_date
    ).order_by('-fic_mis_date').first()

def update_stage_for_account(account, fic_mis_date):
    """
    Update the stage of a single account, setting both the stage description and the numeric value.
    """
    stage = determine_stage_for_account(account)

    if stage:
        account.n_stage_descr = stage
        account.n_curr_ifrs_stage_skey = {'Stage 1': 1, 'Stage 2': 2, 'Stage 3': 3}.get(stage)

        previous_account = get_latest_previous_fic_mis_date(account, fic_mis_date)
        account.n_prev_ifrs_stage_skey = previous_account.n_curr_ifrs_stage_skey if previous_account else None

        return account
    else:
        save_log('update_stage_for_account', 'WARNING', f"Failed to determine stage for account {account.n_account_number}.")
        return None

def update_stage(fic_mis_date):
    """
    Update the stage of accounts in the FCT_Stage_Determination table for the provided fic_mis_date using multi-threading.
    """
    try:
        accounts_to_update = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date)
        if not accounts_to_update.exists():
            save_log('update_stage', 'INFO', f"No accounts found for fic_mis_date {fic_mis_date}.")
            return 0

        updated_accounts = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(update_stage_for_account, account, fic_mis_date): account for account in accounts_to_update}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    updated_accounts.append(result)

        if updated_accounts:
            FCT_Stage_Determination.objects.bulk_update(updated_accounts, ['n_stage_descr', 'n_curr_ifrs_stage_skey', 'n_prev_ifrs_stage_skey'])
            save_log('update_stage', 'INFO', f"Successfully updated stages for {len(updated_accounts)} accounts on fic_mis_date {fic_mis_date}.")
        else:
            save_log('update_stage', 'WARNING', f"No stages were updated for accounts on fic_mis_date {fic_mis_date}.")

        return 1

    except Exception as e:
        save_log('update_stage', 'ERROR', f"Error during stage update process for fic_mis_date {fic_mis_date}: {str(e)}")
        return 0
