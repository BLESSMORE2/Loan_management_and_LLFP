from django.db import transaction
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from ..models import FSI_Expected_Cashflow, Ldn_Financial_Instrument

# Accrued interest calculation function based on day count convention
def calculate_accrued_interest(principal, interest_rate, days, day_count_ind):
    """
    Calculate accrued interest using the given day count convention.
    - For '30/360': Interest is calculated on a 360-day year.
    - For '30/365': Interest is calculated on a 365-day year.
    Formula: Interest = Principal * (Interest Rate / 100) * (Days / DayCount)
    """
    if day_count_ind == '30/360':
        day_count = Decimal(360)
    elif day_count_ind == '30/365':
        day_count = Decimal(365)
    else:
        # Default to 365 if day_count_ind is unrecognized
        print(f"Warning: Unknown day_count_ind '{day_count_ind}', defaulting to 365.")
        day_count = Decimal(365)

    # Ensure principal and interest_rate are Decimal
    accrued_interest = principal * (interest_rate / Decimal(100)) * (Decimal(days) / day_count)
    print(f"Accrued interest for {days} days: {accrued_interest:.2f}")
    return accrued_interest

# Function to calculate EAD and Accrued Interest for a specific cash flow bucket
def calculate_exposure_and_accrued_interest(loan, cash_flow, previous_cash_flow_date):
    """
    Calculate both EAD (Exposure at Default) and Accrued Interest for a specific cash flow bucket.
    EAD is calculated by considering the principal balance and accrued interest.
    """
    try:
        # Step 1: Get the outstanding principal balance for the current bucket
        n_balance = cash_flow.n_balance

        # Ensure the balance is in Decimal type
        n_balance = Decimal(n_balance)

        # Step 2: Initialize EAD with the current principal balance
        n_exposure_at_default = n_balance

        # Step 3: Calculate accrued interest based on days between previous cash flow date and current bucket's cash flow date
        if loan.n_curr_interest_rate:
            interest_rate = Decimal(loan.n_curr_interest_rate)
            days_since_last_payment = (cash_flow.d_cash_flow_date - previous_cash_flow_date).days

            accrued_interest = calculate_accrued_interest(
                n_balance,
                interest_rate,
                days_since_last_payment,
                loan.v_day_count_ind  # Use day count convention from the loan
            )
            
            # Step 4: Add accrued interest to EAD and store accrued interest in the cash flow
            n_exposure_at_default += accrued_interest
            cash_flow.n_accrued_interest = accrued_interest  # Store accrued interest
            print(f"EAD for account {loan.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {n_exposure_at_default:.2f}")

        return n_exposure_at_default
    except Exception as e:
        print(f"Error calculating EAD and accrued interest for account {loan.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {e}")
        return None

# Function to process and update EAD and accrued interest for a list of cash flows (used for bulk update)
def process_cash_flows(cash_flows, fic_mis_date):
    """
    Processes a list of cash flow records and updates their Exposure at Default (EAD) and accrued interest.
    This function is designed to be run in a thread.
    """
    bulk_updates = []
    previous_cash_flow_date = None

    for cash_flow in cash_flows:
        try:
            # Fetch the corresponding loan details
            loan = Ldn_Financial_Instrument.objects.get(v_account_number=cash_flow.v_account_number, fic_mis_date=fic_mis_date)

            # Use d_last_payment_date for the first bucket, otherwise use previous cash flow date
            if previous_cash_flow_date is None:
                previous_cash_flow_date = loan.d_last_payment_date or cash_flow.d_cash_flow_date

            # Calculate EAD and accrued interest for each cash flow bucket
            n_exposure_at_default = calculate_exposure_and_accrued_interest(loan, cash_flow, previous_cash_flow_date)

            # Update the cash flow if EAD was calculated successfully
            if n_exposure_at_default is not None:
                cash_flow.n_exposure_at_default = n_exposure_at_default
                bulk_updates.append(cash_flow)

            # Update the previous cash flow date for the next iteration
            previous_cash_flow_date = cash_flow.d_cash_flow_date

        except Exception as e:
            print(f"Error processing cash flow for account {cash_flow.v_account_number}, bucket {cash_flow.n_cash_flow_bucket}: {e}")

    # Perform bulk update and catch any errors during the bulk update process
    try:
        FSI_Expected_Cashflow.objects.bulk_update(bulk_updates, ['n_exposure_at_default', 'n_accrued_interest'])
        print(f"Successfully updated {len(bulk_updates)} cash flows.")
    except Exception as e:
        print(f"Error during bulk update: {e}")

# Main function to update cash flow buckets with multi-threading and bulk update
def update_cash_flows_with_ead(fic_mis_date, max_workers=8, batch_size=1000):
    """
    Update all cash flow buckets with Exposure at Default (EAD) and Accrued Interest using multi-threading and bulk updates.
    """
    try:
        # Fetch all cash flow records that need to be updated
        cash_flows = FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date).order_by('d_cash_flow_date')

        total_cash_flows = cash_flows.count()
        if total_cash_flows == 0:
            print(f"No cash flows found for fic_mis_date {fic_mis_date}.")
            return

        # Split cash flows into batches
        cash_flow_batches = [cash_flows[i:i + batch_size] for i in range(0, total_cash_flows, batch_size)]

        print(f"Processing {total_cash_flows} cash flow buckets in {len(cash_flow_batches)} batches...")

        # Use multi-threading to process each batch
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_cash_flows, batch, fic_mis_date) for batch in cash_flow_batches]

            # Wait for all threads to complete
            for future in futures:
                try:
                    future.result()
                except Exception as exc:
                    print(f"Thread encountered an error: {exc}")

        print(f"Updated {total_cash_flows} cash flow buckets with Exposure at Default and Accrued Interest.")

    except Exception as e:
        print(f"Error updating cash flows for fic_mis_date {fic_mis_date}: {e}")


