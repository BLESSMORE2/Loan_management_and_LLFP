import concurrent.futures
from decimal import Decimal
from math import pow

from django.db.models import F
from django.db import transaction

from ..models import CoolingPeriodDefinition, FCT_Stage_Determination
from .save_log import save_log


def get_previous_stage_and_cooling_status(account_number, fic_mis_date):
    """
    Get the latest previous stage and cooling period status for the given account_number
    by checking the most recent record strictly before fic_mis_date.
    """
    previous_record = (
        FCT_Stage_Determination.objects
        .filter(n_account_number=account_number, fic_mis_date__lt=fic_mis_date)
        .order_by('-fic_mis_date')
        .only('n_curr_ifrs_stage_skey', 'n_in_cooling_period_flag')
        .first()
    )

    if previous_record:
        return previous_record.n_curr_ifrs_stage_skey, previous_record.n_in_cooling_period_flag
    else:
        return None, False


def is_cooling_period_expired(account):
    """
    Check if the cooling period has expired based on the start date and expected duration.
    """
    if account.d_cooling_start_date:
        days_in_cooling = (account.fic_mis_date - account.d_cooling_start_date).days
        if days_in_cooling >= (account.n_cooling_period_duration or 0):
            return True
    return False


def start_cooling_period(account, previous_stage, current_stage):
    """
    Start a new cooling period for the account when moving from a higher stage to a lower stage.
    """
    try:
        # Attempt to fetch CoolingPeriodDefinition for the account’s amortization unit
        cooling_def = CoolingPeriodDefinition.objects.get(v_amrt_term_unit=account.v_amrt_term_unit)
    except CoolingPeriodDefinition.DoesNotExist:
        save_log(
            'start_cooling_period',
            'WARNING',
            f"No cooling period defined for amortization unit={account.v_amrt_term_unit}. Skipping."
        )
        return

    account.d_cooling_start_date = account.fic_mis_date
    account.n_target_ifrs_stage_skey = current_stage
    account.n_in_cooling_period_flag = True
    account.n_cooling_period_duration = cooling_def.n_cooling_period_days
    # Revert the stage to the higher (previous) stage until cooling is done
    account.n_curr_ifrs_stage_skey = previous_stage
    account.n_stage_descr = f"Stage {previous_stage}"


def process_single_account(account):
    """
    Process cooling period and stage determination logic for a single account record.
    """
    try:
        current_stage = account.n_curr_ifrs_stage_skey
        previous_stage, was_in_cooling_period = get_previous_stage_and_cooling_status(
            account.n_account_number, 
            account.fic_mis_date
        )

        if previous_stage is not None:
            if was_in_cooling_period:
                # If we were in cooling, check if we can exit or must remain
                if current_stage >= previous_stage:
                    # Stage is now same or higher -> exit cooling
                    account.n_in_cooling_period_flag = False
                    account.d_cooling_start_date = None
                    account.n_cooling_period_duration = None
                    account.n_target_ifrs_stage_skey = None
                    # Keep current_stage
                    account.n_curr_ifrs_stage_skey = current_stage
                    account.n_stage_descr = f"Stage {current_stage}"
                else:
                    # Stage is lower -> possibly remain in cooling
                    if is_cooling_period_expired(account):
                        # Cooling expired, finalize the lower stage
                        account.n_in_cooling_period_flag = False
                        account.n_target_ifrs_stage_skey = None
                        account.n_curr_ifrs_stage_skey = current_stage
                        account.n_stage_descr = f"Stage {current_stage}"
                    else:
                        # Still in cooling -> revert stage to previous
                        account.n_curr_ifrs_stage_skey = previous_stage
                        account.n_stage_descr = f"Stage {previous_stage}"
                        return account  # No need to save now if partial logic
            else:
                # We were not in cooling previously
                if current_stage < previous_stage:
                    # Stage decreased -> start cooling
                    start_cooling_period(account, previous_stage, current_stage)
                else:
                    # Stage same or higher -> normal progression
                    account.n_curr_ifrs_stage_skey = current_stage
                    account.n_stage_descr = f"Stage {current_stage}"
        else:
            save_log(
                'process_single_account',
                'INFO',
                f"No previous stage found for account={account.n_account_number}."
            )
            # Keep current stage as is

        return account  # Return for final saving
    except Exception as e:
        save_log(
            'process_single_account',
            'ERROR',
            f"Error processing account={account.n_account_number}: {e}"
        )
        return None


def process_cooling_period_for_accounts(fic_mis_date, num_threads=4, batch_size=2000, update_batch_size=5000):
    """
    Process cooling period logic for accounts based on a given fic_mis_date using multi-threading.
    Leverages chunking, parallel execution, and optional sub-batch updates for performance.

    :param fic_mis_date:      MIS date
    :param num_threads:       Parallel threads for processing
    :param batch_size:        Number of records processed in each thread
    :param update_batch_size: Number of records to update in each bulk update sub-batch
    :return:                  1 if success, 0 otherwise
    """
    try:
        # Fetch valid amortization units from CoolingPeriodDefinition
        valid_amrt_units = list(CoolingPeriodDefinition.objects.values_list('v_amrt_term_unit', flat=True))
        if not valid_amrt_units:
            save_log(
                'process_cooling_period_for_accounts',
                'WARNING',
                "No CoolingPeriodDefinition records found. Skipping all processing."
            )
            return 0

        # We only need columns used in the logic
        accounts_qs = (
            FCT_Stage_Determination.objects
            .filter(fic_mis_date=fic_mis_date, v_amrt_term_unit__in=valid_amrt_units)
            .only(
                'n_account_number',
                'fic_mis_date',
                'n_curr_ifrs_stage_skey',
                'n_in_cooling_period_flag',
                'd_cooling_start_date',
                'n_cooling_period_duration',
                'n_target_ifrs_stage_skey',
                'n_stage_descr',
                'v_amrt_term_unit',
            )
        )
        total_accounts = accounts_qs.count()
        if total_accounts == 0:
            save_log(
                'process_cooling_period_for_accounts',
                'INFO',
                f"No accounts found for fic_mis_date={fic_mis_date} with valid amortization units."
            )
            return 0

        save_log(
            'process_cooling_period_for_accounts',
            'INFO',
            f"Processing {total_accounts} accounts for fic_mis_date={fic_mis_date}..."
        )

        # Convert to list for parallel processing
        accounts_list = list(accounts_qs)

        def chunker(seq, size):
            for pos in range(0, len(seq), size):
                yield seq[pos:pos + size]

        # Parallel processing of accounts
        updated_accounts = []
        error_occurred = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for batch in chunker(accounts_list, batch_size):
                futures.append(
                    executor.submit(process_batch_of_accounts, batch)
                )

            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_result = future.result()
                    if batch_result is None:
                        error_occurred = True
                    else:
                        updated_accounts.extend(batch_result)
                except Exception as exc:
                    save_log(
                        'process_cooling_period_for_accounts',
                        'ERROR',
                        f"Thread batch processing error: {exc}"
                    )
                    error_occurred = True

        if error_occurred:
            # Return early if there's a major failure
            return 0

        # Bulk update all changes in sub-batches
        total_updates = len(updated_accounts)
        if total_updates == 0:
            save_log(
                'process_cooling_period_for_accounts',
                'INFO',
                "No records needed updating after processing logic."
            )
            return 0

        with transaction.atomic():
            for start in range(0, total_updates, update_batch_size):
                end = start + update_batch_size
                FCT_Stage_Determination.objects.bulk_update(
                    updated_accounts[start:end],
                    [
                        'n_in_cooling_period_flag',
                        'd_cooling_start_date',
                        'n_cooling_period_duration',
                        'n_target_ifrs_stage_skey',
                        'n_curr_ifrs_stage_skey',
                        'n_stage_descr',
                    ]
                )

        save_log(
            'process_cooling_period_for_accounts',
            'INFO',
            f"Successfully processed cooling periods for {total_updates} accounts on fic_mis_date={fic_mis_date}."
        )
        return 1

    except Exception as e:
        save_log(
            'process_cooling_period_for_accounts',
            'ERROR',
            f"Error during cooling period processing for fic_mis_date={fic_mis_date}: {e}"
        )
        return 0


def process_batch_of_accounts(batch):
    """
    Helper function to process a list (batch) of accounts and return updated accounts.
    """
    updated_local = []
    for account in batch:
        updated_acc = process_single_account(account)
        if updated_acc:
            updated_local.append(updated_acc)
    return updated_local


# import concurrent.futures
# from datetime import timedelta
# from ..models import CoolingPeriodDefinition, FCT_Stage_Determination
# from .save_log import save_log

# def get_previous_stage_and_cooling_status(account, fic_mis_date):
#     """
#     Get the latest previous stage and cooling period status for the account by checking the latest previous fic_mis_date
#     that is strictly before the input fic_mis_date.
#     """
#     previous_record = FCT_Stage_Determination.objects.filter(
#         n_account_number=account.n_account_number,
#         fic_mis_date__lt=fic_mis_date
#     ).order_by('-fic_mis_date').first()

#     if previous_record:
#         return previous_record.n_curr_ifrs_stage_skey, previous_record.n_in_cooling_period_flag
#     else:
#         return None, False

# def is_cooling_period_expired(account):
#     """
#     Check if the cooling period has expired based on the start date and expected duration.
#     """
#     if account.d_cooling_start_date:
#         days_in_cooling_period = (account.fic_mis_date - account.d_cooling_start_date).days
#         if days_in_cooling_period >= account.n_cooling_period_duration:
#             return True
#     return False

# def start_cooling_period(account, current_stage, target_stage, fic_mis_date):
#     """
#     Start a new cooling period for the account when moving from a higher to a lower stage.
#     """
#     try:
#         cooling_period_def = CoolingPeriodDefinition.objects.get(v_amrt_term_unit=account.v_amrt_term_unit)
#     except CoolingPeriodDefinition.DoesNotExist:
#         save_log('start_cooling_period', 'WARNING', f"Cooling period not defined for amortization unit {account.v_amrt_term_unit}. Skipping cooling period.")
#         return

#     account.d_cooling_start_date = fic_mis_date
#     account.n_target_ifrs_stage_skey = target_stage
#     account.n_in_cooling_period_flag = True
#     account.n_cooling_period_duration = cooling_period_def.n_cooling_period_days

# def process_single_account(account, fic_mis_date):
#     """
#     Process cooling period and stage determination for a single account.
#     """
#     current_stage = account.n_curr_ifrs_stage_skey
#     previous_stage, was_in_cooling_period = get_previous_stage_and_cooling_status(account, fic_mis_date)
    
#     if previous_stage:
#         if was_in_cooling_period:
#             if account.n_curr_ifrs_stage_skey >= previous_stage:
#                 account.n_in_cooling_period_flag = False
#                 account.d_cooling_start_date = None
#                 account.n_cooling_period_duration = None
#                 account.n_target_ifrs_stage_skey = None
#             else:
#                 if is_cooling_period_expired(account):
#                     account.n_in_cooling_period_flag = False
#                     account.n_target_ifrs_stage_skey = None
#                     account.n_curr_ifrs_stage_skey = current_stage
#                     account.n_stage_descr = f"Stage {current_stage}"
#                 else:
#                     account.n_curr_ifrs_stage_skey = previous_stage
#                     account.n_stage_descr = f"Stage {previous_stage}"
#                     return
#         else:
#             if current_stage < previous_stage:
#                 start_cooling_period(account, previous_stage, current_stage, fic_mis_date)
#                 account.n_curr_ifrs_stage_skey = previous_stage
#                 account.n_stage_descr = f"Stage {previous_stage}"
#             else:
#                 account.n_curr_ifrs_stage_skey = current_stage
#                 account.n_stage_descr = f"Stage {current_stage}"
#     else:
#         save_log('process_single_account', 'INFO', f"No previous stage found for account {account.n_account_number}.")

#     account.save()

# def process_cooling_period_for_accounts(fic_mis_date):
#     """
#     Process cooling period logic for accounts based on a given fic_mis_date using multi-threading.
#     """
#     try:
#         valid_amrt_term_units = CoolingPeriodDefinition.objects.values_list('v_amrt_term_unit', flat=True)
#         accounts_to_process = FCT_Stage_Determination.objects.filter(
#             fic_mis_date=fic_mis_date,
#             v_amrt_term_unit__in=valid_amrt_term_units
#         )

#         if not accounts_to_process.exists():
#             save_log('process_cooling_period_for_accounts', 'INFO', f"No accounts found for fic_mis_date {fic_mis_date} with valid amortization term units.")
#             return 0

#         updated_accounts_count = 0
#         with concurrent.futures.ThreadPoolExecutor() as executor:
#             futures = [executor.submit(process_single_account, account, fic_mis_date) for account in accounts_to_process]

#             for future in concurrent.futures.as_completed(futures):
#                 try:
#                     future.result()
#                     updated_accounts_count += 1
#                 except Exception as exc:
#                     save_log('process_cooling_period_for_accounts', 'ERROR', f"An error occurred during account processing: {exc}")
#                     return 0

#         save_log('process_cooling_period_for_accounts', 'INFO', f"Successfully processed cooling periods for {updated_accounts_count} accounts on fic_mis_date {fic_mis_date}.")
#         return 1

#     except Exception as e:
#         save_log('process_cooling_period_for_accounts', 'ERROR', f"Error during cooling period processing for fic_mis_date {fic_mis_date}: {str(e)}")
#         return 0
