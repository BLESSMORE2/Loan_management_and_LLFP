from django.shortcuts import render,redirect
import matplotlib.pyplot as plt
import io
import  base64
from .models import *
from .forms import *

from .Functions.data import *





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



