import concurrent.futures
from .models import FSI_CreditRating_Stage, FSI_DPD_Stage_Mapping, FCT_Stage_Determination

def determine_stage_for_account(account):
    """
    Determine the stage for an account based on credit rating or DPD.
    Priority is given to the credit rating if available, otherwise, DPD is used.
    """
    # Check if the account has a credit rating code
    credit_rating_code = account.n_credit_rating_code
    if credit_rating_code:
        try:
            # Look up the stage based on the credit rating
            credit_rating_stage = FSI_CreditRating_Stage.objects.get(credit_rating=credit_rating_code)
            return credit_rating_stage.stage  # Return the stage based on the credit rating
        except FSI_CreditRating_Stage.DoesNotExist:
            # Log or handle the missing credit rating entry
            print(f"Credit rating {credit_rating_code} not found for account {account.n_account_number}. Falling back to DPD.")
    
    # Fallback to DPD stage determination if no valid credit rating found
    return determine_stage_by_dpd(account)

def determine_stage_by_dpd(account):
    """
    Determine the stage for an account based on Days Past Due (DPD) and payment frequency.
    This method is only called if no valid credit rating is found.
    """
    delinquent_days = account.n_delinquent_days
    payment_frequency = account.v_amrt_term_unit  # Using v_amrt_term_unit for frequency (e.g., 'M', 'Q', 'H', 'Y')

    if delinquent_days is None or not payment_frequency:
        # Log or handle missing DPD data
        print(f"Missing DPD or payment frequency for account {account.n_account_number}. Cannot determine stage.")
        return 'Unknown Stage'

    # Try to find the DPD stage mapping for the given payment frequency
    try:
        dpd_stage_mapping = FSI_DPD_Stage_Mapping.objects.get(payment_frequency=payment_frequency)
        if delinquent_days <= dpd_stage_mapping.stage_1_threshold:
            return 'Stage 1'
        elif delinquent_days <= dpd_stage_mapping.stage_2_threshold:
            return 'Stage 2'
        else:
            return 'Stage 3'
    except FSI_DPD_Stage_Mapping.DoesNotExist:
        # Log or handle missing DPD stage mapping entry
        print(f"DPD stage mapping not found for payment frequency {payment_frequency} in account {account.n_account_number}.")
        return 'Unknown Stage'

def update_stage_for_account(account):
    """
    Update the stage of a single account.
    """
    stage = determine_stage_for_account(account)
    if stage:
        account.n_stage_descr = stage  # Update the stage description
        account.save()  # Save the account with the new stage
        print(f"Stage for account {account.n_account_number} updated to {stage}.")
    else:
        print(f"Failed to determine stage for account {account.n_account_number}.")

def update_stage_for_fic_mis_date(fic_mis_date):
    """
    Update the stage of accounts in the FCT_Stage_Determination table for the provided fic_mis_date using multi-threading.
    """
    # Filter accounts based on fic_mis_date
    accounts_to_update = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date)
    
    # Use ThreadPoolExecutor to handle multiple accounts in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit each account update to a thread
        futures = [executor.submit(update_stage_for_account, account) for account in accounts_to_update]
        
        # Wait for all threads to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Get the result of the thread, if any exceptions occurred they will be raised here
            except Exception as exc:
                print(f"An error occurred during stage update: {exc}")

# Example usage: Update all records with a specific fic_mis_date
fic_mis_date = '2024-09-17'  # Use the required date here
update_stage_for_fic_mis_date(fic_mis_date)
