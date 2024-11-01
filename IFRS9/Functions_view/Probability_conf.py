from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import *
from ..forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


@login_required
def probability_configuration(request):
    return render(request, 'probability_conf/probability_configuration.html')

@login_required
def pd_modelling(request):
    # Logic for PD Modelling
    return render(request, 'probability_conf/pd_modelling.html')


# List all segments
@login_required
def segment_list(request):
    segments = FSI_Product_Segment.objects.all()
    return render(request, 'probability_conf/segment_list.html', {'segments': segments})

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
            form.save()
            messages.success(request, "Segment updated successfully!")
            return redirect('segment_list')
        else:
            # Include actual error messages
            error_message = form.errors.as_json()
            messages.error(request, f"There was an error in updating the segment: {error_message}")
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

# List all PD Term Structures
@login_required
def pd_term_structure_list(request):
    term_structures = Ldn_PD_Term_Structure.objects.all()
    return render(request, 'probability_conf/pd_term_structure_list.html', {'term_structures': term_structures})

# Create new PD Term Structure
@login_required
def pd_term_structure_create(request):
    if request.method == "POST":
        form = PDTermStructureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "PD Term Structure added successfully!")
            return redirect('pd_term_structure_list')
        else:
            # Display specific form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        form = PDTermStructureForm()
    return render(request, 'probability_conf/pd_term_structure_form.html', {'form': form})

# Edit PD Term Structure
@login_required
def pd_term_structure_edit(request, term_id):
    term_structure = get_object_or_404(Ldn_PD_Term_Structure, pk=term_id)
    if request.method == "POST":
        form = PDTermStructureForm(request.POST, instance=term_structure)
        if form.is_valid():
            form.save()
            messages.success(request, "PD Term Structure updated successfully!")
            return redirect('pd_term_structure_list')
        else:
            # Display specific form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
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
    pd_term_details = Ldn_PD_Term_Structure_Dtl.objects.filter(
        v_pd_term_structure_id__v_pd_term_structure_type='D'  # Filter for 'Rating' type PD Term Structures
    ).select_related('v_pd_term_structure_id')
    return render(request, 'probability_conf/delinquent_pd_list.html', {'pd_term_details': pd_term_details})

# Create a new PD Term Detail
@login_required
def delinquent_pd_create(request):
    if request.method == 'POST':
        form = PDTermStructureDtlForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Delinquent PD Term added successfully!")
            return redirect('delinquent_pd_list')
        else:
            messages.error(request, f"Error adding Delinquent PD Term: {form.errors}")
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
            form.save()
            messages.success(request, "Delinquent PD Term updated successfully!")
            return redirect('delinquent_pd_list')
        else:
            messages.error(request, f"Error updating Delinquent PD Term: {form.errors}")
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
    pd_term_details = Ldn_PD_Term_Structure_Dtl.objects.filter(
        v_pd_term_structure_id__v_pd_term_structure_type='R'  # Filter for 'Rating' type PD Term Structures
    ).select_related('v_pd_term_structure_id')
    
    return render(request, 'probability_conf/rating_pd_list.html', {'pd_term_details': pd_term_details})

# Create a new Rating Based PD Term Detail
@login_required
def rating_pd_create(request):
    if request.method == 'POST':
        form = PDTermStructureDtlRatingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Rating Based PD Term added successfully!")
            return redirect('rating_pd_list')
        else:
            messages.error(request, "Error adding Rating Based PD Term.")
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
            form.save()
            messages.success(request, "Rating Based PD Term updated successfully!")
            return redirect('rating_pd_list')
        else:
            messages.error(request, "Error updating Rating Based PD Term.")
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
            form.save()
            messages.success(request, "Interpolation Method added successfully!")
            return redirect('interpolation_method_list')
        else:
            messages.error(request, "Error adding Interpolation Method.")
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
            form.save()
            messages.success(request, "Interpolation Method updated successfully!")
            return redirect('interpolation_method_list')
        else:
            messages.error(request, "Error updating Interpolation Method.")
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