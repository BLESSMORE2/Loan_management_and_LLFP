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
