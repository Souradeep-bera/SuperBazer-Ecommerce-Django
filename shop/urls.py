from . import views
from django.urls import path

urlpatterns = [
    path('', views.index, name="ShopHome"),
    path('about/', views.about, name="AboutUs"),
    path('contact/', views.contact, name="ContactUs"),
    path('tracker/', views.tracker, name="Trackingstatus"),
    path('search/', views.search, name="Search"),
    path('products/<int:myid>', views.productView, name="Productview"),
    path("buynow/", views.buyNow, name="buyNow"),
    path('checkout/', views.checkout, name="Checkout"),
    path('cart/', views.cart, name="cart"),
    path('shop/cart/', views.clear_cart, name='clear_cart'),
    path('shop/handlerequest/', views.handlerequest, name='HandleRequest'),
    path('footer/', views.footer, name='Footer'),
    path('signup/', views.handleSignup, name="handleSignup"),
    path('signupPage/', views.signupPage, name='signupPage'),
    path('login/', views.handleLogin, name="handleLogin"),
    path('loginPage/', views.loginPage, name="loginPage"),
    path('logout/', views.handleLogout, name="handleLogout"),
]
