import concurrent.futures
from ..models import FCT_Stage_Determination, FSI_PD_Interpolated
from django.db.models import Q
from ..Functions import save_log

def calculate_pd_for_account(account, fic_mis_date, term_unit_to_periods):
    """
    Function to calculate 12-month PD and Lifetime PD for a single account.
    """
    # Determine amortization frequency and periods per year based on the amortization term unit
    amortization_periods = term_unit_to_periods.get(account.v_amrt_term_unit, 12)  # Default to 12 (monthly)
    print(f"Processing account {account.n_prod_code}: Amortization periods per year = {amortization_periods}")

    # Calculate the number of months and buckets to maturity
    if account.d_maturity_date and account.fic_mis_date:
        months_to_maturity = (account.d_maturity_date.year - account.fic_mis_date.year) * 12 + \
                             (account.d_maturity_date.month - account.fic_mis_date.month)
        buckets_to_maturity = months_to_maturity // (12 // amortization_periods)  # Convert months to buckets
        print(f"Account {account.n_prod_code}: Buckets to maturity = {buckets_to_maturity} (for {account.v_amrt_term_unit})")
    else:
        print(f"Skipping account {account.n_prod_code}: Missing dates")
        return  # Skip if dates are not available

    # Calculate the number of buckets needed for 12 months
    buckets_needed_for_12_months = 12 // (12 // amortization_periods)  # Adjust to term unit
    print(f"Account {account.n_prod_code}: Buckets needed to reach 12 months = {buckets_needed_for_12_months} (for {account.v_amrt_term_unit})")

    # Fetch the PD values for the calculated buckets
    try:
        # If the maturity is greater than 12 months, we calculate 12-Month PD and Lifetime PD separately
        if months_to_maturity > 12:
            # Fetch the 12-Month PD based on the calculated bucket for 12 months
            twelve_months_pd_record = FSI_PD_Interpolated.objects.get(
                Q(v_int_rating_code=account.n_credit_rating_code) | Q(v_delq_band_code=str(account.n_delq_band_code)),
                v_pd_term_structure_id=account.n_pd_term_structure_skey,
                v_cash_flow_bucket_id=buckets_needed_for_12_months
            )
            twelve_months_pd = twelve_months_pd_record.n_cumulative_default_prob
            print(f"Account {account.n_prod_code}: 12-month PD = {twelve_months_pd}")
            
            # Fetch the Lifetime PD based on the calculated bucket for maturity
            lifetime_pd_record = FSI_PD_Interpolated.objects.get(
                Q(v_int_rating_code=account.n_credit_rating_code) | Q(v_delq_band_code=str(account.n_delq_band_code)),
                v_pd_term_structure_id=account.n_pd_term_structure_skey,
                v_cash_flow_bucket_id=buckets_to_maturity
            )
            lifetime_pd = lifetime_pd_record.n_cumulative_default_prob
            print(f"Account {account.n_prod_code}: Lifetime PD = {lifetime_pd}")
        else:
            # If the maturity is less than or equal to 12 months, the 12-Month PD and Lifetime PD are the same
            pd_record = FSI_PD_Interpolated.objects.get(
                Q(v_int_rating_code=account.n_credit_rating_code) | Q(v_delq_band_code=str(account.n_delq_band_code)),
                v_pd_term_structure_id=account.n_pd_term_structure_skey,
                v_cash_flow_bucket_id=buckets_to_maturity
            )
            twelve_months_pd = pd_record.n_cumulative_default_prob
            lifetime_pd = pd_record.n_cumulative_default_prob
            print(f"Account {account.n_prod_code}: 12-month and Lifetime PD = {twelve_months_pd} (since maturity <= 12 months)")
    
    except FSI_PD_Interpolated.DoesNotExist:
        twelve_months_pd = None
        lifetime_pd = None
        print(f"Account {account.n_prod_code}: No PD records found for bucket {buckets_needed_for_12_months} or {buckets_to_maturity}")

    # Update the FCT_Stage_Determination table with the calculated PDs
    if twelve_months_pd:
        account.n_twelve_months_pd = twelve_months_pd
        print(f"Account {account.n_prod_code}: Updated 12-month PD = {twelve_months_pd}")
    if lifetime_pd:
        account.n_lifetime_pd = lifetime_pd
        print(f"Account {account.n_prod_code}: Updated Lifetime PD = {lifetime_pd}")

    account.save()
    print(f"Account {account.n_prod_code}: PD values successfully saved.")

def calculate_pd_for_accounts(fic_mis_date):
    """
    Main function to calculate the 12-month PD and Lifetime PD for accounts using multi-threading.
    """
    try:
        # Map v_amrt_term_unit to the number of periods in a year (buckets per year)
        term_unit_to_periods = {
            'M': 12,  # Monthly
            'Q': 4,   # Quarterly
            'H': 2,   # Half-Yearly
            'Y': 1    # Yearly
        }

        # Fetch all accounts for the given MIS date
        accounts = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date)
        total_accounts = accounts.count()

        # Print the number of records found
        print(f"Found {total_accounts} accounts for processing.")

        if total_accounts == 0:
            print("No accounts found for the given MIS date.")
            return 0  # Return 0 if no accounts are found

        # Use ThreadPoolExecutor for multi-threading
        updated_accounts = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit tasks to the executor for each account
            futures = {executor.submit(calculate_pd_for_account, account, fic_mis_date, term_unit_to_periods): account for account in accounts}

            # Process the results as they complete
            for future in concurrent.futures.as_completed(futures):
                account = futures[future]
                try:
                    future.result()  # This ensures any exceptions are raised
                    updated_accounts += 1
                    print(f"Successfully updated PD for account: {account.n_prod_code}")
                except Exception as e:
                    print(f"Error occurred while processing account {account.n_prod_code}: {e}")
                    return 0  # Return 0 if any error occurs

        # Print summary at the end
        print(f"{updated_accounts} out of {total_accounts} accounts were successfully updated.")

        # Return 1 if the function completes successfully without errors
        return 1

    except Exception as e:
        # Handle any unexpected errors
        print(f"An unexpected error occurred: {e}")
        return 0  # Return 0 in case of any other exceptions