from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import Product, Contact, Order, OrderUpdate
from math import ceil
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import localtime
from paytmchecksum import PaytmChecksum
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import re
from django.contrib.auth.decorators import login_required


MERCHANT_KEY = 'bKMfNxPPf_QdZppa'

# Create main views here.
def index(request):
    # Initializes an empty list that will eventually hold products grouped by category along with slide information (for carousel display).
    allProds = []

    # This retrieves a queryset of dictionaries containing only the 'category' and 'id' fields of all Product objects in the database.
    catprod = Product.objects.values('category', 'id', 'price')

    # This uses set comprehension to extract all unique categories from catprod
    cats = {item['category'] for item in catprod}
    for cat in cats:
        # Retrieves all products that belong to the current category (cat)
        prod = Product.objects.filter(category=cat)
        n = len(prod)
        nSlides = n//4 + ceil((n/4) - (n//4)) # Calculates the number of slides needed for the current category
        allProds.append([prod, range(1, nSlides), nSlides])

    param = {'allProds': allProds}
    return render(request, "shop/index.html", param)

def searchMatch(query, item):
    '''return true only if query matches the item'''
    query = query.lower()
    return (
        query in item.product_name.lower() or
        query in item.category.lower()
    )

def search(request):
    query= request.GET.get('search')
    allProds = []
    catprods = Product.objects.values('category', 'id')
    cats = {item['category'] for item in catprods}
    for cat in cats:
        prodtemp = Product.objects.filter(category=cat)
        prod=[item for item in prodtemp if searchMatch(query, item)]
        n = len(prod)
        nLetter = n // 4 + ceil((n / 4) - (n // 4))
        if len(prod)!= 0:
            allProds.append([prod, range(1, nLetter), nLetter])
    params = {'allProds': allProds, "msg":""}
    if len(allProds)==0 or len(query)<2:
        params={'msg':"Please make sure to enter relevant search query"}
    return render(request, 'shop/search.html', params)


def about(request):
    return render(request, 'shop/about.html')


def contact(request):
    if request.method=="POST":
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        desc = request.POST.get('desc', '')
        contact = Contact(name = name, email = email, phone = phone, desc = desc)
        contact.save()
        return redirect("shop/contact.html?success=True")
    return render(request, "shop/contact.html")


def tracker(request):
    if request.method == 'POST':
        orderId = request.POST.get('orderId', '')
        email = request.POST.get('email', '')

        try:
            order = Order.objects.filter(order_id = orderId, email = email)
            if order.exists():
                updates = []
                updates_objs = OrderUpdate.objects.filter(order_id=orderId)

                for item in updates_objs:
                    local_time = localtime(item.timestamp) # Converts UTC to your local timezone
                    # Append each update's description and formatted time to the updates list
                    updates.append({
                        'text': item.update_desc,
                        'time': local_time.strftime(" %Y, %b %d, %a %I:%M:%S %p")
                    })

                # Load the cart data from items_json-
                cart = json.loads(order[0].item_json)

                # Inject product price into each item-
                for key in cart:
                    product = cart[key]
                    try:
                        product_obj = Product.objects.get(id=key)
                        product['price'] = product_obj.price
                        product['name'] = product_obj.product_name  # Optional: if missing
                    except Product.DoesNotExist:
                        product['price'] = 0
                        product['name'] = "Unknown"

                return JsonResponse({
                    "updates":updates,
                    "cart":cart
                })
            else:
                return JsonResponse({
                    "updates":[],
                    "cart":[]
                })
        except Exception as e:
            return HttpResponse(json.dumps([]), content_type="application/json")
    return render(request, "shop/tracker.html")


def productView(request, myid):
    # Fetch the product based on the provided id-
    product = Product.objects.filter(id=myid)
    return render(request, "shop/productview.html", {'prod': product[0]})

def buyNow(request):
    if request.method == "POST":
        data = json.loads(request.body)
        request.session['buynow'] = {
            'id': data.get('id'),
            'name': data.get('name'),
            'price': data.get('price'),
            'qty': int(data.get('qty')),
        }
        return JsonResponse({"status":'success'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def checkout(request):
    if request.method == 'GET':
        if 'buynow' in request.session:
            try:
                data = request.session.pop('buynow')  # remove after fetching
                product = Product.objects.get(id=data['id'])
                allProd = [{
                    "quantity": data['qty'],
                    "product": product
                }]
                return render(request, "shop/checkout.html", {'prod': allProd, 'is_buynow':True})
            except Product.DoesNotExist:
                return HttpResponse("Product not found", status=404)
            
        product_id = request.GET.get("prodId")
        quantity = request.GET.get("qty", 1)

        # if product_id:
        #     try:
        #         product = Product.objects.get(pk = product_id)
        #         allProd = [{"quantity":quantity, "product":product}]
        #         return render(request, "shop/checkout.html", {'prod':allProd})
            
        #     except Product.DoesNotExist:
        #         return HttpResponse("Product not found", status=404)
   
        cart_data = request.session.get("Checkout_cart", {})
        try:
            cart_dict = json.loads(cart_data) if isinstance(cart_data, str) else cart_data
        except:
            cart_dict = {}

        cart_items = []
        for product_id, product_info in cart_dict.items():
            try:
                product = Product.objects.get(id=product_id)
                cart_items.append({
                    'product':product,
                    'quantity':product_info['qty'],
                })
            except:
                continue
        return render(request, 'shop/checkout.html', {"prod": cart_items})  # <-- use 'prod' in your template

    if request.method == "POST":
        item_json = request.POST.get('itemsJson', '')
        amount =request.POST.get('amount', '')
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address1', '') + " , " + request.POST.get('address2', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        
        order = Order(item_json = item_json, amount = amount, name = name, email = email, phone = phone, address = address, city = city, state = state, zip_code = zip_code)
        order.save()

        update = OrderUpdate(order_id = order.order_id, update_desc = "The order has been placed")
        update.save()

        thank = True
        id = order.order_id

        # Request paytm to transfer the money to account after payment by user-
        param_dict={
            'MID': 'DIY12386817555501617',
            'ORDER_ID': 'order.order_id',
            'TXN_AMOUNT': str(amount),
            'CUST_ID': 'email',
            'INDUSTRY_TYPE_ID': 'Retail',
            'WEBSITE': 'WEBSTAGING', # Use for testing purpse
            'CHANNEL_ID': 'WEB',
            'CALLBACK_URL':'http://127.0.0.1:8000/shop/handlerequest/',
        }
        param_dict['CHECKSUMHASH'] = PaytmChecksum.generateSignature(param_dict, MERCHANT_KEY)
        return render(request, 'shop/paytm.html', {'param_dict':param_dict})

@csrf_exempt
def cart(request):
    if request.method == 'POST':
        try:
            # Read JSON body
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            cart_data = body_data.get('cart_data', '{}')  # cart_data is a string (JSON format)

            cart_dict = json.loads(cart_data)  # Now convert that string to dict
            request.session['Checkout_cart'] = cart_dict  # Save to session

            return JsonResponse({'status': 'success'})  # let frontend know it's stored
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=400)

    elif request.method == 'GET':
        cart_dict = request.session.get('Checkout_cart', {})
        cart_items = []

        for product_id, product_info in cart_dict.items():
            try:
                if not isinstance(product_info, dict) or 'qty' not in product_info:
                    continue
                product = Product.objects.get(pk=product_id)
                cart_items.append({
                    'product': product,
                    'quantity': product_info['qty'],
                })
            except (Product.DoesNotExist, ValueError, TypeError) as e:
                continue
        return render(request, "shop/cart.html", {'prod': cart_items})
    return JsonResponse({'status': 'invalid_method'}, status=405)

@csrf_exempt
def clear_cart(request):
    if request.method == 'POST':
        try:
            # Optional: read cart_data if sent
            cart_data = request.POST.get('cart_data', '()')
            print("Client sent cleared cart:", cart_data)

            # Clear cart in session-
            request.session['Checkout_cart'] = {}
            request.session.modified = True  # Ensure session is saved
            return JsonResponse({'status':"Success"})
        except Exception as e:
            return JsonResponse({'status':'error', 'message': str(e)}, status = 400)
    return JsonResponse({'status':'Invalid Requst'}, status = 405)

@csrf_exempt
def handlerequest(request):
    if request.method == 'POST':
        form = request.POST
        response_dict = {}
        for i in form.keys():
            response_dict[i] =form[i]
        checksum = form.get('CHECKSUMHASH')

        # Verify checksum
        verify = PaytmChecksum.verify_checksum(response_dict, MERCHANT_KEY, checksum)

        if verify:
            if response_dict.get('STATUS') == 'TXN_SUCCESS':
                print("Order Successful")
            else:
                print('Order Was not successful' + response_dict.get('RESMSG', 'No Message'))
        else:
            print("Chesksum Mismatch")
        return render(request, 'shop/paymentstatus.html', {'response':response_dict})
    else:
        return render(request, 'shop/paymentstatus.html', {'response':{'error' : 'Invalid Request'}})
    

def footer(request):
    return render(request, "shop/footer.html")

# Authenticate APIs-
def signupPage(request):
    return render(request, 'shop/signup.html')

# Cheack is password contains letter, digit and special character-
def validate_check(pass1):
    has_letter = re.search(r'[a-zA-Z]', pass1)
    has_digit = re.search(r"\d", pass1)
    has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', pass1)

    return all([has_letter, has_digit, has_special])

def handleSignup(request):
    if request.method == 'POST':
        # Get the post parameter:
        username = request.POST['username']
        fname = request.POST['fname']
        lname = request.POST['lname']
        email = request.POST['email']
        pass1 = request.POST['pass1']
        pass2 = request.POST['pass2']
        terms_accepted = request.POST.get('terms')

        # Check for duplicate fileds-
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists, please try another username")
            return redirect("/")

        # # Check for errorneous input:
        if len(username) < 10:
            messages.error(request, "Username must be at least 10 characters with letters and numbers")
            return redirect("/")
        if not username.isalnum():
            messages.error(request, "Username should only contain letters and numbers")
            return redirect("/")
        if len(pass1) < 8 and len(pass2) < 8 :
            messages.error(request, "Password must be contain atleast 8 character")
            return redirect("/")
        if pass1 != pass2:
            messages.error(request, "Passwords do not match")
            return redirect("/")
        if not validate_check(pass1):
            messages.error(request, "Passwords should be contain letters and numbers and special characters")
            return redirect("/")
        
        # Check if checkbox is checked
        if not terms_accepted:
            messages.warning(request, "You must accept the terms & conditions to register.")
            return redirect('signupPage')
            
        # Create the user-
        myuser = User.objects.create_user(username = username, email = email, password = pass1)
        myuser.first_name = fname
        myuser.last_name = lname
        myuser.save()
        messages.success(request, "Your SuperBazer account has been created successfully")
        return redirect("/") 
    else:
        return redirect('signupPage')

def loginPage(request):
    return render(request, 'shop/login.html')

def handleLogin(request):
    if request.method == "POST":
        loginusername = request.POST['username']
        loginpassword = request.POST['password']

        user = authenticate(username = loginusername, password = loginpassword)
        if user is not None:
            login(request, user)
            messages.success(request, "Successfully Login")
            return redirect("/")
        else:
            messages.error(request, "Invalid Credentials, Please try again")
            return redirect("/")

    return redirect('loginPage')

def handleLogout(request):
    logout(request)
    messages.success(request, "Successfully logged out")
    return redirect("/")