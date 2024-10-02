from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from ..models import Ldn_LGD_Term_Structure,CollateralLGD
from ..forms import LGDTermStructureForm,CollateralLGDForm

def lgd_configuration(request):
    return render(request, 'lgd_conf/lgd_configuration.html')



# List all LGD Term Structures
def lgd_term_structure_list(request):
    term_structures = Ldn_LGD_Term_Structure.objects.all()
    return render(request, 'lgd_conf/lgd_term_structure_list.html', {'term_structures': term_structures})

# Create a new LGD Term Structure
def lgd_term_structure_create(request):
    if request.method == 'POST':
        form = LGDTermStructureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "LGD Term Structure added successfully!")
            return redirect('lgd_term_structure_list')
        else:
            messages.error(request, "Error adding LGD Term Structure.")
    else:
        form = LGDTermStructureForm()
    
    return render(request, 'lgd_conf/lgd_term_structure_form.html', {'form': form})

# Edit LGD Term Structure
def lgd_term_structure_edit(request, term_id):
    term_structure = get_object_or_404(Ldn_LGD_Term_Structure, pk=term_id)
    if request.method == 'POST':
        form = LGDTermStructureForm(request.POST, instance=term_structure)
        if form.is_valid():
            form.save()
            messages.success(request, "LGD Term Structure updated successfully!")
            return redirect('lgd_term_structure_list')
        else:
            messages.error(request, "Error updating LGD Term Structure.")
    else:
        form = LGDTermStructureForm(instance=term_structure)
    
    return render(request, 'lgd_conf/lgd_term_structure_form.html', {'form': form})

# Delete LGD Term Structure
def lgd_term_structure_delete(request, term_id):
    term_structure = get_object_or_404(Ldn_LGD_Term_Structure, pk=term_id)
    if request.method == 'POST':
        term_structure.delete()
        messages.success(request, "LGD Term Structure deleted successfully!")
        return redirect('lgd_term_structure_list')
    return render(request, 'lgd_conf/lgd_term_structure_confirm_delete.html', {'term_structure': term_structure})


def view_lgd_calculation(request):
    # Ensure only one record exists, get the first or the only one
    lgd_instance = get_object_or_404(CollateralLGD)

    # Pass the instance to the template
    return render(request, 'lgd_conf/view_lgd_calculation.html', {'lgd_instance': lgd_instance})

def edit_lgd_calculation(request):
    """Edit the LGD Calculation settings"""
    lgd_instance = get_object_or_404(CollateralLGD)

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