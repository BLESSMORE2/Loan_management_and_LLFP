import requests
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from django.db.models import Sum
from ..models import DimExchangeRateConf, Ldn_Exchange_Rate, FCT_Reporting_Lines, ReportingCurrency, Dim_Run
from django.utils import timezone
from .save_log import save_log
from decimal import Decimal


EXCHANGE_RATE_API_URL = 'https://v6.exchangerate-api.com/v6/'
      

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

def get_exchange_rates_from_api(base_currency, date=None, use_latest=False):
    """Fetch exchange rates for a base currency either for the latest or for a specific date (historical)."""
    try:
        # Fetch the API key from the config table where use_on_exchange_rates is True
        exchange_rate_conf = DimExchangeRateConf.objects.filter(use_on_exchange_rates=True).first()

        if not exchange_rate_conf:
            save_log('get_exchange_rates_from_api', 'ERROR', "API usage is disabled.")
            return None  # Stop execution if the API usage is disabled

        EXCHANGE_RATE_API_KEY = exchange_rate_conf.EXCHANGE_RATE_API_KEY

        # Determine if we are using latest or historical rates
        if use_latest:
            # Use the latest exchange rate
            url = f"{EXCHANGE_RATE_API_URL}{EXCHANGE_RATE_API_KEY}/latest/{base_currency}"
        else:
            # Use historical exchange rate based on the date provided
            if not date:
                save_log('get_exchange_rates_from_api', 'ERROR', "Historical rates require a date to be supplied.")
                return None
            # Split the date string 'YYYY-MM-DD' to extract year, month, and day
            year, month, day = date.split('-')

            # Construct the historical API URL (no leading zeros for month and day)
            url = f"{EXCHANGE_RATE_API_URL}{EXCHANGE_RATE_API_KEY}/history/{base_currency}/{int(year)}/{int(month)}/{int(day)}"

        response = requests.get(url)
        data = response.json()

        # Log response details for debugging
        save_log('get_exchange_rates_from_api', 'INFO', f"Response Status: {response.status_code}, Text: {response.text}")

        # Check if the response is valid
        if response.status_code == 200:
            if data.get('result') == "success":
                save_log('get_exchange_rates_from_api', 'INFO', f"Successfully fetched exchange rates for {base_currency} on {date if not use_latest else 'latest'}")
                return data['conversion_rates']  # Return the full dictionary of rates
            else:
                # Handle specific error types from the API
                error_type = data.get('error-type', 'Unknown error')
                save_log('get_exchange_rates_from_api', 'ERROR', f"Exchange rate API error: {error_type}")
                return None
        else:
            save_log('get_exchange_rates_from_api', 'ERROR', f"API request failed with status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        save_log('get_exchange_rates_from_api', 'ERROR', f"Error fetching exchange rates from API: {e}")
        return None

def update_reporting_lines_with_exchange_rate(fic_mis_date):
    try:
        # Step 1: Determine if we should use the latest exchange rates or historical
        exchange_rate_conf = DimExchangeRateConf.objects.filter(use_on_exchange_rates=True).first()
        if not exchange_rate_conf:
            save_log('update_reporting_lines_with_exchange_rate', 'ERROR', "No valid exchange rate configuration found.")
            return "No valid exchange rate configuration found."

        use_latest = exchange_rate_conf.use_latest_exchange_rates

        # Step 2: Get the reporting currency code (target currency for all conversions)
        reporting_currency = ReportingCurrency.objects.first()  # Assuming there's only one reporting currency
        if not reporting_currency:
            save_log('update_reporting_lines_with_exchange_rate', 'ERROR', "No reporting currency defined.")
            return "Error: No reporting currency defined."
        
        target_currency_code = reporting_currency.currency_code.code  # This is the base currency

        # Step 3: Fetch exchange rates (latest or historical based on the config)
        exchange_rates = get_exchange_rates_from_api(target_currency_code, fic_mis_date, use_latest)

        if not exchange_rates:
            save_log('update_reporting_lines_with_exchange_rate', 'ERROR', "Unable to fetch exchange rates.")
            return "Error: Unable to fetch exchange rates."
        
        #  Delete existing exchange rates for the provided fic_mis_date before inserting new ones
        Ldn_Exchange_Rate.objects.filter(fic_mis_date=fic_mis_date).delete()

        # Step 4: Save the fetched exchange rates to the database for future use (if historical, use fic_mis_date)
        exchange_rate_dict = {}
        for from_currency, exchange_rate in exchange_rates.items():
            if from_currency != target_currency_code:  # Ensure we are not inverting the base currency
                inverted_exchange_rate = 1 / Decimal(str(exchange_rate))
            else:
                inverted_exchange_rate = Decimal(str(exchange_rate))  # For the base currency itself, keep it as is

            Ldn_Exchange_Rate.objects.create(
                fic_mis_date=fic_mis_date,
                v_from_ccy_code=from_currency,   # The foreign currency
                v_to_ccy_code=target_currency_code,  # Always report to the reporting currency
                n_exchange_rate=inverted_exchange_rate,  # Store the inverted exchange rate
                d_last_updated=timezone.now()
            )
            exchange_rate_dict[(from_currency, target_currency_code)] = inverted_exchange_rate
        
        # Step 5: Update the reporting lines with the fetched exchange rates
        def process_entry(line):
            if line.v_ccy_code == target_currency_code:
                # No conversion is needed, so use NCY value as the RCY value (multiply by 1)
                line.n_exposure_at_default_rcy = line.n_exposure_at_default_ncy
                line.n_carrying_amount_rcy = line.n_carrying_amount_ncy
                line.n_lifetime_ecl_rcy = line.n_lifetime_ecl_ncy
                line.n_12m_ecl_rcy = line.n_12m_ecl_ncy
            else:
                # Fetch the exchange rate for the line's currency
                exchange_rate_key = (line.v_ccy_code, target_currency_code)

                if exchange_rate_key not in exchange_rate_dict:
                    save_log('update_reporting_lines_with_exchange_rate', 'ERROR', f"Exchange rate not found for {line.v_ccy_code} to {target_currency_code}")
                    return line

                # Apply the exchange rate, converting it to Decimal before multiplication
                exchange_rate = exchange_rate_dict[exchange_rate_key]
                line.n_exposure_at_default_rcy = exchange_rate * Decimal(line.n_exposure_at_default_ncy) if line.n_exposure_at_default_ncy else None
                line.n_carrying_amount_rcy = exchange_rate * Decimal(line.n_carrying_amount_ncy) if line.n_carrying_amount_ncy else None
                line.n_lifetime_ecl_rcy = exchange_rate * Decimal(line.n_lifetime_ecl_ncy) if line.n_lifetime_ecl_ncy else None
                line.n_12m_ecl_rcy = exchange_rate * Decimal(line.n_12m_ecl_ncy) if line.n_12m_ecl_ncy else None

            return line

        # Step 6: Fetch the reporting lines and process them with multi-threading
        reporting_lines = FCT_Reporting_Lines.objects.filter(fic_mis_date=fic_mis_date)
        with ThreadPoolExecutor(max_workers=20) as executor:
            updated_entries = list(executor.map(process_entry, reporting_lines))

        # Step 7: Bulk update the reporting lines
        with transaction.atomic():
            FCT_Reporting_Lines.objects.bulk_update(updated_entries, [
                'n_exposure_at_default_rcy', 'n_carrying_amount_rcy', 'n_lifetime_ecl_rcy', 'n_12m_ecl_rcy'
            ])

        save_log('update_reporting_lines_with_exchange_rate', 'INFO', f"Successfully updated reporting lines for MIS date {fic_mis_date}.")
        return "Update successful."

    except ValueError as ve:
        save_log('update_reporting_lines_with_exchange_rate', 'ERROR', f"Value Error: {str(ve)}")
        return f"Value Error: {str(ve)}"
    except Exception as e:
        save_log('update_reporting_lines_with_exchange_rate', 'ERROR', f"Error during update: {str(e)}")
        return f"Error during update: {str(e)}"