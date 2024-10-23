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


def fetch_and_save_exchange_rates_from_api(target_currency_code, fic_mis_date, use_latest):
    """Fetch exchange rates from the API and save them to the database."""
    # Fetch exchange rates from the API
    exchange_rates = get_exchange_rates_from_api(target_currency_code, fic_mis_date, use_latest)

    if not exchange_rates:
        save_log('fetch_and_save_exchange_rates_from_api', 'ERROR', "Unable to fetch exchange rates from API.")
        return "Error: Unable to fetch exchange rates."

    # Delete existing exchange rates for the provided fic_mis_date
    Ldn_Exchange_Rate.objects.filter(fic_mis_date=fic_mis_date).delete()
    save_log('fetch_and_save_exchange_rates_from_api', 'INFO', f"Deleted old exchange rates for date {fic_mis_date}.")

    # Save the fetched exchange rates to the database
    exchange_rate_dict = {}
    for from_currency, exchange_rate in exchange_rates.items():
        if from_currency != target_currency_code:
            inverted_exchange_rate = 1 / Decimal(str(exchange_rate))
        else:
            inverted_exchange_rate = Decimal(str(exchange_rate))  # For the base currency itself

        # Insert new exchange rate records after deletion
        Ldn_Exchange_Rate.objects.create(
            fic_mis_date=fic_mis_date,
            v_from_ccy_code=from_currency,   # The foreign currency
            v_to_ccy_code=target_currency_code,  # Always report to the reporting currency
            n_exchange_rate=inverted_exchange_rate,  # Store the inverted exchange rate
            d_last_updated=timezone.now()
        )
        exchange_rate_dict[(from_currency, target_currency_code)] = inverted_exchange_rate

    return exchange_rate_dict

def fetch_manual_exchange_rates(target_currency_code, fic_mis_date):
    """Fetch manually loaded exchange rates from the database."""
    exchange_rates = Ldn_Exchange_Rate.objects.filter(fic_mis_date=fic_mis_date)
    if not exchange_rates.exists():
        save_log('fetch_manual_exchange_rates', 'ERROR', f"No manually loaded exchange rates found for date {fic_mis_date}.")
        return None

    # Prepare the exchange rate dictionary from the database records
    exchange_rate_dict = {(rate.v_from_ccy_code, rate.v_to_ccy_code): rate.n_exchange_rate for rate in exchange_rates}
    return exchange_rate_dict

def update_reporting_lines(fic_mis_date, exchange_rate_dict, target_currency_code):
    """Update the FCT_Reporting_Lines with the provided exchange rates."""
    n_run_key = get_latest_run_skey()

    if not n_run_key:
        return "No run key available."

    # Update the reporting lines with the fetched exchange rates
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
                save_log('update_reporting_lines', 'ERROR', f"Exchange rate not found for {line.v_ccy_code} to {target_currency_code}")
                return line

            # Apply the exchange rate, converting it to Decimal before multiplication
            exchange_rate = exchange_rate_dict[exchange_rate_key]
            line.n_exposure_at_default_rcy = exchange_rate * Decimal(line.n_exposure_at_default_ncy) if line.n_exposure_at_default_ncy else None
            line.n_carrying_amount_rcy = exchange_rate * Decimal(line.n_carrying_amount_ncy) if line.n_carrying_amount_ncy else None
            line.n_lifetime_ecl_rcy = exchange_rate * Decimal(line.n_lifetime_ecl_ncy) if line.n_lifetime_ecl_ncy else None
            line.n_12m_ecl_rcy = exchange_rate * Decimal(line.n_12m_ecl_ncy) if line.n_12m_ecl_ncy else None

        return line

    # Fetch the reporting lines and process them with multi-threading
    reporting_lines = FCT_Reporting_Lines.objects.filter(n_run_key=n_run_key, fic_mis_date=fic_mis_date)
    with ThreadPoolExecutor(max_workers=20) as executor:
        updated_entries = list(executor.map(process_entry, reporting_lines))

    # Bulk update the reporting lines and log the number of rows updated
    with transaction.atomic():
        FCT_Reporting_Lines.objects.bulk_update(updated_entries, [
            'n_exposure_at_default_rcy', 'n_carrying_amount_rcy', 'n_lifetime_ecl_rcy', 'n_12m_ecl_rcy'
        ])

    save_log('update_reporting_lines', 'INFO', f"Successfully updated {len(updated_entries)} reporting lines for MIS date {fic_mis_date}.")
    return f"Update successful. {len(updated_entries)} rows updated."

def update_reporting_lines_with_exchange_rate(fic_mis_date):
    try:
        # Step 1: Get exchange rate configuration
        exchange_rate_conf = DimExchangeRateConf.objects.first()
        if not exchange_rate_conf:
            save_log('update_reporting_lines_with_exchange_rate', 'ERROR', "No valid exchange rate configuration found.")
            return "No valid exchange rate configuration found."

        use_online = exchange_rate_conf.use_on_exchange_rates
        use_latest = exchange_rate_conf.use_latest_exchange_rates

        # Step 2: Get the reporting currency code (target currency for all conversions)
        reporting_currency = ReportingCurrency.objects.first()
        if not reporting_currency:
            save_log('update_reporting_lines_with_exchange_rate', 'ERROR', "No reporting currency defined.")
            return "Error: No reporting currency defined."
        
        target_currency_code = reporting_currency.currency_code.code  # This is the base currency

        # Step 3: Based on the configuration, call the appropriate function
        if use_online:
            exchange_rate_dict = fetch_and_save_exchange_rates_from_api(target_currency_code, fic_mis_date, use_latest)
        else:
            exchange_rate_dict = fetch_manual_exchange_rates(target_currency_code, fic_mis_date)

        if not exchange_rate_dict:
            return "Error: Unable to retrieve exchange rates."

        # Step 4: Update reporting lines using the fetched exchange rates
        return update_reporting_lines(fic_mis_date, exchange_rate_dict, target_currency_code)

    except ValueError as ve:
        save_log('update_reporting_lines_with_exchange_rate', 'ERROR', f"Value Error: {str(ve)}")
        return f"Value Error: {str(ve)}"
    except Exception as e:
        save_log('update_reporting_lines_with_exchange_rate', 'ERROR', f"Error during update: {str(e)}")
        return f"Error during update: {str(e)}"
