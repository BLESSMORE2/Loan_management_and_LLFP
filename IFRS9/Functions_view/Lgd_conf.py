from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from ..models import Ldn_LGD_Term_Structure,CollateralLGD
from ..forms import LGDTermStructureForm,CollateralLGDForm
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from Users.models import AuditTrail  # Import AuditTrail model
from django.utils.timezone import now  # For timestamping



@login_required
def lgd_configuration(request):
    return render(request, 'lgd_conf/lgd_configuration.html')



# List all LGD Term Structures
@login_required
def lgd_term_structure_list(request):
    term_structures = Ldn_LGD_Term_Structure.objects.all()
    return render(request, 'lgd_conf/lgd_term_structure_list.html', {'term_structures': term_structures})

# Create a new LGD Term Structure
@login_required
@permission_required('IFRS9.add_ldn_lgd_term_structure', raise_exception=True)
def lgd_term_structure_create(request):
    if request.method == 'POST':
        form = LGDTermStructureForm(request.POST)
        if form.is_valid():
            # Save the form without committing to the database yet
            term_structure = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
            term_structure.created_by = request.user
                # Save the object to the database
            term_structure.save()
            # Log the creation in the AuditTrail
            AuditTrail.objects.create(
                    user=request.user,
                    model_name='Ldn_LGD_Term_Structure',
                    action='create',
                    object_id=term_structure.pk,
                    change_description=(f"Created LGD Term Structure: Name - {term_structure.v_lgd_term_structure_name}, "
                                        f"Description - {term_structure.v_lgd_term_structure_desc}, LGD% - {term_structure.n_lgd_percent}"),
                    timestamp=now(),
                )

            messages.success(request, "LGD Term Structure added successfully!")
            return redirect('lgd_term_structure_list')
        else:
            messages.error(request, "Error adding LGD Term Structure.")
    else:
        form = LGDTermStructureForm()
    
    return render(request, 'lgd_conf/lgd_term_structure_form.html', {'form': form})

# Edit LGD Term Structure
@login_required
@permission_required('IFRS9.change_ldn_lgd_term_structure', raise_exception=True)
def lgd_term_structure_edit(request, term_id):
    term_structure = get_object_or_404(Ldn_LGD_Term_Structure, pk=term_id)
    if request.method == 'POST':
        form = LGDTermStructureForm(request.POST, instance=term_structure)
        if form.is_valid():
            term_structure = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
            term_structure.created_by = request.user
                # Save the object to the database
            term_structure.save()
            # Log the update in the AuditTrail
            AuditTrail.objects.create(
                    user=request.user,
                    model_name='Ldn_LGD_Term_Structure',
                    action='update',
                    object_id=term_structure.pk,
                    change_description=(f"Updated LGD Term Structure: Name - {term_structure.v_lgd_term_structure_name}, "
                                        f"Description - {term_structure.v_lgd_term_structure_desc}, LGD% - {term_structure.n_lgd_percent}"),
                    timestamp=now(),
                )
          
            messages.success(request, "LGD Term Structure updated successfully!")
            return redirect('lgd_term_structure_list')
        else:
            messages.error(request, "Error updating LGD Term Structure.")
    else:
        form = LGDTermStructureForm(instance=term_structure)
    
    return render(request, 'lgd_conf/lgd_term_structure_form.html', {'form': form})

# Delete LGD Term Structure
@login_required
@permission_required('IFRS9.delete_ldn_lgd_term_structure', raise_exception=True)
def lgd_term_structure_delete(request, term_id):
    term_structure = get_object_or_404(Ldn_LGD_Term_Structure, pk=term_id)
    if request.method == 'POST':
        # Log the deletion in the AuditTrail
        AuditTrail.objects.create(
                user=request.user,
                model_name='Ldn_LGD_Term_Structure',
                action='delete',
                object_id=term_structure.pk,
                change_description=(f"Deleted LGD Term Structure: Name - {term_structure.v_lgd_term_structure_name}, "
                                    f"Description - {term_structure.v_lgd_term_structure_desc}, LGD% - {term_structure.n_lgd_percent}"),
                timestamp=now(),
            )
        term_structure.delete()
        messages.success(request, "LGD Term Structure deleted successfully!")
        return redirect('lgd_term_structure_list')
    return render(request, 'lgd_conf/lgd_term_structure_confirm_delete.html', {'term_structure': term_structure})



@login_required
def view_lgd_calculation(request):
    # Try to retrieve the single CollateralLGD instance
    lgd_instance = CollateralLGD.objects.first()

    # If no instance exists, create one with default values
    if not lgd_instance:
        try:
            lgd_instance = CollateralLGD.objects.create(can_calculate_lgd=False)
        except ValidationError as e:
            return render(request, 'lgd_conf/view_lgd_calculation.html', {'error': str(e)})

    # Pass the instance to the template
    return render(request, 'lgd_conf/view_lgd_calculation.html', {'lgd_instance': lgd_instance})

@login_required

@permission_required('IFRS9.change_collaterallgd', raise_exception=True)
def edit_lgd_calculation(request):
    """Edit the LGD Calculation settings"""
    # Retrieve the first instance of CollateralLGD, or show a 404 if none exists
    lgd_instance = CollateralLGD.objects.first()

    if not lgd_instance:
        messages.error(request, "No LGD Calculation data available to edit.")
        return redirect('view_lgd_calculation')  # Redirect to a safer page

    if request.method == 'POST':
        form = CollateralLGDForm(request.POST, instance=lgd_instance)
        if form.is_valid():
            form.save()
            messages.success(request, "LGD Calculation settings updated successfully!")
            return redirect('view_lgd_calculation')
        else:
            messages.error(request, "Error updating LGD Calculation settings.")
    else:
        form = CollateralLGDForm(instance=lgd_instance)

    return render(request, 'lgd_conf/edit_lgd_calculation.html', {'form': form})