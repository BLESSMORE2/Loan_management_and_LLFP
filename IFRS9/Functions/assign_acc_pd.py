import concurrent.futures
from ..models import FCT_Stage_Determination, FSI_PD_Interpolated
from django.db.models import Q

def calculate_pd_for_account(account, fic_mis_date, term_unit_to_periods):
    """
    Function to calculate 12-month PD and Lifetime PD for a single account.
    """
    # Determine amortization frequency and periods per year
    amortization_periods = term_unit_to_periods.get(account.v_amrt_term_unit, 12)  # Default to 12 (monthly)

    # Calculate the number of months to maturity
    if account.d_maturity_date and account.fic_mis_date:
        months_to_maturity = (account.d_maturity_date.year - account.fic_mis_date.year) * 12 + \
                             (account.d_maturity_date.month - account.fic_mis_date.month)
    else:
        return  # Skip if dates are not available

    # Fetch PD records based on the account's rating, delinquency band, and PD term structure
    pd_records = FSI_PD_Interpolated.objects.filter(
    fic_mis_date=fic_mis_date,
                Q(v_int_rating_code=account.n_credit_rating_code) | Q(v_delq_band_code=str(account.n_delq_band_skey)),
                v_pd_term_structure_type=account.n_pd_term_structure_skey
                )


    # Initialize PD values
    twelve_months_pd = None
    lifetime_pd = None

    # For accounts with maturity greater than 12 months
    if months_to_maturity > 12:
        for pd_record in pd_records:
            # Convert cash flow bucket unit to monthly periods (e.g., if PD is in quarterly terms)
            if pd_record.v_cash_flow_bucket_unit == 'M':
                periods_per_bucket = 1  # 1 month per bucket (monthly)
            elif pd_record.v_cash_flow_bucket_unit == 'Q':
                periods_per_bucket = 3  # 3 months per bucket (quarterly)
            elif pd_record.v_cash_flow_bucket_unit == 'H':
                periods_per_bucket = 6  # 6 months per bucket (half-yearly)
            elif pd_record.v_cash_flow_bucket_unit == 'Y':
                periods_per_bucket = 12  # 12 months per bucket (yearly)
            else:
                periods_per_bucket = 1  # Default to monthly

            # Calculate 12-month PD if available
            if pd_record.v_cash_flow_bucket_id * periods_per_bucket <= 12:
                twelve_months_pd = pd_record.n_cumulative_default_prob

            # Calculate Lifetime PD if it corresponds to the maturity period
            if pd_record.v_cash_flow_bucket_id * periods_per_bucket >= months_to_maturity:
                lifetime_pd = pd_record.n_cumulative_default_prob
    else:
        # For accounts with maturity less than or equal to 12 months
        for pd_record in pd_records:
            if pd_record.v_cash_flow_bucket_id * periods_per_bucket >= months_to_maturity:
                twelve_months_pd = pd_record.n_cumulative_default_prob
                lifetime_pd = pd_record.n_cumulative_default_prob

    # Update the FCT_Stage_Determination table with the calculated PDs
    if twelve_months_pd:
        account.n_twelve_months_pd = twelve_months_pd
    if lifetime_pd:
        account.n_lifetime_pd = lifetime_pd

    account.save()


def calculate_pd_for_accounts(fic_mis_date):
    """
    Main function to calculate the 12-month PD and Lifetime PD for accounts using multi-threading.
    """
    # Map v_amrt_term_unit to the number of periods in a year
    term_unit_to_periods = {
        'M': 12,  # Monthly
        'Q': 4,   # Quarterly
        'H': 2,   # Half-Yearly
        'Y': 1    # Yearly
    }

    # Fetch all accounts for the given MIS date
    accounts = FCT_Stage_Determination.objects.filter(fic_mis_date=fic_mis_date)

    # Use ThreadPoolExecutor for multi-threading
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks to the executor for each account
        futures = [executor.submit(calculate_pd_for_account, account, fic_mis_date, term_unit_to_periods) for account in accounts]

        # Process the results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # This ensures any exceptions are raised
            except Exception as e:
                print(f"Error occurred: {e}")

# Example usage
calculate_pd_for_accounts(fic_mis_date='2024-09-17')
