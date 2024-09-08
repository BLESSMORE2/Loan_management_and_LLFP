from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from datetime import timedelta, date
from ..models import *


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
        return timedelta(days=180)  # Semi-annual payments (approx. 6 months)
    elif repayment_type == 'Y':
        return timedelta(days=365)  # Annual payments
    else:
        # Default to monthly if repayment type is unrecognized
        return timedelta(days=30)

def calculate_cash_flows_for_loan(loan):
    with transaction.atomic():
        # Check if a payment schedule exists for this account and fic_mis_date
        payment_schedule = Ldn_Payment_Schedule.objects.filter(
            v_account_number=loan.v_account_number,
            fic_mis_date=loan.fic_mis_date
        ).order_by('d_payment_date')

        balance = float(loan.n_eop_bal) if loan.n_eop_bal is not None else 0.0 # Start with the current end-of-period balance
        starting_balance = balance  # Keep track of the initial balance
        current_date = loan.d_next_payment_date
        fixed_interest_rate = float(loan.n_curr_interest_rate) if loan.n_curr_interest_rate is not None else 0.0 # Fixed interest rate
        withholding_tax = float(loan.n_wht_percent) if loan.n_wht_percent is not None else 0.0  # WHT percentage as decimal
        management_fee_rate =  float(loan.v_management_fee_rate) if loan.v_management_fee_rate is not None else 0.0 # Management fee rate (if applicable)
        v_amrt_term_unit = loan.v_amrt_term_unit
        repayment_type = loan.v_amrt_repayment_type  # Get amortization type (bullet/amortized)
        cashflow_bucket = 1

         # Fetch the interest method from Fsi_Interest_Method. Default to 'Simple' if none exists.
        interest_method = Fsi_Interest_Method.objects.first()  # Always fetch the first available method
        if not interest_method:
            interest_method = Fsi_Interest_Method.objects.create(v_interest_method='Simple', description="Default Simple Interest Method")

        # Determine payment interval based on repayment type (e.g., 'M', 'Q', 'H', 'Y')
        payment_interval = get_payment_interval(v_amrt_term_unit)

        # Management fee calculation
        management_fee_day = loan.d_start_date.day
        management_fee_month = loan.d_start_date.month
        management_fee_date = date(current_date.year, management_fee_month, management_fee_day)

        if payment_schedule.exists():
            # Use the payment schedule
            bucket = 1
            for schedule in payment_schedule:
                principal_payment = schedule.n_principal_payment_amt or 0
                interest_payment = schedule.n_interest_payment_amt or 0
                total_payment = principal_payment + interest_payment

                # Calculate the new balance
                balance -= principal_payment

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

                bucket += 1  # Increment the bucket number for the next payment date
        else:
            # No payment schedule exists, proceed with projected cash flows
            periods = ((loan.d_maturity_date - current_date).days // payment_interval.days) + 1
            fixed_principal_payment = round(starting_balance / periods, 2)
            total_principal_paid = 0
            print('periods')
            print(periods)
            total_principal_paid = 0  # Track total principal paid

            while current_date <= loan.d_maturity_date:
                # Default interest payment to avoid UnboundLocalError
                interest_payment = 0.0

                # Interest Calculation based on the method selected
                if interest_method.v_interest_method == 'Simple':
                    # Simple Interest
                    if v_amrt_term_unit == 'M':
                            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 30)  # Monthly interest
                    elif v_amrt_term_unit == 'Q':
                            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 360)# Quarterly interest
                    elif v_amrt_term_unit == 'H':
                            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 360)  # Semi-annual interest
                    elif v_amrt_term_unit == 'Y':
                            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 365) # Annual interest
                    else:
                        interest_payment = balance * fixed_interest_rate * (payment_interval.days / 365)

                elif interest_method.v_interest_method == 'Compound':
                    # Calculate Interest Payment based on the frequency (M, Q, H, Y)
                    if v_amrt_term_unit == 'M':
                        interest_payment = balance * ((1 + fixed_interest_rate / 12) ** periods - 1)  # Monthly interest
                    elif v_amrt_term_unit == 'Q':
                        interest_payment = balance * ((1 + fixed_interest_rate / 4) ** periods - 1) # Quarterly interest
                    elif v_amrt_term_unit == 'H':
                        interest_payment = balance * ((1 + fixed_interest_rate / 2) ** periods - 1)  # Semi-annual interest
                    elif v_amrt_term_unit == 'Y':
                        interest_payment = balance * fixed_interest_rate  # Annual interest
                    else:
                        # Use default monthly interest calculation if frequency is unrecognized
                        interest_payment = balance * ((1 + fixed_interest_rate /12) ** periods - 1)
                 
                elif interest_method.v_interest_method == 'Amortized':
                    # Amortized Interest
                    # Check if fixed_interest_rate is annual, adjust as needed if it's monthly, quarterly, etc.
                    if v_amrt_term_unit == 'Y':
                        interest_rate_per_period = fixed_interest_rate  # Annual to per-period rate
                    elif v_amrt_term_unit == 'M':
                        interest_rate_per_period = fixed_interest_rate / 12  # Convert annual rate to monthly
                    elif v_amrt_term_unit == 'Q':
                        interest_rate_per_period = fixed_interest_rate / 4  # Convert annual rate to quarterly
                    elif v_amrt_term_unit == 'H':
                        interest_rate_per_period = fixed_interest_rate / 2  # Convert annual rate to semi-annual
                    else:
                        # Default to annual rate
                        interest_rate_per_period = fixed_interest_rate / 12
                    # Calculate total payment (fixed payment for each period)
                    total_payment = loan.n_eop_bal * (interest_rate_per_period / (1 - (1 + interest_rate_per_period) ** -periods))
                    # Calculate interest payment for the current period
                    interest_payment = balance * interest_rate_per_period
                    # Principal payment is the difference between the total payment and the interest payment
                    principal_payment = total_payment - interest_payment          

                elif interest_method.v_interest_method == 'Floating':
                    # Floating/Variable Interest Rate
                    if v_amrt_term_unit == 'M':
                        variable_rate = loan.n_curr_interest_rate + loan.n_variable_rate_margin
                        interest_payment = balance * variable_rate * (payment_interval.days / 30)  # Monthly interest
                    elif v_amrt_term_unit == 'Q':
                        variable_rate = loan.n_curr_interest_rate + loan.n_variable_rate_margin
                        interest_payment = balance * variable_rate * (payment_interval.days / 91)  # Monthly interest# Quarterly interest
                    elif v_amrt_term_unit == 'H':
                        variable_rate = loan.n_curr_interest_rate + loan.n_variable_rate_margin
                        interest_payment = balance * variable_rate * (payment_interval.days / 180)  # Monthly interest  # Semi-annual interest
                    elif v_amrt_term_unit == 'Y':
                        variable_rate = loan.n_curr_interest_rate + loan.n_variable_rate_margin
                        interest_payment = balance * variable_rate * (payment_interval.days / 365)  # Monthly interest # Annual interest
                    else:
                        interest_payment = balance * fixed_interest_rate * (payment_interval.days / 30)

                else :
                    # Simple Interest
                    if v_amrt_term_unit == 'M':
                            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 30)  # Monthly interest
                    elif v_amrt_term_unit == 'Q':
                            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 91)# Quarterly interest
                    elif v_amrt_term_unit == 'H':
                            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 182)  # Semi-annual interest
                    elif v_amrt_term_unit == 'Y':
                            interest_payment = balance * fixed_interest_rate * (payment_interval.days / 365) # Annual interest
                    else:
                        interest_payment = balance * fixed_interest_rate * (payment_interval.days / 365)
                

                    
                    

                # Calculate WHT payment and net interest
                wht_payment = interest_payment * withholding_tax  # WHT is calculated on the interest
                interest_payment_net = interest_payment - wht_payment  # Subtract WHT from total interest

                # Calculate Principal Payment based on the amortization type
                if repayment_type == 'bullet':
                    principal_payment = 0 if current_date < loan.d_maturity_date else balance
                elif repayment_type == 'amortized':
                        principal_payment = fixed_principal_payment
                  # Last payment clears the balance

            

                total_principal_paid += principal_payment  # Track total principal paid

                # Check if the current date is the management fee date
                management_fee_net = 0
                if current_date == management_fee_date and management_fee_rate:
                    management_fee = balance * management_fee_rate
                    wht_management_fee = management_fee * withholding_tax  # WHT on management fee
                    management_fee_net = management_fee - wht_management_fee  # Net management fee after WHT
                    
                    # Set the management fee date for the next year
                    management_fee_date = management_fee_date.replace(year=management_fee_date.year + 1)

                # Total Payment (Principal + Net Interest + Management Fee if applicable)
                total_payment = principal_payment + interest_payment_net + management_fee_net

                # Store the cash flow
                FSI_Expected_Cashflow.objects.create(
                    fic_mis_date=loan.fic_mis_date,
                    v_account_number=loan.v_account_number,
                    n_cash_flow_bucket=cashflow_bucket,
                    d_cash_flow_date=current_date,
                    n_principal_payment=principal_payment,
                    n_interest_payment=interest_payment + management_fee_net,  # Include net management fee in interest
                    n_cash_flow_amount=total_payment,
                    n_balance=balance - principal_payment,
                    V_CCY_CODE=loan.v_ccy_code,
                )

                # Update balance and proceed to the next payment
                balance -= principal_payment
                current_date += payment_interval
                cashflow_bucket += 1
                periods -= 1  # Decrease the number of remaining periods

            # Handle cases where management fee date does not coincide with any scheduled payment date
            if management_fee_rate and current_date > management_fee_date:
                # Create a separate entry for the management fee if no payment was made on the exact management fee date
                FSI_Expected_Cashflow.objects.create(
                    fic_mis_date=loan.fic_mis_date,
                    v_account_number=loan.v_account_number,
                    n_cash_flow_bucket=cashflow_bucket,
                    d_cash_flow_date=management_fee_date,
                    n_principal_payment=0,  # No principal repayment for management fee
                    n_interest_payment=management_fee_net,  # Net management fee in interest column
                    n_cash_flow_amount=management_fee_net,  # Total payment is the net management fee
                    n_balance=balance,  # Balance remains unchanged
                    V_CCY_CODE=loan.v_ccy_code,
                )
                cashflow_bucket += 1  # Increment bucket for separate management fee payment


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
