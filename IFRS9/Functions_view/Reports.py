from django.shortcuts import render, get_object_or_404
from ..models import FCT_Reporting_Lines, ReportColumnConfig
from django.db.models import Max
from django.contrib import messages
import csv
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def reporting_home(request):
    return render(request, 'reports/reporting.html')

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