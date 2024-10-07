import concurrent.futures
from django.db import transaction
from ..models import FCT_Stage_Determination, FSI_PD_Account_Interpolated
from .save_log import save_log

def calculate_account_level_pd_for_account(account, fic_mis_date, term_unit_to_periods):
    """
    Function to calculate 12-month PD and Lifetime PD for a single account using account-level interpolated PD data.
    """
    amortization_periods = term_unit_to_periods.get(account.v_amrt_term_unit, 12)  # Default to 12 (monthly)
    try:
        # Calculate the number of months and buckets to maturity
        if account.d_maturity_date and account.fic_mis_date:
            months_to_maturity = (account.d_maturity_date.year - account.fic_mis_date.year) * 12 + \
                                 (account.d_maturity_date.month - account.fic_mis_date.month)
            buckets_to_maturity = months_to_maturity // (12 // amortization_periods)
            save_log('calculate_account_level_pd_for_account', 'INFO', f"Account {account.n_prod_code}: Buckets to maturity = {buckets_to_maturity} (for {account.v_amrt_term_unit})")
        else:
            save_log('calculate_account_level_pd_for_account', 'WARNING', f"Skipping account {account.n_prod_code}: Missing dates")
            return

        buckets_needed_for_12_months = 12 // (12 // amortization_periods)
        save_log('calculate_account_level_pd_for_account', 'INFO', f"Account {account.n_prod_code}: Buckets needed for 12-month PD = {buckets_needed_for_12_months}")

        # Fetch PD records based on maturity
        if months_to_maturity > 12:
            twelve_months_pd_record = FSI_PD_Account_Interpolated.objects.get(
                v_account_number=account.n_account_number,
                fic_mis_date=fic_mis_date,
                v_cash_flow_bucket_id=buckets_needed_for_12_months
            )
            twelve_months_pd = twelve_months_pd_record.n_cumulative_default_prob
            save_log('calculate_account_level_pd_for_account', 'INFO', f"Account {account.n_prod_code}: 12-month PD = {twelve_months_pd}")

            lifetime_pd_record = FSI_PD_Account_Interpolated.objects.get(
                v_account_number=account.n_account_number,
                fic_mis_date=fic_mis_date,
                v_cash_flow_bucket_id=buckets_to_maturity
            )
            lifetime_pd = lifetime_pd_record.n_cumulative_default_prob
            save_log('calculate_account_level_pd_for_account', 'INFO', f"Account {account.n_prod_code}: Lifetime PD = {lifetime_pd}")
        else:
            pd_record = FSI_PD_Account_Interpolated.objects.get(
                v_account_number=account.n_account_number,
                fic_mis_date=fic_mis_date,
                v_cash_flow_bucket_id=buckets_to_maturity
            )
            twelve_months_pd = pd_record.n_cumulative_default_prob
            lifetime_pd = pd_record.n_cumulative_default_prob
            save_log('calculate_account_level_pd_for_account', 'INFO', f"Account {account.n_prod_code}: 12-month and Lifetime PD (same for short maturity) = {twelve_months_pd}")

        # Update the account with calculated PDs
        if twelve_months_pd is not None:
            account.n_twelve_months_pd = twelve_months_pd
            save_log('calculate_account_level_pd_for_account', 'INFO', f"Account {account.n_prod_code}: Updated 12-month PD = {twelve_months_pd}")
        if lifetime_pd is not None:
            account.n_lifetime_pd = lifetime_pd
            save_log('calculate_account_level_pd_for_account', 'INFO', f"Account {account.n_prod_code}: Updated Lifetime PD = {lifetime_pd}")

        account.save()
        save_log('calculate_account_level_pd_for_account', 'INFO', f"Account {account.n_prod_code}: PD values successfully saved.")

    except FSI_PD_Account_Interpolated.DoesNotExist:
        save_log('calculate_account_level_pd_for_account', 'WARNING', f"Account {account.n_prod_code}: No PD records found for bucket {buckets_needed_for_12_months} or {buckets_to_maturity}")
    except Exception as e:
        save_log('calculate_account_level_pd_for_account', 'ERROR', f"Account {account.n_prod_code}: Error calculating PD values: {e}")

def calculate_account_level_pd_for_accounts(fic_mis_date):
    """
    Main function to calculate the 12-month PD and Lifetime PD for accounts using multi-threading and account-level PDs.
    """
    try:
        term_unit_to_periods = {
            'M': 12,  # Monthly
            'Q': 4,   # Quarterly
            'H': 2,   # Half-Yearly
            'Y': 1    # Yearly
        }

        accounts = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date)
        total_accounts = accounts.count()
        save_log('calculate_account_level_pd_for_accounts', 'INFO', f"Found {total_accounts} accounts for processing.")

        if total_accounts == 0:
            save_log('calculate_account_level_pd_for_accounts', 'INFO', "No accounts found for the given MIS date.")
            return 0

        updated_accounts = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(calculate_account_level_pd_for_account, account, fic_mis_date, term_unit_to_periods): account for account in accounts}

            for future in concurrent.futures.as_completed(futures):
                account = futures[future]
                try:
                    future.result()  # Raise any exceptions
                    updated_accounts += 1
                    save_log('calculate_account_level_pd_for_accounts', 'INFO', f"Successfully updated PD for account: {account.n_prod_code}")
                except Exception as e:
                    save_log('calculate_account_level_pd_for_accounts', 'ERROR', f"Error occurred while processing account {account.n_prod_code}: {e}")
                    return 0

        save_log('calculate_account_level_pd_for_accounts', 'INFO', f"{updated_accounts} out of {total_accounts} accounts were successfully updated.")
        return 1

    except Exception as e:
        save_log('calculate_account_level_pd_for_accounts', 'ERROR', f"An unexpected error occurred: {e}")
        return 0
