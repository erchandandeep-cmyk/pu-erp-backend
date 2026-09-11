from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Document

@login_required
def document_list(request):
    docs = Document.objects.filter(owner=request.user)
    return render(request, "documents/list.html", {"documents": docs})
