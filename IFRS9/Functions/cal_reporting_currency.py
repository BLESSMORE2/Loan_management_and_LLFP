import requests
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from django.db.models import Sum
from ..models import DimExchangeRateConf, Ldn_Exchange_Rate, FCT_Reporting_Lines, ReportingCurrency, Dim_Run
from django.utils import timezone
from .save_log import save_log

EXCHANGE_RATE_API_URL = 'https://v6.exchangerate-api.com/v6/'

def get_all_exchange_rates_from_api(base_currency):
    """Fetch all exchange rates for a base currency from ExchangeRate-API in one request."""
    try:
        # Fetch the API key from the config table where use_on_exchange_rates is True
        exchange_rate_conf = DimExchangeRateConf.objects.filter(use_on_exchange_rates=True).first()

        if not exchange_rate_conf:
            save_log('get_all_exchange_rates_from_api', 'ERROR', "API usage is disabled.")
            return None  # Stop execution if the API usage is disabled

        EXCHANGE_RATE_API_KEY = exchange_rate_conf.EXCHANGE_RATE_API_KEY

        # Construct the API URL to get all rates for the base currency
        url = f"{EXCHANGE_RATE_API_URL}{EXCHANGE_RATE_API_KEY}/latest/{base_currency}"
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200 and data['result'] == "success":
            save_log('get_all_exchange_rates_from_api', 'INFO', f"Successfully fetched exchange rates for {base_currency}")
            return data['conversion_rates']  # Return the full dictionary of rates
        else:
            raise ValueError(f"API request failed: {data.get('error-type', 'Unknown error')}")
    except Exception as e:
        save_log('get_all_exchange_rates_from_api', 'ERROR', f"Error fetching exchange rates from API: {e}")
        return None

def get_latest_run_skey():
    """Retrieve the latest_run_skey from Dim_Run table."""
    try:
        run_record = Dim_Run.objects.first()
        if not run_record:
            save_log('get_latest_run_skey', 'ERROR', "No run key available in Dim_Run table.")
            return None
        return run_record.latest_run_skey
    except Dim_Run.DoesNotExist:
        save_log('get_latest_run_skey', 'ERROR', "Dim_Run table is missing.")
        return None

def update_reporting_lines_with_exchange_rate(fic_mis_date):
    try:
        n_run_key = get_latest_run_skey()
        if not n_run_key:
            return "No run key found."

        # Step 1: Get the reporting currency code (target currency for all conversions)
        reporting_currency = ReportingCurrency.objects.first()  # Assuming there's only one reporting currency
        if not reporting_currency:
            save_log('update_reporting_lines_with_exchange_rate', 'ERROR', "No reporting currency defined.")
            return "Error: No reporting currency defined."
        
        target_currency_code = reporting_currency.currency_code.code

        # Step 2: Fetch exchange rates for the provided fic_mis_date from the database
        exchange_rates = Ldn_Exchange_Rate.objects.filter(fic_mis_date=fic_mis_date)
        
        # Check if we should use online API rates or local database rates
        use_online_api = DimExchangeRateConf.objects.filter(use_on_exchange_rates=True).exists()

        exchange_rate_dict = {}
        if exchange_rates.exists():
            # If exchange rates exist in the database, store them in a dictionary for quick access
            exchange_rate_dict = {(rate.v_from_ccy_code, rate.v_to_ccy_code): rate.n_exchange_rate for rate in exchange_rates}
        elif use_online_api:
            # Fetch all exchange rates once from the API if needed
            api_exchange_rates = get_all_exchange_rates_from_api(target_currency_code)
            if api_exchange_rates:
                exchange_rate_dict.update({(target_currency_code, currency): rate for currency, rate in api_exchange_rates.items()})

                # Save the fetched exchange rates to the database for future use
                for from_currency, exchange_rate in api_exchange_rates.items():
                    Ldn_Exchange_Rate.objects.create(
                        fic_mis_date=fic_mis_date,
                        v_from_ccy_code=target_currency_code,
                        v_to_ccy_code=from_currency,
                        n_exchange_rate=exchange_rate,
                        d_last_updated=timezone.now()
                    )
            else:
                save_log('update_reporting_lines_with_exchange_rate', 'ERROR', "Unable to fetch exchange rates from API.")
        
        # Step 3: Prepare the process function for multi-threading
        def process_entry(line):
            if line.v_ccy_code == target_currency_code:
                # No conversion is needed, so use NCY value as the RCY value (multiply by 1)
                line.n_exposure_at_default_rcy = line.n_exposure_at_default_ncy
                line.n_carrying_amount_rcy = line.n_carrying_amount_ncy
                line.n_lifetime_ecl_rcy = line.n_lifetime_ecl_ncy
                line.n_12m_ecl_rcy = line.n_12m_ecl_ncy
            else:
                # Step 5: Check if the exchange rate exists in the local dictionary
                exchange_rate_key = (target_currency_code, line.v_ccy_code)

                if exchange_rate_key not in exchange_rate_dict:
                    save_log('update_reporting_lines_with_exchange_rate', 'ERROR', f"Exchange rate not found for {line.v_ccy_code} to {target_currency_code}")
                    return line

                # Apply the exchange rate
                exchange_rate = exchange_rate_dict[exchange_rate_key]
                line.n_exposure_at_default_rcy = exchange_rate * line.n_exposure_at_default_ncy if line.n_exposure_at_default_ncy else None
                line.n_carrying_amount_rcy = exchange_rate * line.n_carrying_amount_ncy if line.n_carrying_amount_ncy else None
                line.n_lifetime_ecl_rcy = exchange_rate * line.n_lifetime_ecl_ncy if line.n_lifetime_ecl_ncy else None
                line.n_12m_ecl_rcy = exchange_rate * line.n_12m_ecl_ncy if line.n_12m_ecl_ncy else None

            return line

        # Step 4: Fetch the reporting lines based on n_run_key and fic_mis_date
        reporting_lines = FCT_Reporting_Lines.objects.filter(fic_mis_date=fic_mis_date, n_run_key=n_run_key)

        # Step 5: Use multi-threading to process the reporting lines
        with ThreadPoolExecutor(max_workers=20) as executor:
            updated_entries = list(executor.map(process_entry, reporting_lines))

        # Step 6: Bulk update the modified reporting lines
        with transaction.atomic():
            FCT_Reporting_Lines.objects.bulk_update(updated_entries, [
                'n_exposure_at_default_rcy', 'n_carrying_amount_rcy', 'n_lifetime_ecl_rcy', 'n_12m_ecl_rcy'
            ])

        save_log('update_reporting_lines_with_exchange_rate', 'INFO', f"Successfully updated reporting lines for run key {n_run_key} and MIS date {fic_mis_date}.")
        return "Update successful."

    except ValueError as ve:
        save_log('update_reporting_lines_with_exchange_rate', 'ERROR', f"Value Error: {str(ve)}")
        return f"Value Error: {str(ve)}"
    except Exception as e:
        save_log('update_reporting_lines_with_exchange_rate', 'ERROR', f"Error during update: {str(e)}")
        return f"Error during update: {str(e)}"
