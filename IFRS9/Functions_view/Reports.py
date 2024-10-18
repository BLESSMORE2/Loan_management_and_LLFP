from django.shortcuts import render, get_object_or_404
from ..models import FCT_Reporting_Lines, ReportColumnConfig
from django.db.models import Max
from django.contrib import messages
import csv
from datetime import datetime
from django.http import HttpResponse
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def reporting_home(request):
    return render(request, 'reports/reporting.html')
def list_reports(request):
    # This view will render the list of available reports
    return render(request, 'reports/list_reports.html')

def view_results_and_extract(request):
    # Get the latest `fic_mis_date` and `n_run_key`
    latest_fic_mis_date = FCT_Reporting_Lines.objects.aggregate(Max('fic_mis_date'))['fic_mis_date__max']
    latest_n_run_key = FCT_Reporting_Lines.objects.aggregate(Max('n_run_key'))['n_run_key__max']
    
    # Fetch FIC MIS Date and Run Key from the request, default to latest if not provided
    fic_mis_date = request.GET.get('fic_mis_date', latest_fic_mis_date)
    n_run_key = request.GET.get('n_run_key', latest_n_run_key)

    # Ensure FIC MIS Date and Run Key are provided, these are mandatory
    if not fic_mis_date or not n_run_key:
        messages.error(request, "Both FIC MIS Date and Run Key are required.")
        return render(request, 'reports/report_view.html', {
            'selected_columns': [],
            'report_data': [],
            'filters': request.GET,
            'latest_fic_mis_date': latest_fic_mis_date,
            'latest_n_run_key': latest_n_run_key,
            'fic_mis_date': fic_mis_date,
            'n_run_key': n_run_key,
        })

    # Apply filters, ensuring FIC MIS Date and Run Key are always included
    filters = {
        'fic_mis_date': fic_mis_date,
        'n_run_key': n_run_key,
    }

    # Dynamically add optional filters if they have a valid value
    if request.GET.get('n_prod_code'):
        filters['n_prod_code'] = request.GET.get('n_prod_code')
    
    if request.GET.get('n_prod_type'):
        filters['n_prod_type'] = request.GET.get('n_prod_type')
    
    if request.GET.get('n_pd_term_structure_name'):
        filters['n_pd_term_structure_name'] = request.GET.get('n_pd_term_structure_name')

    if request.GET.get('n_curr_ifrs_stage_skey'):
        try:
            filters['n_curr_ifrs_stage_skey'] = int(request.GET.get('n_curr_ifrs_stage_skey'))
        except ValueError:
            messages.error(request, "Invalid IFRS Stage Key. Please enter a valid number.")
            return render(request, 'reports/report_view.html', {
                'selected_columns': [],
                'report_data': [],
                'filters': request.GET,
                'latest_fic_mis_date': latest_fic_mis_date,
                'latest_n_run_key': latest_n_run_key,
                'fic_mis_date': fic_mis_date,
                'n_run_key': n_run_key,
            })

    # Fetch the saved column mappings for the report
    report_config = get_object_or_404(ReportColumnConfig, report_name="default_report")
    selected_columns = report_config.selected_columns

    # Query the FCT_Reporting_Lines table using only the selected columns and applied filters
    report_data = FCT_Reporting_Lines.objects.filter(**filters).values(*selected_columns)

    # Paginate the report data
    paginator = Paginator(report_data, 25)  # Show 25 results per page
    page = request.GET.get('page', 1)

    try:
        paginated_report_data = paginator.page(page)
    except PageNotAnInteger:
        paginated_report_data = paginator.page(1)
    except EmptyPage:
        paginated_report_data = paginator.page(paginator.num_pages)

    # Pass the data and the selected columns to the template
    context = {
        'selected_columns': selected_columns,
        'report_data': paginated_report_data,  # Pass paginated data
        'filters': filters,
        'latest_fic_mis_date': latest_fic_mis_date,
        'latest_n_run_key': latest_n_run_key,
        'fic_mis_date': fic_mis_date,  # Pass FIC MIS Date to template
        'n_run_key': n_run_key,        # Pass Run Key to template
    }
    return render(request, 'reports/report_view.html', context)



def download_report(request):
    # Fetch the same filters as used in the view_results_and_extract
    filters = {
        'fic_mis_date': request.GET.get('fic_mis_date'),
        'n_run_key': request.GET.get('n_run_key'),
        'n_prod_code': request.GET.get('n_prod_code'),
        'n_prod_type': request.GET.get('n_prod_type'),
        'n_pd_term_structure_name': request.GET.get('n_pd_term_structure_name'),
        'n_curr_ifrs_stage_skey': request.GET.get('n_curr_ifrs_stage_skey'),
    }
    
    # Remove None values from filters
    filters = {k: v for k, v in filters.items() if v is not None}

    # Fetch the saved column mappings
    report_config = ReportColumnConfig.objects.get(report_name="default_report")
    selected_columns = report_config.selected_columns

    # Query the FCT_Reporting_Lines with the filters
    report_data = FCT_Reporting_Lines.objects.filter(**filters).values(*selected_columns)

    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report.csv"'

    # Write the selected columns as the header
    writer = csv.writer(response)
    writer.writerow(selected_columns)

    # Write the data rows
    for row in report_data:
        writer.writerow([row[column] for column in selected_columns])

    return response


############################################


def ecl_summary_report(request):
   

    # Main filter form fields
    fic_mis_date = request.GET.get('fic_mis_date')
    n_run_key = request.GET.get('n_run_key')

    # Sub-filter form fields
    v_ccy_code = request.GET.get('v_ccy_code')
    n_prod_segment = request.GET.get('n_prod_segment')
    n_prod_type = request.GET.get('n_prod_type')
    n_stage_descr = request.GET.get('n_stage_descr')
    n_loan_type = request.GET.get('n_loan_type')

    ecl_data = None  # No data until main filter is applied

    # Only fetch ecl_data when both fic_mis_date and n_run_key are provided
    if fic_mis_date and n_run_key:
        ecl_data = FCT_Reporting_Lines.objects.filter(fic_mis_date=fic_mis_date, n_run_key=n_run_key)

        # Distinct values for sub-filters, ordered alphabetically
        distinct_currency_codes = ecl_data.values_list('v_ccy_code', flat=True).distinct().order_by('v_ccy_code')
        distinct_prod_segments = ecl_data.values_list('n_prod_segment', flat=True).distinct().order_by('n_prod_segment')
        distinct_prod_types = ecl_data.values_list('n_prod_type', flat=True).distinct().order_by('n_prod_type')
        distinct_stage_descrs = ecl_data.values_list('n_stage_descr', flat=True).distinct().order_by('n_stage_descr')
        distinct_loan_types = ecl_data.values_list('n_loan_type', flat=True).distinct().order_by('n_loan_type')

        # Apply sub-filters if provided
        if v_ccy_code:
            ecl_data = ecl_data.filter(v_ccy_code=v_ccy_code)
        if n_prod_segment:
            ecl_data = ecl_data.filter(n_prod_segment=n_prod_segment)
        if n_prod_type:
            ecl_data = ecl_data.filter(n_prod_type=n_prod_type)
        if n_stage_descr:
            ecl_data = ecl_data.filter(n_stage_descr=n_stage_descr)
        if n_loan_type:
            ecl_data = ecl_data.filter(n_loan_type=n_loan_type)

    # Check for an AJAX request to dynamically update the dropdowns
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        field_name = request.GET.get('field')
        field_value = request.GET.get('value')

        if field_name == 'fic_mis_date':
            # Get corresponding run keys based on the selected fic_mis_date
            n_run_keys = FCT_Reporting_Lines.objects.filter(fic_mis_date=field_value).order_by('-n_run_key').values_list('n_run_key', flat=True).distinct()
            return JsonResponse({'n_run_keys': list(n_run_keys)})
    
    context = {
        'fic_mis_dates': FCT_Reporting_Lines.objects.order_by('-fic_mis_date').values_list('fic_mis_date', flat=True).distinct(),
        'distinct_currency_codes': distinct_currency_codes if fic_mis_date and n_run_key else [],
        'distinct_prod_segments': distinct_prod_segments if fic_mis_date and n_run_key else [],
        'distinct_prod_types': distinct_prod_types if fic_mis_date and n_run_key else [],
        'distinct_stage_descrs': distinct_stage_descrs if fic_mis_date and n_run_key else [],
        'distinct_loan_types': distinct_loan_types if fic_mis_date and n_run_key else [],
        'ecl_data': ecl_data,
    }
    return render(request, 'reports/ecl_summary_report.html', context)