from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from ..models import Ldn_LGD_Term_Structure,CollateralLGD,FSI_LGD_Term_Structure
from ..forms import LGDTermStructureForm,CollateralLGDForm,LGDTermStructureDtlRatingForm,LGDTermStructureDtlForm
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from Users.models import AuditTrail  # Import AuditTrail model
from django.utils.timezone import now  # For timestamping
from django.core.paginator import Paginator




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
            # Log the update in the AuditTrail
            AuditTrail.objects.create(
                    user=request.user,
                    model_name='CollateralLGD',
                    action='update',
                    object_id=lgd_instance.pk,
                    change_description=f"Updated LGD Calculation settings. Changes: {form.changed_data}",
                    timestamp=now(),
                )
            messages.success(request, "LGD Calculation settings updated successfully!")
            return redirect('view_lgd_calculation')
        else:
            messages.error(request, "Error updating LGD Calculation settings.")
    else:
        form = CollateralLGDForm(instance=lgd_instance)

    return render(request, 'lgd_conf/edit_lgd_calculation.html', {'form': form})



####################################33
# List all Delinquent Based PD Terms
@login_required
def delinquent_pd_list(request):
    # Filter for 'Delinquent' type PD Term Structures
    pd_term_details_list = FSI_LGD_Term_Structure.objects.filter(
        v_pd_term_structure_id__v_pd_term_structure_type='D'
    ).select_related('v_pd_term_structure_id')
    
    # Set up pagination with 5 items per page
    paginator = Paginator(pd_term_details_list, 5)
    page_number = request.GET.get('page')
    pd_term_details = paginator.get_page(page_number)

    return render(request, 'lgd_conf/delinquent_pd_list.html', {'pd_term_details': pd_term_details})

# Create a new PD Term Detail
@login_required
@permission_required('IFRS9.add_FSI_LGD_Term_Structure', raise_exception=True)
def delinquent_pd_create(request):
    if request.method == 'POST':
        form = LGDTermStructureDtlForm(request.POST)
        if form.is_valid():
            try:
                # Save the form without committing to the database yet
                delinquent_pd = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
                delinquent_pd.created_by = request.user
                # Save the object to the database
                delinquent_pd.save()
                 # Log the creation in the AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    model_name='Ldn_PD_Term_Structure_Dtl',
                    action='create',
                    object_id=delinquent_pd.pk,
                    change_description=(
                        f"Created Delinquent PD Term: Structure ID - {delinquent_pd.v_pd_term_structure_id}, "
                        f"Date - {delinquent_pd.fic_mis_date}, Risk Basis - {delinquent_pd.v_credit_risk_basis_cd}, "
                        f"PD Percent - {delinquent_pd.n_pd_percent}"
                    ),
                    timestamp=now(),
                )

                messages.success(request, "Delinquent PD Term added successfully!")
                return redirect('delinquent_pd_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error adding Delinquent PD Term: {e}")
        else:
            # Display form validation errors
            messages.error(request, "There were validation errors. Please correct them below.")
    else:
        form = LGDTermStructureDtlForm()
    
    return render(request, 'lgd_conf/delinquent_pd_form.html', {'form': form})

# Edit PD Term Detail
@login_required
@permission_required('IFRS9.change_FSI_LGD_Term_Structure', raise_exception=True)
def delinquent_pd_edit(request, term_id):
    pd_term_detail = get_object_or_404(FSI_LGD_Term_Structure, pk=term_id)
    
    if request.method == 'POST':
        form = LGDTermStructureDtlForm(request.POST, instance=pd_term_detail)
        if form.is_valid():
            try:
                # Save the form without committing to the database yet
                delinquent_pd = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
                delinquent_pd.created_by = request.user
                # Save the object to the database
                delinquent_pd.save()

                # Log the update in the AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    model_name='Ldn_PD_Term_Structure_Dtl',
                    action='update',
                    object_id=delinquent_pd.pk,
                    change_description=(
                        f"Updated Delinquent PD Term: Structure ID - {delinquent_pd.v_pd_term_structure_id}, "
                        f"Date - {delinquent_pd.fic_mis_date}, Risk Basis - {delinquent_pd.v_credit_risk_basis_cd}, "
                        f"PD Percent - {delinquent_pd.n_pd_percent}"
                    ),
                    timestamp=now(),
                )


                messages.success(request, "Delinquent PD Term updated successfully!")
                return redirect('delinquent_pd_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error updating Delinquent PD Term: {e}")
        else:
            # Display form validation errors
            messages.error(request, "There were validation errors. Please correct them below.")
    else:
        form = LGDTermStructureDtlForm(instance=pd_term_detail)
    
    return render(request, 'lgd_conf/delinquent_pd_form.html', {'form': form})
# Delete PD Term Detail
@login_required
@permission_required('IFRS9.delete_FSI_LGD_Term_Structure', raise_exception=True)
def delinquent_pd_delete(request, term_id):
    pd_term_detail = get_object_or_404(FSI_LGD_Term_Structure, pk=term_id)
    if request.method == 'POST':
         # Log the deletion in the AuditTrail
        AuditTrail.objects.create(
            user=request.user,
            model_name='Ldn_PD_Term_Structure_Dtl',
            action='delete',
            object_id=pd_term_detail.pk,
            change_description=(
                f"Deleted Delinquent Based PD Term: Structure ID - {pd_term_detail.v_pd_term_structure_id}, "
                f"Date - {pd_term_detail.fic_mis_date}, Risk Basis - {pd_term_detail.v_credit_risk_basis_cd}, "
                f"PD Percent - {pd_term_detail.n_pd_percent}"
            ),
            timestamp=now(),
        )
        pd_term_detail.delete()
        messages.success(request, "Delinquent PD Term deleted successfully!")
        return redirect('delinquent_pd_list')
    return render(request, 'lgd_conf/delinquent_pd_confirm_delete.html', {'pd_term_detail': pd_term_detail})

# List View
# List all Rating Based PD Terms
@login_required
def rating_pd_list(request):
    # Filter for 'Rating' type PD Term Structures
    pd_term_details_list = FSI_LGD_Term_Structure.objects.filter(
        v_pd_term_structure_id__v_pd_term_structure_type='R'
    ).select_related('v_pd_term_structure_id')
    
    # Set up pagination with 5 items per page
    paginator = Paginator(pd_term_details_list, 5)
    page_number = request.GET.get('page')
    pd_term_details = paginator.get_page(page_number)

    return render(request, 'lgd_conf/rating_pd_list.html', {'pd_term_details': pd_term_details})

# Create a new Rating Based PD Term Detail
@login_required
@permission_required('IFRS9.add_FSI_LGD_Term_Structure', raise_exception=True)
def rating_pd_create(request):
    if request.method == 'POST':
        form = LGDTermStructureDtlRatingForm(request.POST)
        if form.is_valid():
            try:
                # Save the form without committing to the database yet
                rating = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
                rating.created_by = request.user
                # Save the object to the database
                rating.save()
                # Log the creation in the AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    model_name='Ldn_PD_Term_Structure_Dtl',
                    action='create',
                    object_id=rating.pk,
                    change_description=(
                        f"Created Rating Based PD Term: Structure ID - {rating.v_pd_term_structure_id}, "
                        f"Date - {rating.fic_mis_date}, Risk Basis - {rating.v_credit_risk_basis_cd}, "
                        f"PD Percent - {rating.n_pd_percent}"
                    ),
                    timestamp=now(),
                )

                messages.success(request, "Rating Based PD Term added successfully!")
                return redirect('rating_pd_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error adding Rating Based PD Term: {e}")
    else:
        form = LGDTermStructureDtlRatingForm()
    
    return render(request, 'lgd_conf/rating_pd_form.html', {'form': form})

# Edit Rating Based PD Term Detail
@login_required
@permission_required('IFRS9.change_FSI_LGD_Term_Structure', raise_exception=True)
def rating_pd_edit(request, term_id):
    pd_term_detail = get_object_or_404(FSI_LGD_Term_Structure, pk=term_id)
    if request.method == 'POST':
        form = LGDTermStructureDtlRatingForm(request.POST, instance=pd_term_detail)
        if form.is_valid():
            try:
                # Save the form without committing to the database yet
                rating = form.save(commit=False)
                # Set the created_by field to the currently logged-in user
                rating.created_by = request.user
                # Save the object to the database
                rating.save()

                AuditTrail.objects.create(
                    user=request.user,
                    model_name='Ldn_PD_Term_Structure_Dtl',
                    action='update',
                    object_id=rating.pk,
                    change_description=(
                        f"Updated Rating Based PD Term: Structure ID - {rating.v_pd_term_structure_id}, "
                        f"Date - {rating.fic_mis_date}, Risk Basis - {rating.v_credit_risk_basis_cd}, "
                        f"PD Percent - {rating.n_pd_percent}"
                    ),
                    timestamp=now(),
                )

                
                messages.success(request, "Rating Based PD Term updated successfully!")
                return redirect('rating_pd_list')
            except Exception as e:
                # Capture and display the specific exception message
                messages.error(request, f"Error updating Rating Based PD Term: {e}")
        
    else:
        form = LGDTermStructureDtlRatingForm(instance=pd_term_detail)
    
    return render(request, 'lgd_conf/rating_pd_form.html', {'form': form})

# Delete Rating Based PD Term Detail
@login_required
@permission_required('IFRS9.delete_FSI_LGD_Term_Structure', raise_exception=True)
def rating_pd_delete(request, term_id):
    pd_term_detail = get_object_or_404(FSI_LGD_Term_Structure, pk=term_id)
    if request.method == 'POST':
         # Log the deletion in the AuditTrail
        AuditTrail.objects.create(
            user=request.user,
            model_name='Ldn_PD_Term_Structure_Dtl',
            action='delete',
            object_id=pd_term_detail.pk,
            change_description=(
                f"Deleted Rating Based PD Term: Structure ID - {pd_term_detail.v_pd_term_structure_id}, "
                f"Date - {pd_term_detail.fic_mis_date}, Risk Basis - {pd_term_detail.v_credit_risk_basis_cd}, "
                f"PD Percent - {pd_term_detail.n_pd_percent}"
            ),
            timestamp=now(),
        )
        pd_term_detail.delete()
        messages.success(request, "Rating Based PD Term deleted successfully!")
        return redirect('rating_pd_list')
    return render(request, 'lgd_conf/rating_pd_confirm_delete.html', {'pd_term_detail': pd_term_detail})

