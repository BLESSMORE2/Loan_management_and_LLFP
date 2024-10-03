from django.shortcuts import render, get_object_or_404, redirect
from ..models import ECLMethod
from ..forms import ECLMethodForm
from django.contrib import messages
from django.core.exceptions import ValidationError


def ifrs9_configuration(request):
    # Render the IFRS9 Configuration template
    return render(request, 'ifrs9_conf/ifrs9_configuration.html')

def ecl_methodology_options(request):
    # This view shows the two options: Documentation and Choose Methodology
    return render(request, 'ifrs9_conf/ecl_methodology_options.html')

def ecl_methodology_documentation(request):
    # View to show the ECL methodology documentation
    return render(request, 'ifrs9_conf/ecl_methodology_documentation.html') 
 # You would create a separate documentation page
def ecl_methodology_list(request):
    methods = ECLMethod.objects.all()
    return render(request, 'ifrs9_conf/ecl_methodology_list.html', {'methods': methods})


def add_ecl_method(request):
    if request.method == 'POST':
        form = ECLMethodForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "New ECL Methodology added successfully!")
                return redirect('ecl_methodology_list')
            except ValidationError as e:
                form.add_error(None, e.message)  # This adds the validation error to the form's non-field errors
        else:
            messages.error(request, "There was an error adding the ECL Methodology.")
    else:
        form = ECLMethodForm()

    return render(request, 'ifrs9_conf/add_ecl_method.html', {'form': form})


def edit_ecl_method(request, method_id):
    method = get_object_or_404(ECLMethod, pk=method_id)
    if request.method == 'POST':
        form = ECLMethodForm(request.POST, instance=method)
        if form.is_valid():
            form.save()
            messages.success(request, "ECL methodology updated successfully!")
            return redirect('ecl_methodology_list')
        else:
            messages.error(request, "There was an error updating the ECL methodology.")
    else:
        form = ECLMethodForm(instance=method)
    
    return render(request, 'ifrs9_conf/edit_ecl_method.html', {'form': form})

def delete_ecl_method(request, method_id):
    method = get_object_or_404(ECLMethod, pk=method_id)
    
    if request.method == 'POST':
        method.delete()
        messages.success(request, "ECL Methodology deleted successfully!")
        return redirect('ifrs9_conf/ecl_methodology_list')

    return render(request, 'ifrs9_conf/delete_ecl_method.html', {'method': method})


def choose_ecl_methodology(request):
    # View to configure the ECL methodology
    return render(request, 'ifrs9_conf/choose_ecl_methodology.html')  