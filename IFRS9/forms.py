from django import forms
from .models import *

class UploadFileForm(forms.Form):
    file = forms.FileField(label='Select a file', widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

class ColumnSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        columns = kwargs.pop('columns', [])
        super(ColumnSelectionForm, self).__init__(*args, **kwargs)
        
        # Dynamically generate a MultipleChoiceField for selecting columns
        self.fields['selected_columns'] = forms.MultipleChoiceField(
            choices=[(col, col) for col in columns],
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            label='Select Columns to Include',
            initial=columns  # By default, select all columns
        )

class ColumnMappingForm(forms.Form):
    def __init__(self, *args, selected_columns=None, model_fields=None, **kwargs):
        super(ColumnMappingForm, self).__init__(*args, **kwargs)

        if selected_columns and model_fields:
            for column in selected_columns:
                self.fields[column] = forms.ChoiceField(
                    choices=[(field, field) for field in model_fields] + [('unmapped', 'Unmapped')],
                    required=False
                )
                # Set the initial value for each field if provided in kwargs['initial']
                if 'initial' in kwargs and 'column_mappings' in kwargs['initial']:
                    if column in kwargs['initial']['column_mappings']:
                        self.fields[column].initial = kwargs['initial']['column_mappings'][column]

                        
    def clean(self):
        cleaned_data = super().clean()
        column_mappings = {key.replace('column_mapping_', ''): value for key, value in cleaned_data.items()}
        return {'column_mappings': column_mappings}



##########################################################
class TableSelectForm(forms.Form):
    table_name = forms.ModelChoiceField(queryset=TableMetadata.objects.filter(table_type='STG'), label="Select Table")

# Form for Ldn_Financial_Instrument
