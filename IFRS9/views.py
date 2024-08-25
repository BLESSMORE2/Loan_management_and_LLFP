from django.shortcuts import render,redirect
import matplotlib.pyplot as plt
import io
import urllib, base64
from .models import *
from .forms import *
import pandas as pd
from django.views import View
from django.contrib import messages
from threading import Thread
from queue import Queue
from django.db import transaction, IntegrityError, DatabaseError
from django.core.exceptions import ValidationError
from django.db import connection
from django.apps import apps
from django.forms import modelform_factory
from django.forms import modelformset_factory




def dashboard_view(request):
    # Example data for financial graphs
    categories = ['January', 'February', 'March', 'April', 'May']
    values = [2000, 3000, 4000, 5000, 6000]

    # Create a bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(categories, values, color='skyblue')
    plt.xlabel('Month')
    plt.ylabel('Amount')
    plt.title('Monthly Financial Overview')

    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Encode the image in base64
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return render(request, 'dashboard.html', {'graph': image_base64})



def data_management(request):
    return render(request, 'load_data/data_management.html')
class FileUploadView(View):
    template_name = 'load_data/file_upload_step1.html'

    def get(self, request):
        form = UploadFileForm()

        # Fetch staging tables from the database
        stg_tables = TableMetadata.objects.filter(table_type='STG').values_list('table_name', flat=True)

        return render(request, self.template_name, {
            'form': form,
            'stg_tables': stg_tables  # Pass the staging tables to the template
        })

    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        selected_table = request.POST.get('table_name')  # Get selected table from the form

        if form.is_valid() and selected_table:
            file = form.cleaned_data['file']

            try:
                # Automatically detect file type and process accordingly
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(file)
                else:
                    messages.error(request, "Unsupported file format. Please upload a CSV or Excel file.")
                    return render(request, self.template_name, {'form': form, 'stg_tables': TableMetadata.objects.filter(table_type='STG')})

                # Store the data, column names, and selected table in session for later steps
                request.session['file_data'] = df.to_dict()  # Save the full data in session
                request.session['columns'] = list(df.columns)
                request.session['selected_table'] = selected_table  # Save the selected table

                # Prepare preview for rendering (first 10 rows)
                preview_data = {
                    'headers': list(df.columns),
                    'rows': df.head(10).values.tolist()  # Show the first 10 rows for preview
                }

                return render(request, self.template_name, {
                    'form': form,
                    'preview_data': preview_data,
                    'show_next_button': True,
                    'table_name': selected_table,
                    'file_name': file.name,
                    'stg_tables': TableMetadata.objects.filter(table_type='STG')
                })
            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
        return render(request, self.template_name, {
            'form': form,
            'stg_tables': TableMetadata.objects.filter(table_type='STG')
        })
    
class ColumnSelectionView(View):
    template_name = 'load_data/file_upload_step2.html'

    def get(self, request):
        columns = request.session.get('columns', [])
        if not columns:
            messages.error(request, "No columns found. Please upload a file first.")
            return redirect('file_upload')
        form = ColumnSelectionForm(columns=columns, initial={'selected_columns': columns})
        return render(request, self.template_name, {'form': form, 'columns': columns})

    def post(self, request):
        selected_columns = request.POST.get('selected_columns_hidden').split(',')
        if selected_columns:
            request.session['selected_columns'] = selected_columns
            return redirect('map_columns')
        else:
            messages.error(request, "You must select at least one column.")
        return render(request, self.template_name, {'form': form})

########################
class ColumnMappingView(View):
    template_name = 'load_data/file_upload_step3.html'

    def get(self, request):
        selected_columns = request.session.get('selected_columns', [])
        selected_table = request.session.get('selected_table')  # Get the selected table from the session

        # Get the model class dynamically based on the selected table
        try:
            model_class = apps.get_model('IFRS9', selected_table)  # Replace 'IFRS9' with your actual app name
        except LookupError:
            messages.error(request, "Error: The selected table does not exist.")
            return render(request, self.template_name)

        model_fields = [f.name for f in model_class._meta.fields]

        # Create initial mappings based on matching names (case-insensitive)
        initial_mappings = {}
        unmapped_columns = []

        for column in selected_columns:
            match = next((field for field in model_fields if field.lower() == column.lower()), None)
            if match:
                initial_mappings[column] = match
            else:
                initial_mappings[column] = 'unmapped'  # Set to 'unmapped' if no match is found
                unmapped_columns.append(column)  # Track unmapped columns

        # Initialize the form with the mappings
        form = ColumnMappingForm(
            initial={'column_mappings': initial_mappings}, 
            selected_columns=selected_columns, 
            model_fields=model_fields
        )

        # Debug output
        print('Initial mappings:', initial_mappings)
        print('Unmapped columns:', unmapped_columns)

        # Check if there are unmapped columns
        if unmapped_columns:
            messages.warning(request, "The following columns were not automatically mapped: " + ", ".join(unmapped_columns))
        
        return render(request, self.template_name, {'form': form, 'unmapped_columns': unmapped_columns})

    def post(self, request):
        selected_columns = request.session.get('selected_columns', [])
        selected_table = request.session.get('selected_table')  # Get the selected table from the session

        # Get the model class dynamically based on the selected table
        try:
            model_class = apps.get_model('IFRS9', selected_table)  # Replace 'IFRS9' with your actual app name
        except LookupError:
            messages.error(request, "Error: The selected table does not exist.")
            return render(request, self.template_name)

        model_fields = [f.name for f in model_class._meta.fields]

        # Initialize the form with POST data
        form = ColumnMappingForm(request.POST, selected_columns=selected_columns, model_fields=model_fields)

        if form.is_valid():
            # Safely get the 'column_mappings' from cleaned_data
            mappings = form.cleaned_data.get('column_mappings', {})

            # Debug output to check the mappings
            print("Column Mappings:", mappings)

            # Validate that all columns have been mapped (i.e., not mapped to 'unmapped')
            unmapped_columns = [col for col, mapped_to in mappings.items() if mapped_to == 'unmapped']
            if unmapped_columns:
                messages.error(request, "The following columns are not mapped: " + ", ".join(unmapped_columns))
                return render(request, self.template_name, {'form': form, 'unmapped_columns': unmapped_columns})

            # Ensure that there are mappings before proceeding
            if not mappings or all(value == 'unmapped' for value in mappings.values()):
                messages.error(request, "Error: No valid column mappings provided. Please map all columns before proceeding.")
                return render(request, self.template_name, {'form': form, 'unmapped_columns': unmapped_columns})

            # Save the mappings to the session
            request.session['column_mappings'] = mappings

            return redirect('submit_to_database')

        # If the form is not valid, render the form again with errors
        messages.error(request, "Error: Invalid form submission. Please check your mappings and try again.")
        return render(request, self.template_name, {'form': form})


#####################


class SubmitToDatabaseView(View):
    template_name = 'load_data/file_upload_step4.html'

    def get(self, request):
        try:
            # Retrieve data from the session
            df_data = request.session.get('file_data')
            selected_columns = request.session.get('selected_columns')
            mappings = request.session.get('column_mappings')
            selected_table = request.session.get('selected_table')  # Get the selected table from the session

            # Check for missing data
            if not df_data:
                messages.error(request, "Error: No data found in the uploaded file.")
                return render(request, self.template_name)

            # Convert the session data back into a DataFrame
            df = pd.DataFrame(df_data)

            # Check if the DataFrame is empty
            if df.empty:
                messages.error(request, "Error: The uploaded file contains no data.")
                return render(request, self.template_name)

            # Check for missing columns
            if not selected_columns:
                messages.error(request, "Error: No columns selected for upload.")
                return render(request, self.template_name)

            # Check for missing mappings
            if not mappings:
                messages.error(request, "Error: No column mappings provided.")
                return render(request, self.template_name)

            # Filter the DataFrame to include only selected columns
            df = df[selected_columns]

            # Rename the DataFrame columns based on the mappings
            df.rename(columns=mappings, inplace=True)

            # Get the model class dynamically based on the selected table
            try:
                model_class = apps.get_model('IFRS9', selected_table)
            except LookupError:
                messages.error(request, "Error: The selected table does not exist.")
                return render(request, self.template_name)

            # Split the DataFrame into chunks
            chunk_size = 100  # Customize chunk size as needed
            df_chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]

            # Create a queue to handle results
            result_queue = Queue()

            # Function to insert data into the database (to be run in threads)
            def insert_data_chunk(data_chunk, result_queue):
                for _, row in data_chunk.iterrows():
                    try:
                        model_class.objects.create(**row.to_dict())
                    except IntegrityError as e:
                        result_queue.put(f"Integrity Error: {e}")
                        return
                    except ValidationError as e:
                        if hasattr(e, 'error_dict'):
                            error_messages = "; ".join(f"{field}: {', '.join(errors)}" for field, errors in e.error_dict.items())
                        else:
                            error_messages = ", ".join(e.messages)
                        result_queue.put(f"Validation Error: {error_messages}")
                        return
                    except Exception as e:
                        result_queue.put(f"Error: {str(e)}")
                        return
                result_queue.put("Success")

            # Create and start threads for each chunk
            threads = []
            for chunk in df_chunks:
                thread = Thread(target=insert_data_chunk, args=(chunk, result_queue))
                thread.start()
                threads.append(thread)

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Collect results
            errors = []
            while not result_queue.empty():
                result = result_queue.get()
                if result != "Success":
                    errors.append(result)

            # Handle results
            if errors:
                messages.error(request, " ".join(errors))
            else:
                messages.success(request, "Data successfully uploaded to the database!")

        except Exception as e:
            # Catch any unexpected exceptions
            messages.error(request, f"Unexpected Error: {str(e)}")

        return render(request, self.template_name)
    
    ####################################################################
def data_entry_view(request):
    table_form = TableSelectForm(request.POST or None)
    data_form = None

    if request.method == 'POST':
        if table_form.is_valid():
            selected_table = table_form.cleaned_data['table_name'].table_name  # Get the selected table's name

            try:
                # Get the model class dynamically
                model_class = apps.get_model('IFRS9', selected_table)  # Replace 'IFRS9' with your actual app name
            except LookupError:
                messages.error(request, "Error: The selected table does not exist.")
                return render(request, 'load_data/data_entry.html', {'table_form': table_form, 'data_form': data_form})

            # Dynamically create a form for the selected model
            DynamicForm = modelform_factory(model_class, fields='__all__')
            data_form = DynamicForm(request.POST or None)

            if data_form.is_valid():
                try:
                    data_form.save()
                    messages.success(request, "Data successfully saved!")
                    return redirect('data_entry')
                except IntegrityError as e:
                    messages.error(request, f"Database Error: {e}")
                except ValidationError as e:
                    messages.error(request, f"Validation Error: {e.message_dict}")
                except Exception as e:
                    messages.error(request, f"Unexpected Error: {e}")
    
    return render(request, 'load_data/data_entry.html', {
        'table_form': table_form,
        'data_form': data_form
    })