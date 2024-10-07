from concurrent.futures import ThreadPoolExecutor
from django.db.models import Sum
from django.db import transaction
from ..models import FCT_Reporting_Lines, fsi_Financial_Cash_Flow_Cal, ECLMethod, Dim_Run
from .save_log import save_log

def get_latest_run_skey():
    """
    Retrieve the latest_run_skey from Dim_Run table.
    """
    try:
        run_record = Dim_Run.objects.first()
        if not run_record:
            save_log('get_latest_run_skey', 'ERROR', "No run key is available in the Dim_Run table.")
            return None
        return run_record.latest_run_skey
    except Dim_Run.DoesNotExist:
        save_log('get_latest_run_skey', 'ERROR', "Dim_Run table is missing.")
        return None

def calculate_ecl_based_on_method(fic_mis_date):
    """
    Determines the ECL calculation method from the ECLMethod table and applies it.
    Applies discounting if required by the method, using the latest run key.
    """
    try:
        n_run_key = get_latest_run_skey()
        if not n_run_key:
            return '0'

        ecl_method_record = ECLMethod.objects.first()
        if not ecl_method_record:
            save_log('calculate_ecl_based_on_method', 'ERROR', "No ECL method is defined in the ECLMethod table.")
            return '0'

        method_name = ecl_method_record.method_name
        uses_discounting = ecl_method_record.uses_discounting

        save_log('calculate_ecl_based_on_method', 'INFO', f"Using ECL Method: {method_name}, Discounting: {uses_discounting}, Run Key: {n_run_key}")

        if method_name == 'forward_exposure':
            update_ecl_based_on_forward_loss(n_run_key, fic_mis_date, uses_discounting)
        elif method_name == 'cash_flow':
            update_ecl_based_on_cash_shortfall(n_run_key, fic_mis_date, uses_discounting)
        elif method_name == 'simple_ead':
            update_ecl_based_on_internal_calculations(n_run_key, fic_mis_date)
        else:
            save_log('calculate_ecl_based_on_method', 'ERROR', f"Unknown ECL method: {method_name}")
            return '0'

        save_log('calculate_ecl_based_on_method', 'INFO', "ECL calculation completed successfully.")
        return '1'

    except Exception as e:
        save_log('calculate_ecl_based_on_method', 'ERROR', f"Error calculating ECL: {e}")
        return '0'

def update_ecl_based_on_cash_shortfall(n_run_key, fic_mis_date, uses_discounting):
    """
    Updates ECL based on cash shortfall or cash shortfall present value using multi-threading and bulk update.
    If uses_discounting is True, it uses present value fields.
    """
    try:
        reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)

        def process_entry(entry):
            cash_flow_records = fsi_Financial_Cash_Flow_Cal.objects.filter(
                n_run_skey=n_run_key,
                fic_mis_date=fic_mis_date,
                v_account_number=entry.n_account_number
            )

            if uses_discounting:
                total_cash_shortfall_pv = cash_flow_records.aggregate(Sum('n_cash_shortfall_pv'))['n_cash_shortfall_pv__sum'] or 0
                total_12m_cash_shortfall_pv = cash_flow_records.aggregate(Sum('n_12m_cash_shortfall_pv'))['n_12m_cash_shortfall_pv__sum'] or 0
                entry.n_lifetime_ecl_ncy = total_cash_shortfall_pv
                entry.n_12m_ecl_ncy = total_12m_cash_shortfall_pv
            else:
                total_cash_shortfall = cash_flow_records.aggregate(Sum('n_cash_shortfall'))['n_cash_shortfall__sum'] or 0
                total_12m_cash_shortfall = cash_flow_records.aggregate(Sum('n_12m_cash_shortfall'))['n_12m_cash_shortfall__sum'] or 0
                entry.n_lifetime_ecl_ncy = total_cash_shortfall
                entry.n_12m_ecl_ncy = total_12m_cash_shortfall

            return entry

        with ThreadPoolExecutor(max_workers=20) as executor:
            updated_entries = list(executor.map(process_entry, reporting_lines))

        with transaction.atomic():
            updated_count = FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

        save_log('update_ecl_based_on_cash_shortfall', 'INFO', f"Successfully updated {updated_count} records for ECL based on cash shortfall for run key {n_run_key} and MIS date {fic_mis_date}.")
    except Exception as e:
        save_log('update_ecl_based_on_cash_shortfall', 'ERROR', f"Error updating ECL based on cash shortfall: {e}")

def update_ecl_based_on_forward_loss(n_run_key, fic_mis_date, uses_discounting):
    """
    Updates ECL based on forward expected loss or forward expected loss present value using multi-threading and bulk update.
    If uses_discounting is True, it uses present value fields.
    """
    try:
        reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)

        def process_entry(entry):
            cash_flow_records = fsi_Financial_Cash_Flow_Cal.objects.filter(
                n_run_skey=n_run_key,
                fic_mis_date=fic_mis_date,
                v_account_number=entry.n_account_number
            )

            if uses_discounting:
                total_forward_expected_loss_pv = cash_flow_records.aggregate(Sum('n_forward_expected_loss_pv'))['n_forward_expected_loss_pv__sum'] or 0
                total_12m_fwd_expected_loss_pv = cash_flow_records.aggregate(Sum('n_12m_fwd_expected_loss_pv'))['n_12m_fwd_expected_loss_pv__sum'] or 0
                entry.n_lifetime_ecl_ncy = total_forward_expected_loss_pv
                entry.n_12m_ecl_ncy = total_12m_fwd_expected_loss_pv
            else:
                total_forward_expected_loss = cash_flow_records.aggregate(Sum('n_forward_expected_loss'))['n_forward_expected_loss__sum'] or 0
                total_12m_fwd_expected_loss = cash_flow_records.aggregate(Sum('n_12m_fwd_expected_loss'))['n_12m_fwd_expected_loss__sum'] or 0
                entry.n_lifetime_ecl_ncy = total_forward_expected_loss
                entry.n_12m_ecl_ncy = total_12m_fwd_expected_loss

            return entry

        with ThreadPoolExecutor(max_workers=20) as executor:
            updated_entries = list(executor.map(process_entry, reporting_lines))

        with transaction.atomic():
            updated_count = FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

        save_log('update_ecl_based_on_forward_loss', 'INFO', f"Successfully updated {updated_count} records for ECL based on forward expected loss for run key {n_run_key} and MIS date {fic_mis_date}.")
    except Exception as e:
        save_log('update_ecl_based_on_forward_loss', 'ERROR', f"Error updating ECL based on forward expected loss: {e}")

def update_ecl_based_on_internal_calculations(n_run_key, fic_mis_date):
    """
    Updates ECL based on simple internal calculations: EAD * PD * LGD using multi-threading and bulk update.
    This method does not use discounting.
    """
    try:
        reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)

        def process_entry(entry):
            if entry.n_exposure_at_default_ncy and entry.n_lifetime_pd and entry.n_lgd_percent:
                entry.n_lifetime_ecl_ncy = entry.n_exposure_at_default_ncy * entry.n_lifetime_pd * entry.n_lgd_percent

            if entry.n_exposure_at_default_ncy and entry.n_twelve_months_pd and entry.n_lgd_percent:
                entry.n_12m_ecl_ncy = entry.n_exposure_at_default_ncy * entry.n_twelve_months_pd * entry.n_lgd_percent

            return entry

        with ThreadPoolExecutor(max_workers=20) as executor:
            updated_entries = list(executor.map(process_entry, reporting_lines))

        with transaction.atomic():
            updated_count = FCT_Reporting_Lines.objects.bulk_update(updated_entries, ['n_lifetime_ecl_ncy', 'n_12m_ecl_ncy'])

        save_log('update_ecl_based_on_internal_calculations', 'INFO', f"Successfully updated {updated_count} records for ECL based on internal calculations for run key {n_run_key} and MIS date {fic_mis_date}.")
    except Exception as e:
        save_log('update_ecl_based_on_internal_calculations', 'ERROR', f"Error updating ECL based on internal calculations: {e}")
