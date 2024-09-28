import concurrent.futures
from datetime import timedelta
from ..models import CoolingPeriodDefinition, FCT_Stage_Determination

def get_previous_stage_and_cooling_status(account, fic_mis_date):
    """
    Get the latest previous stage and cooling period status for the account by checking the latest previous fic_mis_date
    that is strictly before the input fic_mis_date.
    """
    previous_record = FCT_Stage_Determination.objects.filter(
        n_account_number=account.n_account_number,
        fic_mis_date__lt=fic_mis_date  # Ensure fic_mis_date is strictly less than the input date
    ).order_by('-fic_mis_date').first()  # Get the latest previous record

    if previous_record:
        return previous_record.n_curr_ifrs_stage_skey, previous_record.n_in_cooling_period_flag
    else:
        return None, False  # No previous stage found, and no cooling period flag

def is_cooling_period_expired(account):
    """
    Check if the cooling period has expired based on the start date and expected duration.
    """
    if account.d_cooling_start_date:
        days_in_cooling_period = (account.fic_mis_date - account.d_cooling_start_date).days
        if days_in_cooling_period >= account.n_cooling_period_duration:
            return True  # Cooling period has expired
    return False  # Cooling period is still ongoing

def start_cooling_period(account, current_stage, target_stage, fic_mis_date):
    """
    Start a new cooling period for the account when moving from a higher to a lower stage.
    The cooling period duration is determined based on the amortization term, and the start date is set to fic_mis_date.
    """
    try:
        cooling_period_def = CoolingPeriodDefinition.objects.get(v_amrt_term_unit=account.v_amrt_term_unit)
    except CoolingPeriodDefinition.DoesNotExist:
        print(f"Cooling period not defined for amortization unit {account.v_amrt_term_unit}. Skipping cooling period.")
        return

    # Start the cooling period and set the relevant fields
    account.d_cooling_start_date = fic_mis_date  # Set the cooling start date to the current fic_mis_date
    account.n_target_ifrs_stage_skey = target_stage
    account.n_in_cooling_period_flag = True
    account.n_cooling_period_duration = cooling_period_def.n_cooling_period_days

    print(f"Cooling period started for account {account.n_account_number} from stage {current_stage} to {target_stage}.")

def process_single_account(account, fic_mis_date):
    """
    Process cooling period and stage determination for a single account.
    """
    # Get the current stage (assumed to be pre-determined)
    current_stage = account.n_curr_ifrs_stage_skey

    # Get the previous stage and cooling status
    previous_stage, was_in_cooling_period = get_previous_stage_and_cooling_status(account, fic_mis_date)
    
    if previous_stage:
        if was_in_cooling_period:
            # If the account was in a cooling period, check if it returned to a higher stage
            if account.n_curr_ifrs_stage_skey >= previous_stage:
                print(f"Account {account.n_account_number} returned to a higher stage {previous_stage}. Resetting cooling period.")
                account.n_in_cooling_period_flag = False
                account.d_cooling_start_date = None
                account.n_cooling_period_duration = None
                account.n_target_ifrs_stage_skey = None
            else:
                # Check if the cooling period has expired
                if is_cooling_period_expired(account):
                    print(f"Cooling period expired for account {account.n_account_number}. Reclassification allowed.")
                    account.n_in_cooling_period_flag = False  # End the cooling period
                    account.n_target_ifrs_stage_skey = None  # Clear the target stage
                    account.n_curr_ifrs_stage_skey = current_stage  # Update to the new stage
                    account.n_stage_descr = f"Stage {current_stage}"
                else:
                    # Override the current stage if the account is still in the cooling period
                    print(f"Account {account.n_account_number} is still in the cooling period. Maintaining previous stage {previous_stage}.")
                    account.n_curr_ifrs_stage_skey = previous_stage
                    account.n_stage_descr = f"Stage {previous_stage}"
                    return  # Skip updating to the new stage if cooling period is ongoing
        else:
            # If not in a cooling period, start one if the current stage is lower than the previous
            if current_stage < previous_stage:
                start_cooling_period(account, previous_stage, current_stage, fic_mis_date)
                # Stay in the previous stage until the cooling period expires
                account.n_curr_ifrs_stage_skey = previous_stage
                account.n_stage_descr = f"Stage {previous_stage}"
            else:
                # If no cooling period is needed, update to the current stage
                account.n_curr_ifrs_stage_skey = current_stage
                account.n_stage_descr = f"Stage {current_stage}"
    print('no previous stage')

    # Save the account with the new or maintained stage
    account.save()

def process_cooling_period_for_accounts(fic_mis_date):
    """
    Process cooling period logic for accounts based on a given fic_mis_date using multi-threading.
    It checks if the account is in a cooling period and whether it should be reclassified or continue in the previous stage.
    """
    # Only query accounts where v_amrt_term_unit is defined in CoolingPeriodDefinition
    valid_amrt_term_units = CoolingPeriodDefinition.objects.values_list('v_amrt_term_unit', flat=True)
    accounts_to_process = FCT_Stage_Determination.objects.filter(
        fic_mis_date=fic_mis_date,
        v_amrt_term_unit__in=valid_amrt_term_units  # Filter only those with valid amortization units
    )

    # Use ThreadPoolExecutor to handle multiple accounts in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit each account to a thread for processing
        futures = [executor.submit(process_single_account, account, fic_mis_date) for account in accounts_to_process]
        
        # Wait for all threads to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Get the result of the thread, if any exceptions occurred they will be raised here
            except Exception as exc:
                print(f"An error occurred during account processing: {exc}")
