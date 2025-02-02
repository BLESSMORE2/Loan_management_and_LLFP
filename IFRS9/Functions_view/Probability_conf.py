from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import *
from ..forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import IntegrityError




@login_required
def probability_configuration(request):
    return render(request, 'probability_conf/probability_configuration.html')

@login_required
def pd_modelling(request):
    # Logic for PD Modelling
    return render(request, 'probability_conf/pd_modelling.html')


# List all segments with pagination
@login_required
def segment_list(request):
    segments = FSI_Product_Segment.objects.all()
    rows_per_page = int(request.GET.get('rows', 5))  # Default to 8 rows per page
    paginator = Paginator(segments, rows_per_page)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate the number of empty rows to add if there are fewer than `rows_per_page` on the page
    empty_rows = rows_per_page - len(page_obj)

    return render(request, 'probability_conf/segment_list.html', {
        'page_obj': page_obj,
        'rows_per_page': rows_per_page,
        'empty_rows': range(empty_rows)  # Pass a range object to loop through empty rows in the template
    })


# Create new segment
@login_required
def segment_create(request):
    if request.method == "POST":
        form = FSIProductSegmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Segment added successfully!")
            return redirect('segment_list')
        else:
            error_message = form.errors.as_json()
            messages.error(request, f"There was an error in adding the segment: {error_message}")
    else:
        form = FSIProductSegmentForm()
    return render(request, 'probability_conf/segment_form.html', {'form': form})

@login_required
def get_product_types(request):
    segment = request.GET.get('segment')
    if segment:
        types = Ldn_Bank_Product_Info.objects.filter(v_prod_segment=segment).values_list('v_prod_type', flat=True).distinct()
        type_choices = [{'value': t, 'display': t} for t in types]
    else:
        type_choices = []
    return JsonResponse(type_choices, safe=False)

@login_required
def get_product_description(request):
    product_type = request.GET.get('product_type')
    if product_type:
        description = Ldn_Bank_Product_Info.objects.filter(v_prod_type=product_type).values_list('v_prod_desc', flat=True).first()
        return JsonResponse({'description': description})
    return JsonResponse({'description': ''})


# Update existing segment
@login_required
def segment_edit(request, segment_id):
    segment = get_object_or_404(FSI_Product_Segment, pk=segment_id)
    
    if request.method == "POST":
        form = FSIProductSegmentForm(request.POST, instance=segment)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Segment updated successfully!")
                return redirect('segment_list')
            except IntegrityError as e:
                # Handle duplicate entry or unique constraint errors
                messages.error(request, f"Integrity error: {e}")
            except Exception as e:
                # Handle any other unexpected errors
                messages.error(request, f"An unexpected error occurred: {e}")
        else:
            # General message for validation errors; specific errors will show in the form
            messages.error(request, "There were errors in the form. Please correct them below.")
    else:
        form = FSIProductSegmentForm(instance=segment)
    
    return render(request, 'probability_conf/segment_form.html', {'form': form})

# Delete segment
@login_required
def segment_delete(request, segment_id):
    segment = get_object_or_404(FSI_Product_Segment, pk=segment_id)
    if request.method == "POST":
        segment.delete()
        messages.success(request, "Segment deleted successfully!")
        return redirect('segment_list')
    return render(request, 'probability_conf/segment_confirm_delete.html', {'segment': segment})

@login_required
def pd_term_structure_list(request):
    term_structures_list = Ldn_PD_Term_Structure.objects.all()
    
    # Set up pagination
    paginator = Paginator(term_structures_list, 5)  # Show 5 items per page
    page_number = request.GET.get('page')
    term_structures = paginator.get_page(page_number)  # Get the page of items

    return render(request, 'probability_conf/pd_term_structure_list.html', {'term_structures': term_structures})

# Create new PD Term Structure
@login_required
def pd_term_structure_create(request):
    if request.method == "POST":
        form = PDTermStructureForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "PD Term Structure added successfully!")
                return redirect('pd_term_structure_list')
            except IntegrityError as e:
                # Handle duplicate entry error with the specific exception message
                messages.error(request, f"Error adding PD Term Structure: {e}")
            except Exception as e:
                # Handle any other exceptions
                messages.error(request, f"An unexpected error occurred: {e}")
        else:
            # Display form validation errors
            messages.error(request, "There were errors in the form. Please correct them below.")
    else:
        form = PDTermStructureForm()

    return render(request, 'probability_conf/pd_term_structure_form.html', {'form': form})

@login_required
def pd_term_structure_edit(request, term_id):
    term_structure = get_object_or_404(Ldn_PD_Term_Structure, pk=term_id)
    
    if request.method == "POST":
        form = PDTermStructureForm(request.POST, instance=term_structure)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "PD Term Structure updated successfully!")
                return redirect('pd_term_structure_list')
            except IntegrityError as e:
                # Handle duplicate entry error with the specific exception message
                messages.error(request, f"Error updating PD Term Structure: {e}")
            except Exception as e:
                # Catch any other exceptions and show the error message
                messages.error(request, f"An unexpected error occurred: {e}")
        else:
            messages.error(request, "There were validation errors. Please correct them below.")
    else:
        form = PDTermStructureForm(instance=term_structure)
    
    return render(request, 'probability_conf/pd_term_structure_form.html', {'form': form})
# Delete PD Term Structure
@login_required
def pd_term_structure_delete(request, term_id):
    term_structure = get_object_or_404(Ldn_PD_Term_Structure, pk=term_id)
    if request.method == "POST":
        term_structure.delete()
        messages.success(request, "PD Term Structure deleted successfully!")
        return redirect('pd_term_structure_list')
    return render(request, 'probability_conf/pd_term_structure_confirm_delete.html', {'term_structure': term_structure})


####################################33
# List all Delinquent Based PD Terms
@login_required
def delinquent_pd_list(request):
    # Filter for 'Delinquent' type PD Term Structures
    pd_term_details_list = Ldn_PD_Term_Structure_Dtl.objects.filter(
        v_pd_term_structure_id__v_pd_term_structure_type='D'
    ).select_related('v_pd_term_structure_id')
    
    # Set up pagination with 5 items per page
    paginator = Paginator(pd_term_details_list, 5)
    page_number = request.GET.get('page')
    pd_term_details = paginator.get_page(page_number)

    return render(request, 'probability_conf/delinquent_pd_list.html', {'pd_term_details': pd_term_details})

# Create a new PD Term Detail
@login_required
def delinquent_pd_create(request):
    if request.method == 'POST':
        form = PDTermStructureDtlForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Delinquent PD Term added successfully!")
                return redirect('delinquent_pd_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error adding Delinquent PD Term: {e}")
        else:
            # Display form validation errors
            messages.error(request, "There were validation errors. Please correct them below.")
    else:
        form = PDTermStructureDtlForm()
    
    return render(request, 'probability_conf/delinquent_pd_form.html', {'form': form})

# Edit PD Term Detail
@login_required
def delinquent_pd_edit(request, term_id):
    pd_term_detail = get_object_or_404(Ldn_PD_Term_Structure_Dtl, pk=term_id)
    
    if request.method == 'POST':
        form = PDTermStructureDtlForm(request.POST, instance=pd_term_detail)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Delinquent PD Term updated successfully!")
                return redirect('delinquent_pd_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error updating Delinquent PD Term: {e}")
        else:
            # Display form validation errors
            messages.error(request, "There were validation errors. Please correct them below.")
    else:
        form = PDTermStructureDtlForm(instance=pd_term_detail)
    
    return render(request, 'probability_conf/delinquent_pd_form.html', {'form': form})
# Delete PD Term Detail
@login_required
def delinquent_pd_delete(request, term_id):
    pd_term_detail = get_object_or_404(Ldn_PD_Term_Structure_Dtl, pk=term_id)
    if request.method == 'POST':
        pd_term_detail.delete()
        messages.success(request, "Delinquent PD Term deleted successfully!")
        return redirect('delinquent_pd_list')
    return render(request, 'probability_conf/delinquent_pd_confirm_delete.html', {'pd_term_detail': pd_term_detail})

# List View
# List all Rating Based PD Terms
@login_required
def rating_pd_list(request):
    # Filter for 'Rating' type PD Term Structures
    pd_term_details_list = Ldn_PD_Term_Structure_Dtl.objects.filter(
        v_pd_term_structure_id__v_pd_term_structure_type='R'
    ).select_related('v_pd_term_structure_id')
    
    # Set up pagination with 5 items per page
    paginator = Paginator(pd_term_details_list, 5)
    page_number = request.GET.get('page')
    pd_term_details = paginator.get_page(page_number)

    return render(request, 'probability_conf/rating_pd_list.html', {'pd_term_details': pd_term_details})

# Create a new Rating Based PD Term Detail
@login_required
def rating_pd_create(request):
    if request.method == 'POST':
        form = PDTermStructureDtlRatingForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Rating Based PD Term added successfully!")
                return redirect('rating_pd_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error adding Rating Based PD Term: {e}")
    else:
        form = PDTermStructureDtlRatingForm()
    
    return render(request, 'probability_conf/rating_pd_form.html', {'form': form})

# Edit Rating Based PD Term Detail
@login_required
def rating_pd_edit(request, term_id):
    pd_term_detail = get_object_or_404(Ldn_PD_Term_Structure_Dtl, pk=term_id)
    if request.method == 'POST':
        form = PDTermStructureDtlRatingForm(request.POST, instance=pd_term_detail)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Rating Based PD Term updated successfully!")
                return redirect('rating_pd_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error updating Rating Based PD Term: {e}")
        
    else:
        form = PDTermStructureDtlRatingForm(instance=pd_term_detail)
    
    return render(request, 'probability_conf/rating_pd_form.html', {'form': form})

# Delete Rating Based PD Term Detail
@login_required
def rating_pd_delete(request, term_id):
    pd_term_detail = get_object_or_404(Ldn_PD_Term_Structure_Dtl, pk=term_id)
    if request.method == 'POST':
        pd_term_detail.delete()
        messages.success(request, "Rating Based PD Term deleted successfully!")
        return redirect('rating_pd_list')
    return render(request, 'probability_conf/rating_pd_confirm_delete.html', {'pd_term_detail': pd_term_detail})



# List all Interpolation Methods
@login_required
def interpolation_method_list(request):
    preferences = FSI_LLFP_APP_PREFERENCES.objects.all()
    return render(request, 'probability_conf/interpolation_method_list.html', {'preferences': preferences})

# Create a new Interpolation Method
@login_required
def interpolation_method_create(request):
    if request.method == 'POST':
        form = InterpolationMethodForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Interpolation Method added successfully!")
                return redirect('interpolation_method_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error adding Interpolation Method: {e}")
        else:
            # Display form validation errors
            messages.error(request, "There were validation errors. Please correct them below.")
    else:
        form = InterpolationMethodForm()

    return render(request, 'probability_conf/interpolation_method_form.html', {'form': form})
# Edit Interpolation Method
@login_required
def interpolation_method_edit(request, method_id):
    interpolation_method = get_object_or_404(FSI_LLFP_APP_PREFERENCES, pk=method_id)
    
    if request.method == 'POST':
        form = InterpolationMethodForm(request.POST, instance=interpolation_method)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Interpolation Method updated successfully!")
                return redirect('interpolation_method_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error updating Interpolation Method: {e}")
        else:
            # Display form validation errors
            messages.error(request, "There were validation errors. Please correct them below.")
    else:
        form = InterpolationMethodForm(instance=interpolation_method)

    return render(request, 'probability_conf/interpolation_method_form.html', {'form': form})

# Delete Interpolation Method
@login_required
def interpolation_method_delete(request, method_id):
    interpolation_method = get_object_or_404(FSI_LLFP_APP_PREFERENCES, pk=method_id)
    if request.method == 'POST':
        interpolation_method.delete()
        messages.success(request, "Interpolation Method deleted successfully!")
        return redirect('interpolation_method_list')

    return render(request, 'probability_conf/interpolation_method_confirm_delete.html', {'interpolation_method': interpolation_method})