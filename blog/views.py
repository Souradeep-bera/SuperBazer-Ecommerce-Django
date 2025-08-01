from django.shortcuts import render
from django.http import HttpResponse
from .models import Blogpost

# Create your views here.
def index(request):
    myposts = Blogpost.objects.all()
    print("Mypost Index: ",myposts, '\n')
    return render(request, "blog/index.html", {"myposts":myposts})

def blogpost(request, id):
    post = Blogpost.objects.filter(post_id = id)[0]
    print("Post: ", post, '\n')
    return render(request, 'blog/blogpost.html', {'post': post})