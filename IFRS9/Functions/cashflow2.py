from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from datetime import timedelta, date
from ..models import *
from .save_log import save_log


def get_payment_interval(v_amrt_term_unit, day_count_ind):
    """Determine the payment interval in days based on repayment type and day count convention."""
    if day_count_ind == '30/360':
        if v_amrt_term_unit == 'D':
            return timedelta(days=1)
        elif v_amrt_term_unit == 'W':
            return timedelta(weeks=1)
        elif v_amrt_term_unit == 'M':
            return timedelta(days=30)
        elif v_amrt_term_unit == 'Q':
            return timedelta(days=90)
        elif v_amrt_term_unit == 'H':
            return timedelta(days=180)
        elif v_amrt_term_unit == 'Y':
            return timedelta(days=360)
        else:
            return timedelta(days=30)

    elif day_count_ind == '30/365':
        if v_amrt_term_unit == 'D':
            return timedelta(days=1)
        elif v_amrt_term_unit == 'W':
            return timedelta(weeks=1)
        elif v_amrt_term_unit == 'M':
            return timedelta(days=30)
        elif v_amrt_term_unit == 'Q':
            return timedelta(days=91)
        elif v_amrt_term_unit == 'H':
            return timedelta(days=182)
        elif v_amrt_term_unit == 'Y':
            return timedelta(days=365)
        else:
            return timedelta(days=30)
    else:
        return timedelta(days=30)


def calculate_cash_flows_for_loan(loan):
    try:
        with transaction.atomic():
            # Check if a payment schedule exists for this account and fic_mis_date
            payment_schedule = Ldn_Payment_Schedule.objects.filter(
                v_account_number=loan.v_account_number,
                fic_mis_date=loan.fic_mis_date
            ).order_by('d_payment_date')

            balance = float(loan.n_eop_bal) if loan.n_eop_bal is not None else 0.0
            starting_balance = balance
            current_date = loan.d_next_payment_date
            fixed_interest_rate = float(loan.n_curr_interest_rate) if loan.n_curr_interest_rate is not None else 0.0
            withholding_tax = float(loan.n_wht_percent) if loan.n_wht_percent is not None else 0.0
            management_fee_rate = float(loan.v_management_fee_rate) if loan.v_management_fee_rate is not None else 0.0
            v_amrt_term_unit = loan.v_amrt_term_unit
            repayment_type = loan.v_amrt_repayment_type
            v_day_count_ind = loan.v_day_count_ind
            cashflow_bucket = 1

            interest_method = Fsi_Interest_Method.objects.first() or Fsi_Interest_Method.objects.create(
                v_interest_method='Simple', description="Default Simple Interest Method"
            )

            payment_interval = get_payment_interval(v_amrt_term_unit, v_day_count_ind)
            if payment_interval.days == 0:
                raise ValueError("Invalid payment interval: days cannot be zero")

            periods = ((loan.d_maturity_date - current_date).days // payment_interval.days) + 1
            if periods <= 0:
                raise ValueError("Invalid periods calculation: 'periods' must be greater than zero")

            if payment_schedule.exists():
                bucket = 1
                for schedule in payment_schedule:
                    principal_payment = schedule.n_principal_payment_amt or 0.0
                    interest_payment = schedule.n_interest_payment_amt or 0.0
                    total_payment = principal_payment + interest_payment
                    balance -= principal_payment

                    FSI_Expected_Cashflow.objects.create(
                        fic_mis_date=loan.fic_mis_date,
                        v_account_number=loan.v_account_number,
                        n_cash_flow_bucket=bucket,
                        d_cash_flow_date=schedule.d_payment_date,
                        n_principal_payment=principal_payment,
                        n_interest_payment=interest_payment,
                        n_cash_flow_amount=total_payment,
                        n_balance=balance,
                        V_CCY_CODE=loan.v_ccy_code,
                    )
                    bucket += 1
            else:
                fixed_principal_payment = round(starting_balance / periods, 2)

                while current_date <= loan.d_maturity_date:
                    principal_payment = 0.0
                    if v_day_count_ind == '30/360':
                        day_count_factor = 360
                    elif v_day_count_ind == '30/365':
                        day_count_factor = 365
                    else:
                        day_count_factor = 365

                    if interest_method.v_interest_method == 'Simple':
                        interest_payment = balance * fixed_interest_rate * (payment_interval.days / day_count_factor)
                    elif interest_method.v_interest_method == 'Compound':
                        interest_payment = balance * ((1 + fixed_interest_rate / (day_count_factor / payment_interval.days)) ** periods - 1)
                    elif interest_method.v_interest_method == 'Amortized':
                        interest_rate_per_period = fixed_interest_rate / (day_count_factor / payment_interval.days)
                        if interest_rate_per_period == 0 or periods <= 0:
                            raise ValueError("Invalid interest rate per period or periods for amortized calculation")
                        total_payment = starting_balance * (interest_rate_per_period / (1 - (1 + interest_rate_per_period) ** -periods))
                        interest_payment = balance * interest_rate_per_period
                        principal_payment = total_payment - interest_payment
                    elif interest_method.v_interest_method == 'Floating':
                        variable_rate = loan.n_curr_interest_rate + loan.n_variable_rate_margin
                        interest_payment = balance * variable_rate * (payment_interval.days / day_count_factor)
                    else:
                        interest_payment = balance * fixed_interest_rate * (payment_interval.days / day_count_factor)

                    wht_payment = interest_payment * withholding_tax
                    interest_payment_net = interest_payment - wht_payment

                    if repayment_type == 'bullet':
                        if periods == 1:
                            principal_payment = balance
                        else:
                            principal_payment = 0
                    elif repayment_type == 'amortized':
                        principal_payment = fixed_principal_payment
                    else:
                        raise ValueError(f"Unsupported repayment type: '{repayment_type}' for account {loan.v_account_number}")

                    management_fee_net = 0.0
                    management_fee_day = loan.d_start_date.day
                    management_fee_month = loan.d_start_date.month
                    management_fee_date = date(current_date.year, management_fee_month, management_fee_day)
                    if current_date.month == management_fee_date.month and current_date.year == management_fee_date.year and management_fee_rate:
                        management_fee_net = balance * management_fee_rate
                        wht_management_fee = management_fee_net * withholding_tax
                        management_fee_net -= wht_management_fee
                        management_fee_date = management_fee_date.replace(year=management_fee_date.year + 1)

                    total_payment = principal_payment + interest_payment_net + management_fee_net

                    FSI_Expected_Cashflow.objects.create(
                        fic_mis_date=loan.fic_mis_date,
                        v_account_number=loan.v_account_number,
                        n_cash_flow_bucket=cashflow_bucket,
                        d_cash_flow_date=current_date,
                        n_principal_payment=principal_payment,
                        n_interest_payment=interest_payment + management_fee_net,
                        n_cash_flow_amount=total_payment,
                        n_balance=balance - principal_payment,
                        V_CASH_FLOW_TYPE=repayment_type,
                        management_fee_added=management_fee_net,
                        V_CCY_CODE=loan.v_ccy_code,
                    )

                    balance -= principal_payment
                    current_date += payment_interval
                    cashflow_bucket += 1
                    periods -= 1

    except Exception as e:
        save_log(
            'calculate_cash_flows_for_loan',
            'ERROR',
            f"Account {loan.v_account_number} skipped due to error: {str(e)}"
        )
        return


def project_cash_flows(fic_mis_date):
    try:
        FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date).delete()
        loans = Ldn_Financial_Instrument.objects.filter(fic_mis_date=fic_mis_date)
        if not loans.exists():
            save_log('project_cash_flows', 'ERROR', f"No loans found for the given fic_mis_date: {fic_mis_date}", status='FAILURE')
            return 0

        num_threads = min(10, len(loans))
        total_cash_flows = 0

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(calculate_cash_flows_for_loan, loan) for loan in loans]
            for future in futures:
                future.result()

        total_cash_flows = FSI_Expected_Cashflow.objects.filter(fic_mis_date=fic_mis_date).count()

        save_log(
            'project_cash_flows', 'INFO', 
            f"Total of {total_cash_flows} cash flows projected for {loans.count()} loans for MIS date {fic_mis_date}.", 
            status='SUCCESS'
        )
        return 1

    except Exception as e:
        save_log('project_cash_flows', 'ERROR', f"Error occurred: {str(e)}", status='FAILURE')
        return 0
