import concurrent.futures
from ..models import FSI_Expected_Cashflow, fsi_Financial_Cash_Flow_Cal, Dim_Run
from django.db import transaction
from django.db import models

def get_next_run_skey():
    """
    Retrieve the current n_run_skey from the RunKey table and return the next value.
    If no records exist, start with 1.
    """
    # Get the current run_skey from the RunKey table
    try:
        run_key_record = Dim_Run.objects.first()
        if run_key_record is None:
            # If the RunKey table is empty, start with 1
            return 1
        else:
            return run_key_record.latest_run_skey + 1
    except Dim_Run.DoesNotExist:
        return 1  # Start at 1 if the RunKey table doesn't exist or is empty

def update_run_key(next_run_skey):
    """
    Update the RunKey table with the latest run_skey.
    """
    run_key_record, created = Dim_Run.objects.get_or_create(id=1)  # Ensure there's always one RunKey record
    run_key_record.latest_run_skey = next_run_skey
    run_key_record.save()

def insert_cash_flow_record(cashflow, run_skey):
    """
    Function to insert a single cash flow record into fsi_Financial_Cash_Flow_Cal.
    This function is called by multiple threads.
    """
    try:
        # Create a dictionary to hold only the fields that have non-None values
        data_to_insert = {
            'v_account_number': cashflow.v_account_number,
            'd_cash_flow_date': cashflow.d_cash_flow_date,
            'n_run_skey': run_skey,  # Use the provided run_skey for all records in the batch
            'fic_mis_date': cashflow.fic_mis_date,
            'n_principal_run_off': cashflow.n_principal_payment,
            'n_interest_run_off': cashflow.n_interest_payment,
            'n_cash_flow_bucket_id': cashflow.n_cash_flow_bucket,
            'n_cash_flow_amount': cashflow.n_cash_flow_amount,
            'v_ccy_code': cashflow.V_CCY_CODE,
            'n_exposure_at_default':cashflow.n_exposure_at_default
        }

        # Insert the data into fsi_Financial_Cash_Flow_Cal
        fsi_Financial_Cash_Flow_Cal.objects.create(**data_to_insert)
        return True  # Successful insert

    except Exception as e:
        # Handle any exception that may occur during the insert operation
        print(f"Error inserting data for account {cashflow.v_account_number} on {cashflow.d_cash_flow_date}: {e}")
        return False  # Failed insert

def insert_cash_flow_data(fic_mis_date):
    """
    Function to insert data from FSI_Expected_Cashflow into fsi_Financial_Cash_Flow_Cal, excluding fields that are None.
    Also prints the number of selected and inserted records. Multi-threading is used for faster inserts.
    """
    # Fetch all records from FSI_Expected_Cashflow for the given MIS date
    expected_cashflows = FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date)
    total_selected = expected_cashflows.count()  # Get total number of selected rows
    total_inserted = 0  # Counter for the number of rows inserted

    # Print the number of rows selected
    print(f"Number of rows selected: {total_selected}")

    # Get the next run_skey
    next_run_skey = get_next_run_skey()
    print(f"Using n_run_skey = {next_run_skey} for this batch of inserts.")

    # Use ThreadPoolExecutor for multi-threading
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks to the executor for each cashflow record
        futures = [executor.submit(insert_cash_flow_record, cashflow, next_run_skey) for cashflow in expected_cashflows]

        # Process the results as they complete
        for future in concurrent.futures.as_completed(futures):
            if future.result():  # If the insertion was successful
                total_inserted += 1

    # Update the RunKey table with the latest run_skey
    update_run_key(next_run_skey)

    # Print the number of rows successfully inserted
    print(f"Number of rows inserted: {total_inserted}")

# Example usage
insert_cash_flow_data(fic_mis_date='2024-09-17')
