from concurrent.futures import ThreadPoolExecutor
from django.db.models import Sum
from ..models import FCT_Reporting_Lines, fsi_Financial_Cash_Flow_Cal, ECLMethod, Dim_Run

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.first()
        if not run_record:
            raise ValueError("No run key is available in the Dim_Run table.")
        return run_record.latest_run_skey
    except Dim_Run.DoesNotExist:
        raise ValueError("Dim_Run table is missing.")


def calculate_ecl_based_on_method(fic_mis_date):
    """
    Determines the ECL calculation method from the ECLMethod table and applies it.
    Applies discounting if required by the method, using the latest run key.
    """
    try:
        # Get the latest run key from Dim_Run table
        n_run_key = get_latest_run_skey()

        ecl_method_record = ECLMethod.objects.first()
        if not ecl_method_record:
            raise ValueError("No ECL method is defined in the ECLMethod table.")

        method_name = ecl_method_record.method_name
        uses_discounting = ecl_method_record.uses_discounting

        print(f"Using ECL Method: {method_name}, Discounting: {uses_discounting}, Run Key: {n_run_key}")

        if method_name == 'forward_exposure':
            update_ecl_based_on_forward_loss(n_run_key, fic_mis_date, uses_discounting)
        elif method_name == 'cash_flow':
            update_ecl_based_on_cash_shortfall(n_run_key, fic_mis_date, uses_discounting)
        elif method_name == 'simple_ead':
            update_ecl_based_on_internal_calculations(n_run_key, fic_mis_date)
        else:
            raise ValueError(f"Unknown ECL method: {method_name}")

        print("ECL calculation completed successfully.")
    except Exception as e:
        print(f"Error calculating ECL: {e}")


def update_ecl_based_on_cash_shortfall(n_run_key, fic_mis_date, uses_discounting):
    """
    Updates ECL based on cash shortfall or cash shortfall present value using multi-threading and bulk update.
    If uses_discounting is True, it uses present value fields.
    """
    try:
        reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)
        updated_count = 0  # Track the number of records updated

        def process_entry(entry):
            nonlocal updated_count  # Allow modification of the outer variable
            cash_flow_records = fsi_Financial_Cash_Flow_Cal.objects.filter(
                n_run_skey=n_run_key,
                fic_mis_date=fic_mis_date,
                v_account_number=entry.n_account_number
            )

            # Apply discounting or not based on the ECL method
            if uses_discounting:
                summed_cash_shortfall = cash_flow_records.aggregate(total_cash_shortfall_pv=Sum('n_cash_shortfall_pv'))
                summed_12m_cash_shortfall = cash_flow_records.aggregate(total_12m_cash_shortfall_pv=Sum('n_12m_cash_shortfall_pv'))

                # Use default value if None
                total_cash_shortfall_pv = summed_cash_shortfall['total_cash_shortfall_pv'] or 0
                total_12m_cash_shortfall_pv = summed_12m_cash_shortfall['total_12m_cash_shortfall_pv'] or 0

                if total_cash_shortfall_pv == 0:
                    raise ValueError(f"No cash shortfall PV found for account {entry.n_account_number}")

                if total_12m_cash_shortfall_pv == 0:
                    raise ValueError(f"No 12M cash shortfall PV found for account {entry.n_account_number}")
            else:
                summed_cash_shortfall = cash_flow_records.aggregate(total_cash_shortfall=Sum('n_cash_shortfall'))
                summed_12m_cash_shortfall = cash_flow_records.aggregate(total_12m_cash_shortfall=Sum('n_12m_cash_shortfall'))

                # Use default value if None
                total_cash_shortfall = summed_cash_shortfall['total_cash_shortfall'] or 0
                total_12m_cash_shortfall = summed_12m_cash_shortfall['total_12m_cash_shortfall'] or 0

                if total_cash_shortfall == 0:
                    raise ValueError(f"No cash shortfall found for account {entry.n_account_number}")

                if total_12m_cash_shortfall == 0:
                    raise ValueError(f"No 12M cash shortfall found for account {entry.n_account_number}")

            # Update lifetime ECL based on cash shortfall
            entry.n_lifetime_ecl_ncy = total_cash_shortfall if not uses_discounting else total_cash_shortfall_pv
            # Update 12-month ECL based on cash shortfall
            entry.n_12m_ecl_ncy = total_12m_cash_shortfall if not uses_discounting else total_12m_cash_shortfall_pv

            updated_count += 1  # Increment the updated count

            return entry

        # Multi-threading for processing entries
        with ThreadPoolExecutor(max_workers=8) as executor:
            updated_entries = list(executor.map(process_entry, reporting_lines))

        # Bulk update the entries in the database
        FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

        print(f"Successfully updated {updated_count} records for ECL based on cash shortfall for run key {n_run_key} and MIS date {fic_mis_date}.")
    except Exception as e:
        print(f"Error updating ECL based on cash shortfall: {e}")


def update_ecl_based_on_forward_loss(n_run_key, fic_mis_date, uses_discounting):
    """
    Updates ECL based on forward expected loss or forward expected loss present value using multi-threading and bulk update.
    If uses_discounting is True, it uses present value fields.
    """
    try:
        reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)
        updated_count = 0  # Track the number of records updated

        def process_entry(entry):
            nonlocal updated_count  # Allow modification of the outer variable
            cash_flow_records = fsi_Financial_Cash_Flow_Cal.objects.filter(
                n_run_skey=n_run_key,
                fic_mis_date=fic_mis_date,
                v_account_number=entry.n_account_number
            )

            if uses_discounting:
                summed_forward_loss = cash_flow_records.aggregate(total_forward_expected_loss_pv=Sum('n_forward_expected_loss_pv'))
                summed_12m_forward_loss = cash_flow_records.aggregate(total_12m_fwd_expected_loss_pv=Sum('n_12m_fwd_expected_loss_pv'))

                total_forward_expected_loss_pv = summed_forward_loss['total_forward_expected_loss_pv'] or 0
                total_12m_fwd_expected_loss_pv = summed_12m_forward_loss['total_12m_fwd_expected_loss_pv'] or 0

                if total_forward_expected_loss_pv == 0:
                    raise ValueError(f"No forward expected loss PV found for account {entry.n_account_number}")

                if total_12m_fwd_expected_loss_pv == 0:
                    raise ValueError(f"No 12M forward expected loss PV found for account {entry.n_account_number}")
            else:
                summed_forward_loss = cash_flow_records.aggregate(total_forward_expected_loss=Sum('n_forward_expected_loss'))
                summed_12m_forward_loss = cash_flow_records.aggregate(total_12m_fwd_expected_loss=Sum('n_12m_fwd_expected_loss'))

                total_forward_expected_loss = summed_forward_loss['total_forward_expected_loss'] or 0
                total_12m_fwd_expected_loss = summed_12m_forward_loss['total_12m_fwd_expected_loss'] or 0

                if total_forward_expected_loss == 0:
                    raise ValueError(f"No forward expected loss found for account {entry.n_account_number}")

                if total_12m_fwd_expected_loss == 0:
                    raise ValueError(f"No 12M forward expected loss found for account {entry.n_account_number}")

            # Update lifetime ECL based on forward expected loss
            entry.n_lifetime_ecl_ncy = total_forward_expected_loss if not uses_discounting else total_forward_expected_loss_pv
            # Update 12-month ECL based on forward expected loss
            entry.n_12m_ecl_ncy = total_12m_fwd_expected_loss if not uses_discounting else total_12m_fwd_expected_loss_pv

            updated_count += 1  # Increment the updated count

            return entry

        # Multi-threading
        with ThreadPoolExecutor(max_workers=8) as executor:
            updated_entries = list(executor.map(process_entry, reporting_lines))

        # Bulk update the entries in the database
        FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

        print(f"Successfully updated {updated_count} records for ECL based on forward expected loss for run key {n_run_key} and MIS date {fic_mis_date}.")
    except Exception as e:
        print(f"Error updating ECL based on forward expected loss: {e}")


def update_ecl_based_on_internal_calculations(n_run_key, fic_mis_date):
    """
    Updates ECL based on simple internal calculations: EAD * PD * LGD using multi-threading and bulk update.
    This method does not use discounting.
    """
    try:
        reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)
        updated_count = 0  # Track the number of records updated

        def process_entry(entry):
            nonlocal updated_count  # Allow modification of the outer variable
            if entry.n_exposure_at_default_ncy and entry.n_lifetime_pd and entry.n_lgd_percent:
                entry.n_lifetime_ecl_ncy = (
                    entry.n_exposure_at_default_ncy *
                    entry.n_lifetime_pd *
                    entry.n_lgd_percent
                )

            if entry.n_exposure_at_default_ncy and entry.n_twelve_months_pd and entry.n_lgd_percent:
                entry.n_12m_ecl_ncy = (
                    entry.n_exposure_at_default_ncy *
                    entry.n_twelve_months_pd *
                    entry.n_lgd_percent
                )

            updated_count += 1  # Increment the updated count

            return entry

        # Multi-threading
        with ThreadPoolExecutor(max_workers=8) as executor:
            updated_entries = list(executor.map(process_entry, reporting_lines))

        # Bulk update the entries in the database
        FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

        print(f"Successfully updated {updated_count} records for ECL based on internal calculations for run key {n_run_key} and MIS date {fic_mis_date}.")
    except Exception as e:
        print(f"Error updating ECL based on internal calculations: {e}")
