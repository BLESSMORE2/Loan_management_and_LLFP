from django.shortcuts import render, redirect, get_object_or_404
from ..models import SupportDocuments
from django.contrib.auth.decorators import login_required, permission_required

# Upload Document
@permission_required('IFRS9.can_upload_document', raise_exception=True)
def upload_document(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            SupportDocuments.objects.create(
                file_name=uploaded_file.name,
                uploaded_file=uploaded_file
            )
        return redirect('view_documents')  # Redirect to the view documents page
    return render(request, 'support/upload_document.html')


# View Uploaded Documents
def view_documents(request):
    files = SupportDocuments.objects.all()
    return render(request, 'support/view_documents.html', {'files': files})


# Delete Document
@permission_required('IFRS9.can_delete_document', raise_exception=True)
def delete_document(request, document_id):
    document = get_object_or_404(SupportDocuments, id=document_id)
    document.delete()
    return redirect('view_documents')  # Redirect back to the documents list