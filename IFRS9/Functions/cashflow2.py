from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from datetime import date, timedelta
from ..models import *
from ..Functions import save_log


def get_payment_interval(repayment_type):
    """Determine the payment interval in days based on repayment type."""
    if repayment_type == 'D':
        return timedelta(days=1)  # Daily payments
    elif repayment_type == 'W':
        return timedelta(weeks=1)  # Weekly payments
    elif repayment_type == 'M':
        return timedelta(days=30)  # Monthly payments (approx. 30 days)
    elif repayment_type == 'Q':
        return timedelta(days=91)  # Quarterly payments (approx. 3 months)
    elif repayment_type == 'H':
        return timedelta(days=182)  # Semi-annual payments (approx. 6 months)
    elif repayment_type == 'Y':
        return timedelta(days=365)  # Annual payments
    else:
        # Default to monthly if repayment type is unrecognized
        return timedelta(days=30)
    

def calculate_cash_flows_for_loan(loan):
    with transaction.atomic():
        balance = loan.n_eop_bal  # Start with the current end-of-period balance
        current_date = loan.d_next_payment_date
        fixed_interest_rate = loan.n_curr_interest_rate  # Fixed interest rate
        withholding_tax = loan.n_wht_percent / 100  # WHT percentage as decimal
        management_fee_rate = loan.v_management_fee_rate  # Management fee rate (if applicable)
        cashflow_bucket = 1

        # Determine payment interval based on repayment type (e.g., 'M', 'Q', 'H', 'Y')
        payment_interval = get_payment_interval(loan.v_repayment_type)

        # Calculate the number of periods based on repayment type
        periods = ((loan.d_maturity_date - current_date).days // payment_interval.days) + 1
        principal_payment = balance / periods  # Fixed principal repaymen

        # Determine the management fee date for the current year
        management_fee_day = loan.d_start_date.day
        management_fee_month = loan.d_start_date.month
        management_fee_date = date(current_date.year, management_fee_month, management_fee_day)

        while current_date <= loan.d_maturity_date:
            # Calculate interest based on remaining balance and interest rate
            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 360)
            
            # Calculate WHT payment and net interest
            wht_payment = interest_payment * withholding_tax  # WHT is calculated on the interest
            interest_payment_net = interest_payment - wht_payment  # Subtract WHT from total interest
            
            # Check if the current date is the management fee date
            management_fee = 0
            if current_date == management_fee_date and management_fee_rate:
                # Calculate management fee and deduct WHT
                management_fee = balance * management_fee_rate
                wht_management_fee = management_fee * withholding_tax  # WHT on management fee
                management_fee_net = management_fee - wht_management_fee  # Net management fee after WHT
                
                # Set the management fee date for the next year
                management_fee_date = management_fee_date.replace(year=management_fee_date.year + 1)
            else:
                management_fee_net = 0

            # Total Payment (Principal + Net Interest + Participation Premium + Management Fee)
            total_payment = principal_payment + interest_payment_net + management_fee_net

            # Store the cash flow
            FSI_Expected_Cashflow.objects.create(
                fic_mis_date=loan.fic_mis_date,
                v_account_number=loan.v_account_number,
                n_cash_flow_bucket=cashflow_bucket,
                d_cash_flow_date=current_date,
                n_principal_payment=principal_payment,
                n_interest_payment=interest_payment + management_fee,  # Include net management fee in interest
                n_cash_flow_amount=total_payment,
                n_balance=balance - principal_payment,
                V_CCY_CODE=loan.v_ccy_code,
            )

            # Update balance and proceed to the next payment
            balance -= principal_payment
            current_date += payment_interval
            cashflow_bucket += 1

        # Handle cases where management fee date does not coincide with any scheduled payment date
        if management_fee_rate and current_date > management_fee_date:
            # Create a separate entry for the management fee if no payment was made on the exact management fee date
            FSI_Expected_Cashflow.objects.create(
                fic_mis_date=loan.fic_mis_date,
                v_account_number=loan.v_account_number,
                n_cash_flow_bucket=cashflow_bucket,
                d_cash_flow_date=management_fee_date,
                n_principal_payment=0,  # No principal repayment for management fee
                n_interest_payment=management_fee,  # Net management fee in interest column
                n_cash_flow_amount=management_fee_net,  # Total payment is the net management fee
                n_balance=balance,  # Balance remains unchanged
                V_CCY_CODE=loan.v_ccy_code,
            )
            cashflow_bucket += 1  # Increment bucket for separate management fee payment


from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from datetime import timedelta
from ..models import *

def calculate_cash_flows_for_loan(loan):
    with transaction.atomic():
        # Check if a payment schedule exists for this account and fic_mis_date
        payment_schedule = Ldn_Payment_Schedule.objects.filter(
            v_account_number=loan.v_account_number,
            fic_mis_date=loan.fic_mis_date
        ).order_by('d_payment_date')
        
        if payment_schedule.exists():
            # Use the payment schedule
            bucket = 1
            for schedule in payment_schedule:
                principal_payment = schedule.n_principal_payment_amt or 0
                interest_payment = schedule.n_interest_payment_amt or 0
                total_payment = principal_payment + interest_payment

                # Calculate the new balance
                balance = loan.n_eop_bal - principal_payment
                
                # Store the cash flow
                FSI_Expected_Cashflow.objects.create(
                    fic_mis_date=loan.fic_mis_date,
                    v_account_number=loan.v_account_number,
                    n_cash_flow_bucket=bucket,  # Bucket number based on payment date order
                    d_cash_flow_date=schedule.d_payment_date,
                    n_principal_payment=principal_payment,
                    n_interest_payment=interest_payment,
                    n_cash_flow_amount=total_payment,
                    n_balance=balance,
                    V_CCY_CODE=loan.v_ccy_code,
                )
                # Update the loan balance for the next iteration
                loan.n_eop_bal = balance
                bucket += 1  # Increment the bucket number for the next payment date
        else:
            # No payment schedule exists, proceed with projected cash flows as before
            current_date = loan.d_next_payment_date
            balance = loan.n_eop_bal
            interest_rate = loan.n_curr_interest_rate / 100  # Convert to decimal
            payment_freq = str(loan.v_interest_freq_unit).strip()  # Ensure it's a string and strip whitespace
            repayment_type = loan.v_repayment_type
            cashflow_bucket = 1

            # Determine payment frequency in days
            if payment_freq == 'D':
                payment_interval = timedelta(days=1)
            elif payment_freq == 'W':
                payment_interval = timedelta(weeks=1)
            elif payment_freq == 'M':
                payment_interval = timedelta(days=30)  # Approximate month (30 days)
            elif payment_freq == 'Q':
                payment_interval = timedelta(days=91)  # Approximate quarter (3 months)
            elif payment_freq == 'H':
                payment_interval = timedelta(days=182)  # Approximate half-year (6 months)
            elif payment_freq == 'Y':
                payment_interval = timedelta(days=365)  # Approximate year
            else:
                # Set a default payment interval and handle the case gracefully
                payment_interval = timedelta(days=30)  # Default to monthly if unknown

            while current_date <= loan.d_maturity_date:
                # Default interest payment to avoid UnboundLocalError
                interest_payment = 0.0

                # Calculate Interest Payment
                if payment_freq == 'M':
                    interest_payment = balance * (interest_rate / 12)  # Monthly interest
                elif payment_freq == 'Q':
                    interest_payment = balance * (interest_rate / 4)  # Quarterly interest
                elif payment_freq == 'H':
                    interest_payment = balance * (interest_rate / 2)  # Half-yearly interest
                elif payment_freq == 'Y':
                    interest_payment = balance * interest_rate  # Annual interest
                else:
                    # Use default monthly interest calculation if frequency is unrecognized
                    interest_payment = balance * (interest_rate / 12)

                # Calculate Principal Payment
                if repayment_type == 'bullet':
                    principal_payment = 0 if current_date < loan.d_maturity_date else balance
                elif repayment_type == 'amortized':
                    periods_remaining = ((loan.d_maturity_date - current_date).days // payment_interval.days)
                    if periods_remaining > 0:
                        annuity_factor = (1 - (1 + interest_rate / 12) ** -periods_remaining) / (interest_rate / 12)
                        total_payment = balance / annuity_factor
                        principal_payment = total_payment - interest_payment
                    else:
                        principal_payment = balance  # last payment pays off the balance

                # Calculate Total Payment
                total_payment = principal_payment + interest_payment

                # Update balance
                balance -= principal_payment

                # Store the cash flow
                FSI_Expected_Cashflow.objects.create(
                    fic_mis_date=loan.fic_mis_date,
                    v_account_number=loan.v_account_number,
                    n_cash_flow_bucket=cashflow_bucket,
                    d_cash_flow_date=current_date,
                    n_principal_payment=principal_payment,
                    n_interest_payment=interest_payment,
                    n_cash_flow_amount=total_payment,
                    n_balance=balance,
                    V_CCY_CODE=loan.v_ccy_code,
                )

                # Move to the next payment date
                current_date += payment_interval
                cashflow_bucket += 1

################################################3
def project_cash_flows(fic_mis_date):

    # Delete existing cash flows for the same fic_mis_date
    FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date).delete()
    # Filter loans by the given fic_mis_date
    loans = Ldn_Financial_Instrument.objects.filter(fic_mis_date=fic_mis_date)

    # Define the number of threads based on the number of loans and system capability
    num_threads = min(30, len(loans))  # Adjust number of threads as needed

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit all loans to be processed in separate threads
        futures = [executor.submit(calculate_cash_flows_for_loan, loan) for loan in loans]

        # Ensure all threads are completed
        for future in futures:
            future.result()  # This will raise exceptions if any occurred in the thread
