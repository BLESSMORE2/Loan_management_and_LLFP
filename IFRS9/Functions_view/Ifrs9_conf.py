from django.shortcuts import render, get_object_or_404, redirect
from ..models import ECLMethod,FCT_Reporting_Lines,ReportColumnConfig,ReportingCurrency,CurrencyCode,DimExchangeRateConf
from ..forms import ECLMethodForm, ColumnMappingForm,ReportingCurrencyForm,CurrencyCodeForm,ExchangeRateConfForm
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.http import JsonResponse
import requests
from django.contrib.auth.decorators import login_required
from Users.models import AuditTrail  # Import AuditTrail model
from django.utils.timezone import now  # For timestamping




@login_required
def ifrs9_configuration(request):
    # Render the IFRS9 Configuration template
    return render(request, 'ifrs9_conf/ifrs9_configuration.html')

@login_required
def ecl_methodology_options(request):
    # This view shows the two options: Documentation and Choose Methodology
    return render(request, 'ifrs9_conf/ecl_methodology_options.html')

@login_required
def ecl_methodology_documentation(request):
    # View to show the ECL methodology documentation
    return render(request, 'ifrs9_conf/ecl_methodology_documentation.html') 

 # You would create a separate documentation page
@login_required
def ecl_methodology_list(request):
    methods = ECLMethod.objects.all()
    return render(request, 'ifrs9_conf/ecl_methodology_list.html', {'methods': methods})

@login_required
def add_ecl_method(request):
    if request.method == 'POST':
        form = ECLMethodForm(request.POST)
        if form.is_valid():
            try:
                # Save the form without committing to the database yet
                ecl_method = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
                ecl_method.created_by = request.user
                # Save the object to the database
                ecl_method.save()
                # Log the creation in the AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    model_name='ECLMethod',
                    action='create',
                    object_id=ecl_method.pk,
                    change_description=f"Created ECL Methodology: {ecl_method.method_name}",
                    timestamp=now(),
                )
                messages.success(request, "New ECL Methodology added successfully!")
                return redirect('ecl_methodology_list')
            except ValidationError as e:
                form.add_error(None, e.message)  # This adds the validation error to the form's non-field errors
        else:
            messages.error(request, "There was an error adding the ECL Methodology.")
    else:
        form = ECLMethodForm()

    return render(request, 'ifrs9_conf/add_ecl_method.html', {'form': form})


@login_required
def edit_ecl_method(request, method_id):
    method = get_object_or_404(ECLMethod, pk=method_id)
    if request.method == 'POST':
        form = ECLMethodForm(request.POST, instance=method)
        if form.is_valid():
            try:
                # Save the form without committing to the database yet
                previous_values = {
                    "method_name": method.method_name,
                    "uses_discounting": method.uses_discounting,
                }
                ecl_method = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
                ecl_method.created_by = request.user
                # Save the object to the database
                ecl_method.save()

                # Log the update in the AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    model_name='ECLMethod',
                    action='update',
                    object_id=ecl_method.pk,
                    change_description=(
                        f"Updated ECL Methodology: From {previous_values} to "
                        f"{form.cleaned_data}"
                    ),
                    timestamp=now(),
                )

                messages.success(request, "ECL methodology updated successfully!")
                return redirect('ecl_methodology_list')
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
        else:
            messages.error(request, "There was an error updating the ECL methodology.")
    else:
        form = ECLMethodForm(instance=method)
    
    return render(request, 'ifrs9_conf/edit_ecl_method.html', {'form': form})


@login_required
def delete_ecl_method(request, method_id):
    method = get_object_or_404(ECLMethod, pk=method_id)
    
    if request.method == 'POST':
        try:
            # Log the deletion in the AuditTrail
            AuditTrail.objects.create(
                user=request.user,
                model_name='ECLMethod',
                action='delete',
                object_id=method.pk,
                change_description=f"Deleted ECL Methodology: {method.method_name}",
                timestamp=now(),
            )

            method.delete()
            messages.success(request, "ECL Methodology deleted successfully!")
            return redirect('ecl_methodology_list')
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}")

    return render(request, 'ifrs9_conf/delete_ecl_method.html', {'method': method})

@login_required
def choose_ecl_methodology(request):
    # View to configure the ECL methodology
    return render(request, 'ifrs9_conf/choose_ecl_methodology.html')  


@login_required
def column_mapping_view(request):
    # Dynamically retrieve all field names from the model
    model_fields = [field.name for field in FCT_Reporting_Lines._meta.get_fields()]

    selected_columns = request.POST.getlist('selected_columns_hidden', [])

    if request.method == 'POST':
        form = ColumnMappingForm(request.POST, selected_columns=selected_columns, model_fields=model_fields)
        if form.is_valid():
            report_name = form.cleaned_data.get('report_name', 'default_report')
            
            # Delete old mappings for the same report name before saving new ones
            ReportColumnConfig.objects.filter(report_name=report_name).delete()

            # Save the new mappings
            column_mappings = form.cleaned_data['column_mappings']
            ReportColumnConfig.objects.create(
                report_name=report_name,
                selected_columns=column_mappings,
            )

            # Add a success message
            messages.success(request, f"Column mappings for {report_name} have been saved successfully.")

            return redirect('ifrs9_configuration')  # Redirect to the configuration page
    else:
        form = ColumnMappingForm(selected_columns=selected_columns, model_fields=model_fields)

    return render(request, 'ifrs9_conf/column_mapping.html', {
        'form': form,
        'available_columns': model_fields,
        'selected_columns': selected_columns
    })

@login_required
def configure_reporting_currency(request):
    """
    View for configuring the reporting currency.
    This page provides options for defining currency codes and selecting a reporting currency.
    """
    return render(request, 'ifrs9_conf/configure_reporting_currency.html')

# List all Reporting Currencies
@login_required
def reporting_currency_list(request):
    reporting_currencies = ReportingCurrency.objects.select_related('currency_code').all()
    return render(request, 'ifrs9_conf/reporting_currency_list.html', {'reporting_currencies': reporting_currencies})

# Create a new Reporting Currency
# Create a new Reporting Currency (only if there isn't one already)
@login_required
def reporting_currency_create(request):
    # Check if a reporting currency already exists
    if ReportingCurrency.objects.exists():
        messages.error(request, "There is already a reporting currency defined. You cannot add another.")
        return redirect('reporting_currency_list')
    
    if request.method == 'POST':
        form = ReportingCurrencyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Reporting currency added successfully!")
            return redirect('reporting_currency_list')
        else:
            messages.error(request, f"Error adding reporting currency: {form.errors}")
    else:
        form = ReportingCurrencyForm()
    
    return render(request, 'ifrs9_conf/reporting_currency_form.html', {'form': form})

# Edit an existing Reporting Currency
@login_required
def reporting_currency_edit(request, currency_id):
    reporting_currency = get_object_or_404(ReportingCurrency, pk=currency_id)
    if request.method == 'POST':
        form = ReportingCurrencyForm(request.POST, instance=reporting_currency)
        if form.is_valid():
            form.save()
            messages.success(request, "Reporting currency updated successfully!")
            return redirect('reporting_currency_list')
        else:
            messages.error(request, f"Error updating reporting currency: {form.errors}")
    else:
        form = ReportingCurrencyForm(instance=reporting_currency)
    
    return render(request, 'ifrs9_conf/reporting_currency_form.html', {'form': form})

# Delete an existing Reporting Currency
@login_required
def reporting_currency_delete(request, currency_id):
    reporting_currency = get_object_or_404(ReportingCurrency, pk=currency_id)
    if request.method == 'POST':
        reporting_currency.delete()
        messages.success(request, "Reporting currency deleted successfully!")
        return redirect('reporting_currency_list')
    return render(request, 'ifrs9_conf/reporting_currency_confirm_delete.html', {'reporting_currency': reporting_currency})

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# List Reporting Currency (since there should only be one)
@login_required
def define_currency_view(request):
    currencies_list = CurrencyCode.objects.all()  # Fetch all defined currencies

    paginator = Paginator(currencies_list, 5)  # Display 5 currencies per page
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver the first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. too high), deliver last page of results
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'ifrs9_conf/define_reporting_currency_list.html', {
        'page_obj': page_obj,  # Pass the page object to the template
    })

# Create Reporting Currency (only if there isn't one already)
@login_required
def define_currency_create(request):
    
    
    if request.method == 'POST':
        form = CurrencyCodeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Reporting currency added successfully!")
            return redirect('define_reporting_currency_view')
        else:
            messages.error(request, f"Error adding reporting currency: {form.errors}")
    else:
        form = CurrencyCodeForm()
    
    return render(request, 'ifrs9_conf/reporting_currency_form.html', {'form': form})

# Edit the existing Reporting Currency
@login_required
def define_currency_edit(request, currency_id):
    reporting_currency = get_object_or_404(CurrencyCode, pk=currency_id)  # Fetch from CurrencyCode table
    if request.method == 'POST':
        form = CurrencyCodeForm(request.POST, instance=reporting_currency)
        if form.is_valid():
            form.save()
            messages.success(request, "Reporting currency updated successfully!")
            return redirect('define_reporting_currency_view')
        else:
            messages.error(request, f"Error updating reporting currency: {form.errors}")
    else:
        form = CurrencyCodeForm(instance=reporting_currency)
    
    return render(request, 'ifrs9_conf/reporting_currency_form.html', {'form': form})

# Delete the existing Reporting Currency
@login_required
def define_currency_delete(request, currency_id):
    reporting_currency = get_object_or_404(CurrencyCode, pk=currency_id)  # Fetch from CurrencyCode table
    if request.method == 'POST':
        reporting_currency.delete()
        messages.success(request, "Reporting currency deleted successfully!")
        return redirect('define_reporting_currency_view')
    return render(request, 'ifrs9_conf/define_reporting_currency_confirm_delete.html', {'reporting_currency': reporting_currency})


@login_required
def configure_exchange_rates_options(request):
    return render(request, 'ifrs9_conf/configure_exchange_rates_options.html')

@login_required
def supported_currencies(request):
    # This is a static view, so no need to fetch anything from the database
    return render(request, 'ifrs9_conf/supported_currencies.html')


# List and Display view
@login_required
def configure_exchange_rate_process(request):
    exchange_conf_list = DimExchangeRateConf.objects.all()
    return render(request, 'ifrs9_conf/configure_exchange_rate_process.html', {'exchange_conf_list': exchange_conf_list})

@login_required
def add_exchange_rate_conf(request):
    if request.method == 'POST':
        form = ExchangeRateConfForm(request.POST)
        if form.is_valid():
            # Save the form without committing to the database yet
            exchange_rate = form.save(commit=False)
            # Set the created_by field to the currently logged-in user
            exchange_rate.created_by = request.user
            # Save the object to the database
            exchange_rate.save()
            # Log the creation in the AuditTrail
            AuditTrail.objects.create(
                    user=request.user,
                    model_name='DimExchangeRateConf',
                    action='create',
                    object_id=exchange_rate.pk,
                    change_description=(
                        f"Created Exchange Rate Config: Use On Exchange Rates - {exchange_rate.use_on_exchange_rates}, "
                        f"Use Latest Exchange Rates - {exchange_rate.use_latest_exchange_rates}"
                    ),
                    timestamp=now(),
                )
            messages.success(request, 'Configuration added successfully!')
            return redirect('configure_exchange_rate_process')
    else:
        form = ExchangeRateConfForm()
    return render(request, 'ifrs9_conf/configure_add_exchange_rate_conf.html', {'form': form})

# Edit view
# Edit view
@login_required
def edit_exchange_rate_conf(request, id):
    exchange_conf = get_object_or_404(DimExchangeRateConf, id=id)
    if request.method == 'POST':
        form = ExchangeRateConfForm(request.POST, instance=exchange_conf)
        if form.is_valid():
            try:
                # Save the form without committing to the database yet
                previous_config = {
                    "use_on_exchange_rates": exchange_conf.use_on_exchange_rates,
                    "use_latest_exchange_rates": exchange_conf.use_latest_exchange_rates,
                }
                exchange_rate = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
                exchange_rate.created_by = request.user
                # Save the object to the database
                exchange_rate.save()

                # Log the update in the AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    model_name='DimExchangeRateConf',
                    action='update',
                    object_id=exchange_rate.pk,
                    change_description=(
                        f"Updated Exchange Rate Config: From {previous_config} to "
                        f"{form.cleaned_data}"
                    ),
                    timestamp=now(),
                )

                messages.success(request, 'Configuration updated successfully!')
                return redirect('configure_exchange_rate_process')
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
    else:
        form = ExchangeRateConfForm(instance=exchange_conf)
    return render(request, 'ifrs9_conf/edit_exchange_rate_conf.html', {'form': form})

# Delete view
@login_required
def delete_exchange_rate_conf(request, id):
    exchange_conf = get_object_or_404(DimExchangeRateConf, id=id)
    if request.method == 'POST':
        try:
            # Log the deletion in the AuditTrail
            AuditTrail.objects.create(
                user=request.user,
                model_name='DimExchangeRateConf',
                action='delete',
                object_id=exchange_conf.pk,
                change_description=(
                    f"Deleted Exchange Rate Config: Use On Exchange Rates - {exchange_conf.use_on_exchange_rates}, "
                    f"Use Latest Exchange Rates - {exchange_conf.use_latest_exchange_rates}"
                ),
                timestamp=now(),
            )

            exchange_conf.delete()
            messages.success(request, 'Configuration deleted successfully!')
            return redirect('configure_exchange_rate_process')
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
    return render(request, 'ifrs9_conf/delete_exchange_rate_conf.html', {'exchange_conf': exchange_conf})

@login_required
def view_exchange_rate(request):
    exchange_rate = None
    error = None
    base_currency = None
    currencies = CurrencyCode.objects.all()  # Fetch all available base currencies from the CurrencyCode table

    if request.method == 'POST':
        currency_code = request.POST.get('currency_code').upper()
        base_currency = request.POST.get('base_currency')

        # Example API call for exchange rate (replace with actual API and key)
        api_url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        response = requests.get(api_url)

        if response.status_code == 200:
            data = response.json()
            exchange_rate = {
                'base_currency': base_currency,
                'currency_code': currency_code,
                'rate': data['rates'].get(currency_code, 'Rate not found')  # Use dynamic base currency
            }
        else:
            error = "Invalid currency code or API error."

    return render(request, 'ifrs9_conf/exchange_rate.html', {
        'exchange_rate': exchange_rate,
        'error': error,
        'currencies': currencies,  # Pass the currencies to the template for the dropdown
        'base_currency': base_currency
    })