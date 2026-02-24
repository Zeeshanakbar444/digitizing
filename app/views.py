from django.shortcuts import render , redirect, get_object_or_404 , HttpResponse
from django.http import HttpResponse, Http404
from .models import *
from django.core.mail import EmailMessage
from django.contrib import messages
# from .models import Contact
from django.template.loader import render_to_string
from django.utils import timezone
from main import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.decorators import login_required
import stripe
# from paypal.standard.forms import PayPalPaymentsForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.core.paginator import Paginator
from decimal import Decimal , InvalidOperation
from django.db.models import Sum
from datetime import datetime
from django.db.models import Q
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter
# from reportlab.lib import colors
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
# from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from django.utils.timezone import now
from django.db import transaction
from datetime import timedelta

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



def home(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    user = request.user

    invoices = Invoice.objects.filter(user=user).order_by("-id")[:5]

    digitizing_orders = DigitizingOrder.objects.filter(user=user).order_by("-id")[:4]
    vector_orders = VectorOrder.objects.filter(user=user).order_by("-id")[:4]
    patches_orders = PatchesOrder.objects.filter(user=user).order_by("-id")[:4]

    digitizing_estimate = DigitizingEstimate.objects.filter(user=user).order_by("-id")[:4]
    vector_estimate = VectorEstimate.objects.filter(user=user).order_by("-id")[:4]
    patches_estimate = PatchesEstimates.objects.filter(user=user).order_by("-id")[:4]

    # Outstanding balance calculation
    

    return render(request, "app/index-dark.html", {
        "digitizing_orders": digitizing_orders,
        "vector_orders": vector_orders,
        "patches_orders": patches_orders,
        "invoices": invoices,
        # "outstanding_balance": outstanding_balance,
    })

@login_required(login_url='login')
def invoice_list(request):
    user = request.user
    invoices = Invoice.objects.filter(user=user).order_by("-id")

    # Calculate totals directly from invoice fields
    total_amount = sum(invoice.total for invoice in invoices)
    paid_amount = sum(invoice.total for invoice in invoices if invoice.payment_status == 'PAID')
    unpaid_amount = total_amount - paid_amount

    # Pagination
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "app/invoice-list.html", {
        "page_obj": page_obj,
        "invoices": page_obj.object_list,
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "unpaid_amount": unpaid_amount,
    })

@login_required(login_url='login')
def invoice_preview(request):
    return render(request  ,"app/invoice_preview.html")

# from django.shortcuts import render, redirect
# from .models import DigitizingOrder, VectorOrder, PatchesOrder

stripe.api_key = 'sk_test_51Q7iVsGf5VxN754qKKH3YPtx5IZTFZPrPs4FNXtfiz5vJFXBePYO7MfI5cUmAFBHriX7vFhKsu03JCbu4T7eC4Gg00BzIi7gEf'
@login_required(login_url='login')
def payment(request):
    type = request.GET['type']
    order_id = request.GET['order_id']
    if type == "Digitizing":
        selected_order = DigitizingOrder.objects.get(id=order_id)
    if type == "Vector Conversion":
        selected_order = VectorOrder.objects.get(id=order_id)
    if type == "Embroidery Patches":
        selected_order = PatchesOrder.objects.get(id=order_id)
    if request.method == "POST":
        paymentOption = request.POST['paymentOption']
        
        if paymentOption == "stripe":
            # print("okk")
            checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': selected_order.design_name,
                    },
                    'unit_amount': int(float(selected_order.total if selected_order.total else selected_order.amount) * 100),

                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'http://127.0.0.1:8888/payment-done/?session_id={{CHECKOUT_SESSION_ID}}&order_id={selected_order.id}&type={selected_order.order_type}',
            cancel_url='http://127.0.0.1:8888/payment_cancelled/',
        )
            return redirect(checkout_session.url, code=303)
        elif paymentOption == "paypal":
            # print("okkkkkkkkkkkkkk")
            host = request.get_host()
            paypal_dict = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': selected_order.total if selected_order.total else selected_order.amount,
                'item_name': selected_order.design_name,
                'invoice': 'INV-'+str(selected_order.id),
                'currency_code': 'USD',
                'notify_url': 'http://{}{}'.format(host, reverse('paypal-ipn')),
                'return_url': 'http://{}{}'.format(host, reverse('payment_done')),
                'cancel_return': 'http://{}{}'.format(host, reverse('payment_cancelled')),
                'no_shipping': 1,
                'paymentaction': 'sale',
                'SOLUTIONTYPE': 'Sole',  # Enables guest checkout
                'LANDINGPAGE': 'Billing',  # Directs to credit card entry page
            }
            form = PayPalPaymentsForm(initial=paypal_dict)
            context = {"form": form}
            return render(request, "app/paypal_redirect.html", context)
            # return redirect(form)

    return render(request  ,"app/payment.html", {"selected_order":selected_order})

# @login_required(login_url='login')
def payment_done(request):
    params = {}
    order_id = request.GET.get('order_id')
    invoice_id = request.GET.get('invoice_id')
    order_type = request.GET.get('type')

    if order_id and order_type:
        order = None
        if order_type == "Digitizing":
            DigitizingOrder.objects.filter(id=order_id).update(
                payment_status="Success Payment",
                order_status="Completed",
            )
            order = DigitizingOrder.objects.get(id=order_id)

        elif order_type == "Vector Conversion":
            VectorOrder.objects.filter(id=order_id).update(
                payment_status="Success Payment",
                order_status="Completed",
            )
            order = VectorOrder.objects.get(id=order_id)

        elif order_type == "Embroidery Patches":
            PatchesOrder.objects.filter(id=order_id).update(
                payment_status="Success Payment",
                order_status="Completed",
            )
            order = PatchesOrder.objects.get(id=order_id)

        if order:
            params['order'] = order

    elif invoice_id:
        # Assuming invoice_id is something like "INV-5"
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            invoice.payment_status = "Success Payment"
            invoice.save()
            params['invoice'] = invoice
        except Invoice.DoesNotExist:
            pass

    return render(request, 'app/payment-success.html', params)



@login_required
# @csrf_exempt
def payment_canceled(request):
	return render(request, 'app/payment-fail.html')



from django.core.paginator import Paginator

def orders(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    user = request.user
    digitizing_orders = DigitizingOrder.objects.filter(user=user)
    vector_orders = VectorOrder.objects.filter(user=user)
    patches_orders = PatchesOrder.objects.filter(user=user)

    # Combine all orders into a single list
    orders = []
    for order in digitizing_orders:
        orders.append({
            'type': 'Digitizing',
            'id': order.id,
            'order_id': order.order_id,
            'stitches': order.number_of_stitches,
            'payment_status': order.payment_status,
            'design_name': order.design_name,
            'amount': order.amount,
            'created_at': order.created_at,
            # 'stitched_image': order.stitched_image,
        })
    for order in vector_orders:
        orders.append({
            'type': 'Vector',
            'id': order.id,
            'order_id': order.order_id,
            'design_name': order.design_name,
            'payment_status': order.payment_status,
            'amount': order.amount,
            'created_at': order.created_at,
            # 'stitched_image': order.stitched_image,
        })
    for order in patches_orders:
        orders.append({
            'type': 'Patches',
            'id': order.id,
            'order_id': order.order_id,
            'design_name': order.design_name,
            'payment_status': order.payment_status,
            'amount': order.amount,
            'created_at': order.created_at,
            # 'stitched_image': order.stitched_image,
        })

    # Sort orders by created_at (newest first)
    orders.sort(key=lambda x: x['created_at'], reverse=True)

    # Apply pagination
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    return render(request, "app/orders.html", {'orders': orders_page})

@login_required(login_url='login')
def place_order(request):
    # try:
    #     get_pricing = Pricing.objects.get(user=request.user)
    # except:
    #     get_pricing = None
        # messages.error(request, "You must select a pricing plan before placing an order.")
        # return redirect("/pricing/")
    if request.method == 'POST':
        try:

            # if not get_pricing:
            #     messages.error(request, "You must select a pricing plan before placing an order.")
            #     return redirect("/pricing/")
            # Create a new DigitizingOrder instance
            order = DigitizingOrder(
                user=request.user,
                order_type='Digitizing',
                order_status='On Progress',
                payment_status='Pending Payment',
                # pricing_model_type=get_pricing.pricing_type,
                design_name=request.POST.get('design_name'),
                number_of_colors=request.POST.get('no_of_colors'),
                po_no=request.POST.get('po_no'),
                # name_of_colors=request.POST.get('name_of_colors'),
                height=request.POST.get('Height', ''),
                width=request.POST.get('Width', ''),
                unit=request.POST.get('unit'),
                type=request.POST.get('type'),
                placement=request.POST.get('placement'),  # Note: form has duplicate 'type' id, should be fixed
                required_blending=request.POST.get('blending', 'No'),
                # Sew_Out_Sample=request.POST.get('sew_out', ''),  # This field is missing from the form, add it if needed
                # Details='',  # This field is missing from the form, add it if needed
                design_format=request.POST.get('design_format'),
                addtitoanl_instructions=request.POST.get('add_inst', '')
            )
            
            # Handle file upload
            # if 'artwork' in request.FILES:
            #     order.artwork = request.FILES['artwork']

            # Save the order to the database
            order.save()
            artwork_files = request.FILES.getlist('artwork[]')
            for file in artwork_files:
                DigitizingOrderArtwork.objects.create(order=order, file=file)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
            }

            email_subject = f"Your Digitizing Order Received ({order.order_id}) {order.design_name} Logo"
            email_body = render_to_string("app/emails/order_placed_email.html", email_context)

            email_msg = EmailMessage(
                subject=email_subject,
                body=email_body,
                to=[request.user.email, 'info@highfivedigitizing.com']
            )
            email_msg.content_subtype = "html"

            # Attach artwork files to email
            for file in artwork_files:
                email_msg.attach(file.name, file.read(), file.content_type)

            email_msg.send()

            messages.success(request, 'Order placed successfully!')
            return redirect('/digitizing_order_list/')

        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')
            return render(request, 'app/place_order.html', {'form_data': request.POST})

    # For GET request, just render the form
    return render(request, 'app/place_order.html')
@login_required(login_url='login')
def order_preview(request, id):
    type = request.GET.get("type", "Digitizing")
    # try:
    if type == "Digitizing":
        get_order = DigitizingOrder.objects.get(id=id)
        
    elif type == "Vector Conversion" or type == "Vector":
        # print("id", id)
        get_order = VectorOrder.objects.get(id=id)

    elif type == "Embroidery Patches" or type == "Patches":
        get_order = PatchesOrder.objects.get(id=id)
    # except:
        # return redirect("/")
    return render(request, 'app/order_preview.html', {"get_order" : get_order})

@login_required(login_url='login')
def edit_preview(request, id):
    try:
        get_order = Edits.objects.get(id=id)
    except:
        return redirect("/")
    return render(request, 'app/edit_preview.html', {"get_order" : get_order})
@login_required(login_url='login')
def estimate_preview(request, id):
    type = request.GET.get("type", "Digitizing")
    try:
        if type == "Digitizing":
            get_order = DigitizingEstimate.objects.get(id=id)
            
        elif type == "Vector Conversion" or type == "Vector":
            get_order = VectorEstimate.objects.get(id=id)

        elif type == "Embroidery Patches" or type == "Patches":
            get_order = PatchesEstimates.objects.get(id=id)

        
            
    except:
        return redirect("/")
    return render(request, 'app/estimate_preview.html', {"get_order" : get_order})

@login_required(login_url='login')
def place_estimate(request):
    if request.method == 'POST':
        # try:
            # try:
            #     get_pricing = Pricing.objects.get(user=request.user)
            # except:
            #     get_pricing = None
            # Create a new DigitizingOrder instance
            order = DigitizingEstimate(
                user=request.user,
                order_type='Digitizing',
                order_status='On Progress',
                payment_status='Pending Payment',
                # pricing_model_type=get_pricing.pricing_type,
                design_name=request.POST.get('design_name'),
                number_of_colors=request.POST.get('no_of_colors'),
                po_no=request.POST.get('po_no'),
                # name_of_colors=request.POST.get('name_of_colors'),
                height=request.POST.get('Height', ''),
                width=request.POST.get('Width', ''),
                unit=request.POST.get('unit'),
                type=request.POST.get('type'),
                placement=request.POST.get('placement'),  # Note: form has duplicate 'type' id, should be fixed
                required_blending=request.POST.get('blending', 'No'),
                # Sew_Out_Sample=request.POST.get('sew_out', ''),  # This field is missing from the form, add it if needed
                # Details='',  # This field is missing from the form, add it if needed
                design_format=request.POST.get('design_format'),
                addtitoanl_instructions=request.POST.get('add_inst', '')
            )
            
            # Handle file upload
            # if 'artwork' in request.FILES:
            #     order.artwork = request.FILES['artwork']

            # Save the order to the database
            order.save()
            for file in request.FILES.getlist('artwork[]'):
                DigitizingEstimateArtwork.objects.create(estimate=order, file=file)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
                # "site_url":request.get_host()
            }

            email_subject = f"Your Digitizing Quote Received ({order.estimate_id}) {order.design_name} Logo"
            email_body = render_to_string("app/emails/quote_placed_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"
            for file in request.FILES.getlist('artwork[]'):
                email_msg.attach(file.name, file.read(), file.content_type)
            email_msg.send()
            
            messages.success(request, 'Quote placed successfully!')
            return redirect('/digitizing_quote_list/')  # You'll need to define this URL

        # except Exception as e:
        #     messages.error(request, f'Error placing estimate: {str(e)}')
        #     print(f'Error placing estimate: {str(e)}')
        #     return render(request, 'app/place_estimate.html', {'form_data': request.POST})
    return render(request  ,"app/place_estimate.html")
from django.core.paginator import Paginator

def estimates(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    user = request.user
    digitizing_orders = DigitizingEstimate.objects.filter(user=user)
    vector_orders = VectorEstimate.objects.filter(user=user)
    patches_orders = PatchesEstimates.objects.filter(user=user)

    # Combine all orders into a single list
    orders = []
    for order in digitizing_orders:
        orders.append({
            'type': 'Digitizing',
            'id': order.id,
            'estimate_id': order.estimate_id,
            'converted': order.converted_to_order,
            'stitches': order.number_of_stitches,
            'design_name': order.design_name,
            'amount': order.amount,
            'created_at': order.created_at,
            'stitched_image': order.stitched_image,
        })
    for order in vector_orders:
        orders.append({
            'type': 'Vector',
            'id': order.id,
            'estimate_id': order.estimate_id,
            'converted': order.converted_to_order,
            'design_name': order.design_name,
            'amount': order.amount,
            'created_at': order.created_at,
            'stitched_image': order.stitched_image,
        })
    for order in patches_orders:
        orders.append({
            'type': 'Patches',
            'id': order.id,
            'estimate_id': order.estimate_id,
            'converted': order.converted_to_order,
            'design_name': order.design_name,
            'amount': order.amount,
            'created_at': order.created_at,
            'stitched_image': order.stitched_image,
        })

    # Sort orders by created_at (newest first)
    orders.sort(key=lambda x: x['created_at'], reverse=True)

    # Apply pagination
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)

    return render(request, "app/estimates.html", {'orders': orders_page})

@login_required(login_url='login')
def edits(request):
    all_edits_list = Edits.objects.filter(user=request.user).order_by('-created_at')  # optional: latest first

    paginator = Paginator(all_edits_list, 10)  # 10 edits per page

    page_number = request.GET.get('page')
    all_edits = paginator.get_page(page_number)

    params = {
        "all_edits": all_edits
    }
    return render(request, "app/edits.html", params)
@login_required(login_url='login')
def place_edit(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    user = request.user
    digitizing_orders = DigitizingOrder.objects.filter(user=user)
    vector_orders = VectorOrder.objects.filter(user=user)
    patches_orders = PatchesOrder.objects.filter(user=user)
    

    # Combine all orders into a single list
    orders = []
    for order in digitizing_orders:
        orders.append(('digitizing', order.id, order.design_name))
    for order in vector_orders:
        orders.append(('vector', order.id, order.design_name))
    for order in patches_orders:
        orders.append(('patches', order.id, order.design_name))

    if request.method == 'POST':
        inst = request.POST.get('inst')  # Format: "order_type:order_id"
        artwork = request.FILES.get('artwork')
        design = request.POST.get('Design')

        # Create the ticket with all design fields initially empty
        ticket = Edits(
            user=user,
            order_status="In Process",
            edit_instructions=inst,
            artwork=artwork,
        )

        # Set the appropriate design field based on the order type
        if design:
            order_type, order_id = design.split(':')
            if order_type == 'digitizing':
                ticket.design_digitizing_id = order_id
            elif order_type == 'vector':
                ticket.design_vector_id = order_id
            elif order_type == 'patches':
                ticket.design_patches_id = order_id
            else:
                raise ValueError("Invalid order type")

        ticket.save()
        messages.success(request, "Your Edit has been made successfully")
        return redirect('/edits/')
    params = {
        'orders': orders,
    }
    return render(request  ,"app/place_edit.html", params)
@login_required(login_url='login')
def unpaid_invoices(request):
    return render(request  ,"app/unpaid_invoices.html")
@login_required(login_url='login')
def notifications(request):
    user_noti = Notification.objects.filter(user=request.user).order_by("-id")
    params = {
        "user_noti":user_noti
    }
    return render(request  ,"app/notifications.html", params)
@login_required(login_url='login')
def noti_preview(request, id):
    user_noti = Notification.objects.get(user=request.user, id=id)
    params = {
        "noti":user_noti
    }
    return render(request  ,"app/noti_preview.html", params)

@login_required(login_url='login')
def profile(request):
    user = request.user
    digitizing_orders = DigitizingOrder.objects.filter(user=user)
    vector_orders = VectorOrder.objects.filter(user=user)
    patches_orders = PatchesOrder.objects.filter(user=user)
    try:
        get_profile = Profile.objects.get(user=user)
    except:
        get_profile = None


    # Combine all orders into a single list
    orders = []
    pending_orders_count = 0  # <-- Initialize counter

    for order in digitizing_orders:
        orders.append({
            'type': 'Digitizing',
            'id': order.id,
            'order_id': order.order_id,
            'stitches': order.number_of_stitches,
            'payment_status': order.payment_status,
            'design_name': order.design_name,
            'amount': order.amount,
            'created_at': order.created_at,
            # 'stitched_image': order.stitched_image,
        })
        if order.order_status == 'On Progress':
            pending_orders_count += 1

    for order in vector_orders:
        orders.append({
            'type': 'Vector',
            'id': order.id,
            'order_id': order.order_id,
            'design_name': order.design_name,
            'payment_status': order.payment_status,
            'amount': order.amount,
            'created_at': order.created_at,
            # 'stitched_image': order.stitched_image,
        })
        if order.order_status == 'On Progress':
            pending_orders_count += 1

    for order in patches_orders:
        orders.append({
            'type': 'Patches',
            'id': order.id,
            'order_id': order.order_id,
            'design_name': order.design_name,
            'payment_status': order.payment_status,
            'amount': order.amount,
            'created_at': order.created_at,
            # 'stitched_image': order.stitched_image,
        })
        if order.order_status == 'On Progress':
            pending_orders_count += 1

    # Sort orders by created_at (newest first)
    orders.sort(key=lambda x: x['created_at'], reverse=True)

    try:
        get_pricing = Pricing.objects.get(user=request.user)
    except:
        get_pricing = None

    print("fdsfsdf" , get_pricing)

    params = {
        "orders": orders,
        "total_orders": len(orders),
        "total_pending_orders": pending_orders_count,  # <-- Added here
        "get_pricing": get_pricing,  # <-- Added here
        "get_profile": get_profile,  # <-- Added here
    }

    return render(request, "app/profile.html", params)

@login_required(login_url='login')
def update_profile(request):
    # Get the user's profile or create one if it doesn't exist
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Get data from the form
        full_name = request.POST.get('full_name')  # This is the field for the full name
        mobile_no = request.POST.get('mobile_no')
        country = request.POST.get('country')
        company = request.POST.get('company')
        business_phone_no = request.POST.get('business_phone_no')
        state = request.POST.get('state')
        website = request.POST.get('website')
        city = request.POST.get('city')
        address = request.POST.get('address')

        # Update the user's name if it's changed
        if full_name != request.user.first_name:
            request.user.first_name = full_name  # Update the user's username (full name)
            request.user.save()

        # Update or create the profile with the new data
        profile.mobile_no = mobile_no
        profile.country = country
        profile.company = company
        profile.business_phone_no = business_phone_no
        profile.state = state
        profile.website = website
        profile.address = address
        profile.city = city

        # Save the profile
        profile.save()

        # Redirect to the profile page or success page
        messages.success(request, "Your Profile has been Updated")
        return redirect('/profile/')  # Change this to your actual profile view

    return render(request, 'update_profile.html', {'profile': profile})


@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        errors = {}

        # Check if the current password is correct
        if not request.user.check_password(current_password):
            errors['current_password'] = 'The current password is incorrect.'

        # Check if the new password and confirm password match
        if new_password != confirm_password:
            errors['confirm_password'] = 'The new passwords do not match.'

        # If there are errors, return them as JSON response
        if errors:
            return JsonResponse({'status': 'error', 'errors': errors})

        # Update the password
        request.user.set_password(new_password)
        request.user.save()

        # Keep the user logged in after password change
        update_session_auth_hash(request, request.user)

        # Return a success message
        return JsonResponse({'status': 'success', 'message': 'Your password has been successfully updated.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

@login_required(login_url='login')
def select_pricing(request):
    if request.method == 'POST':
        pricing_type = request.POST.get('pricing_type')
        
        # Validate the pricing type
        if pricing_type not in dict(Pricing.PRICING_CHOICES).keys():
            messages.error(request, "Invalid pricing selection")
            return redirect('/select_pricing/')
        
        # Update or create the pricing model
        Pricing.objects.update_or_create(
            user=request.user,
            defaults={'pricing_type': pricing_type}
        )
        
        messages.success(request, f"Pricing model updated to {dict(Pricing.PRICING_CHOICES)[pricing_type]}")
        return redirect('/')  # Or wherever you want to redirect
    
    # Get current pricing for display
    try:
        user_pricing = Pricing.objects.get(user=request.user)
    except Pricing.DoesNotExist:
        user_pricing = None
    
    return render(request, 'app/pricing.html', {
        'user_pricing': user_pricing
    })

# def pricing(request):
#     return render(request  ,"app/pricing.html")
@login_required(login_url='login')
def user_logout(request):
    # Log the user out
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('/login/')

def login_view(request):
    if request.method == "POST":
        # print("okk")
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')

        # Try authenticating with username first
        user = authenticate(request, username=identifier, password=password)

        if user is None:
            # If not found, check if it's an email and get the username
            try:
                user_obj = User.objects.get(email=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect('/') 
        else:
            messages.error(request, "Invalid email/username or password.")
            return redirect("/login/")

    return render(request, "app/login.html")


def signup(request):
    if request.method == "POST":
        # Get form data
        # username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Profile data
        contact_name = request.POST.get('contact_name')
        company = request.POST.get('company')
        mobile_no = request.POST.get('mobile_no')
        business_phone_no = request.POST.get('business_phone_no', '')
        website = request.POST.get('website', '')
        invoice_email = request.POST.get('invoice_email')
        reference = request.POST.get('reference', '')
        country = request.POST.get('country')
        state = request.POST.get('state', '')
        city = request.POST.get('city', '')
        address = request.POST.get('address', '')
        postal_code = request.POST.get('postal_code', '')

        # Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
        # elif User.objects.filter(username=username).exists():
        #     messages.error(request, "This username is already taken.")
        else:
            try:
                # Create user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=contact_name
                )
                user.save()

                # Create profile
                profile = Profile.objects.create(
                    user=user,
                    mobile_no=mobile_no,
                    country=country,
                    company=company,
                    address=address,
                    postal_code=postal_code,
                    business_phone_no=business_phone_no,
                    city=city,
                    website=website,
                    invoice_email=invoice_email,
                    reference=reference,
                    state=state
                )
                profile.save()

                # Send welcome email
                user_fullname = user.first_name
                site_url = request.get_host()
                # print("request", request.get_host())

                email_context = {
                    "username": user_fullname,
                    "email": email,
                    "site_url": site_url,
                }

                email_subject = "Welcome to High Five Digitizing"
                email_body = render_to_string("app/emails/account_registered_email.html", email_context)

                email_msg = EmailMessage(email_subject, email_body, to=[email])
                email_msg.content_subtype = "html"
                email_msg.send()

                # Log in user
                user = authenticate(request, username=email, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, "Account created successfully. You are now logged in.")
                    return redirect('/')
                    
            except Exception as e:
                messages.error(request, f"An error occurred while creating your account: {str(e)}")
    
    return render(request, 'app/signup.html')

def open_ticket(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    user = request.user
    digitizing_orders = DigitizingOrder.objects.filter(user=user)
    vector_orders = VectorOrder.objects.filter(user=user)
    patches_orders = PatchesOrder.objects.filter(user=user)
    tickets = OpenTicket.objects.filter(user=request.user).order_by("-id")
    pending_tickets = OpenTicket.objects.filter(user=request.user , ticket_status="Pending").order_by("-id")
    answered_tickets = OpenTicket.objects.filter(user=request.user , ticket_status="Answered").order_by("-id")
    closed_tickets = OpenTicket.objects.filter(user=request.user , ticket_status="Closed").order_by("-id")
    

    # Combine all orders into a single list
    orders = []
    for order in digitizing_orders:
        orders.append(('digitizing', order.id, order.design_name))
    for order in vector_orders:
        orders.append(('vector', order.id, order.design_name))
    for order in patches_orders:
        orders.append(('patches', order.id, order.design_name))

    if request.method == 'POST':
        subject = request.POST.get('Subject')
        design = request.POST.get('Design')  # Format: "order_type:order_id"
        priority = request.POST.get('Priority')
        message = request.POST.get('Message')

        # Create the ticket with all design fields initially empty
        ticket = OpenTicket(
            user=user,
            subject=subject,
            priority=priority,
            message=message
        )

        # Set the appropriate design field based on the order type
        if design:
            order_type, order_id = design.split(':')
            if order_type == 'digitizing':
                ticket.design_digitizing_id = order_id
            elif order_type == 'vector':
                ticket.design_vector_id = order_id
            elif order_type == 'patches':
                ticket.design_patches_id = order_id
            else:
                raise ValueError("Invalid order type")

        ticket.save()
        messages.success(request, "Your ticket has been successfully created. We will process it promptly.")
        return redirect('/')
    params = {
        "tickets":tickets,
        "total_tickets":len(tickets),
        "total_pending_tickets":len(pending_tickets),
        "total_answered_tickets":len(answered_tickets),
        "total_closed_tickets":len(closed_tickets),
        'orders': orders,
    }
    return render(request, 'app/open-ticket.html', params)
from django.core.paginator import Paginator

def view_ticket(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    tickets = OpenTicket.objects.filter(user=request.user).order_by("-id")
    pending_tickets = OpenTicket.objects.filter(user=request.user, ticket_status="Pending").order_by("-id")
    answered_tickets = OpenTicket.objects.filter(user=request.user, ticket_status="Answered").order_by("-id")
    closed_tickets = OpenTicket.objects.filter(user=request.user, ticket_status="Closed").order_by("-id")

    # Apply pagination
    paginator = Paginator(tickets, 10)  # 10 tickets per page
    page_number = request.GET.get('page')
    tickets_page = paginator.get_page(page_number)

    params = {
        "tickets": tickets_page,
        "total_tickets": paginator.count,
        "total_pending_tickets": len(pending_tickets),
        "total_answered_tickets": len(answered_tickets),
        "total_closed_tickets": len(closed_tickets),
    }
    return render(request, "app/view_ticket.html", params)

@login_required(login_url='login')
def place_order_vector(request):
    if request.method == 'POST':
        try:
            # try:
            #     get_pricing = Pricing.objects.get(user=request.user)
            # except:
            #     get_pricing = None
            # Create a new DigitizingOrder instance
            order = VectorOrder(
                user=request.user,
                order_type='Vector Conversion',
                order_status='On Progress',
                payment_status='Pending Payment',
                # pricing_model_type=get_pricing.pricing_type,
                design_name=request.POST.get('design_name'),
                po_no=request.POST.get('po_no'),
                number_of_colors=request.POST.get('no_of_colors'),
                height=request.POST.get('Height', ''),
                width=request.POST.get('Width', ''),
                unit=request.POST.get('unit'),
                color_separation=request.POST.get('color_separation'),
                design_format=request.POST.get('design_format'),
                addtitoanl_instructions=request.POST.get('add_inst', '')
            )

            # print("files", request.FILES.getlist('artwork[]'))
            
            order.save()
            for file in request.FILES.getlist('artwork[]'):
                VectorOrderArtwork.objects.create(order=order, file=file)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
                # "site_url":request.get_host()
            }

            email_subject = f"Your Vector Order Received ({order.order_id}) {order.design_name} Logo"
            email_body = render_to_string("app/emails/order_placed_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"
            for file in request.FILES.getlist('artwork[]'):
                email_msg.attach(file.name, file.read(), file.content_type)
            email_msg.send()
            
            messages.success(request, 'Order placed successfully!')
            return redirect('/vector_order_list/')  # You'll need to define this URL

        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')
            return redirect('/vector_order_list/')
    return render(request  ,"app/place_order_vector.html")

@login_required(login_url='login')
def place_estimate_vector(request):
    if request.method == 'POST':
        try:
            
            # Create a new DigitizingOrder instance
            order = VectorEstimate(
                user=request.user,
                order_type='Vector Conversion',
                order_status='On Progress',
                payment_status='Pending Payment',
                # pricing_model_type=get_pricing.pricing_type,
                design_name=request.POST.get('design_name'),
                po_no=request.POST.get('po_no'),
                number_of_colors=request.POST.get('no_of_colors'),
                height=request.POST.get('Height', ''),
                width=request.POST.get('Width', ''),
                unit=request.POST.get('unit'),
                color_separation=request.POST.get('color_separation'),
                design_format=request.POST.get('design_format'),
                addtitoanl_instructions=request.POST.get('add_inst', '')
            )
            
            order.save()
            for file in request.FILES.getlist('artwork[]'):
                VectorEstimateArtwork.objects.create(estimate=order, file=file)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
                # "site_url":request.get_host()
            }

            email_subject = f"Your Vector Quote Received ({order.estimate_id}) {order.design_name} Logo"
            email_body = render_to_string("app/emails/quote_placed_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"
            for file in request.FILES.getlist('artwork[]'):
                email_msg.attach(file.name, file.read(), file.content_type)
            email_msg.send()

            # email_context = {
            #     "order": order,
            #     "user": request.user,
            #     "site_url": "https://portal.highfivedigitizing.com/",
            # }

            # email_subject = "Welcome to High Five Digitizing"
            # email_body = render_to_string("app/emails/order_placed_email.html", email_context)

            # email_msg = EmailMessage(email_subject, email_body, to=[request.user.email])
            # email_msg.content_subtype = "html"
            # email_msg.send()
            
            messages.success(request, 'Quote placed successfully!')
            return redirect('/vector_quote_list/')  # You'll need to define this URL

        except Exception as e:
            messages.error(request, f'Error placing estimate: {str(e)}')
            return redirect('/vector_quote_list/')
    return render(request  ,"app/place_estimate_vector.html")

@login_required(login_url='login')
def place_order_embroidery(request):
    # border_edge = BorderEdge.objects.all()
    # packages = Package.objects.all()
    # embroidery = Embroidery.objects.all()
    # base_material = BaseMaterial.objects.all()
    # backing_material = BackingMaterial.objects.all()
    
    if request.method == 'POST':
        # try:
            # Get pricing (optional)
            
            order = PatchesOrder(
                user=request.user,
                order_type='Embroidery Patches',
                order_status='On Progress',
                payment_status='Pending Payment',
                design_name=request.POST.get('design_name'),
                po_no=request.POST.get('po_no'),
                number_of_patches=request.POST.get('no_of_patches'),
                patch_type=request.POST.get('patch_type'),
                patch_backing=request.POST.get('patch_backing'),
                border=request.POST.get('Border', ''),
                width=request.POST.get('Width', ''),
                height=request.POST.get('Height', ''),
                unit=request.POST.get('unit', ''),
                number_of_colors=request.POST.get('no_of_colors'),
                addtitoanl_instructions=request.POST.get('add_inst', ''),
                delivery_address=request.POST.get('shipping_addr', ''),
            )

            order.save()
            for file in request.FILES.getlist('artwork[]'):
                PatchOrderArtwork.objects.create(order=order, file=file)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
            }

            email_subject = f"Your Patch Order Received ({order.order_id}) {order.design_name} Logo"
            email_body = render_to_string("app/emails/order_placed_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email,'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"
            for file in request.FILES.getlist('artwork[]'):
                email_msg.attach(file.name, file.read(), file.content_type)
            email_msg.send()


            messages.success(request, 'Order placed successfully!')
            return redirect('/patch_order_list/')

        # except Exception as e:
        #     messages.error(request, f'Error placing order: {str(e)}')
        #     return render(request, 'app/place_order_embroidery.html', {
        #         'form_data': request.POST,
        #         "border_edge": border_edge,
        #         "packages": packages,
        #         "embroidery": embroidery,
        #         "base_material": base_material,
        #         "backing_material": backing_material
        #     })

    # params = {
    #     "border_edge": border_edge,
    #     "packages": packages,
    #     "embroidery": embroidery,
    #     "base_material": base_material,
    #     "backing_material": backing_material
    # }
    return render(request, "app/place_order_embroidery.html")

@login_required(login_url='login')
def convert_estimate_to_order(request, estimate_id, type):
    add_inst_quote_to_order = request.POST.get('add_inst_quote_to_order', '')
    type = type.strip().lower()
    print('convert called', type)
    if type == "digitizing":
        # print("running digitizing")
        estimate = get_object_or_404(DigitizingEstimate, id=estimate_id)

        order = DigitizingOrder.objects.create(
            user = request.user,
            order_type = 'Digitizing',
            order_status = 'On Progress',
            payment_status = 'Pending Payment',
            design_name = estimate.design_name,
            number_of_colors = estimate.number_of_colors,
            po_no = estimate.po_no,
            height = estimate.height,
            width = estimate.width,
            unit = estimate.unit,
            type = estimate.type,
            placement = estimate.placement,
            required_blending = estimate.required_blending,
            Sew_Out_Sample = estimate.Sew_Out_Sample,
            design_format = estimate.design_format,
            addtitoanl_instructions = estimate.addtitoanl_instructions,
            addtitoanl_instructions_quote_to_order = add_inst_quote_to_order,
            
            number_of_stitches=estimate.number_of_stitches,
            amount=estimate.amount,
            instructions_for_user=estimate.instructions_for_user,
            width_for_admin=estimate.width_for_admin,
            height_for_admin=estimate.height_for_admin,
            thumbnail_image=estimate.thumbnail_image,
            
    )
        for est_art in estimate.artworks.all():
            # If you just want to reference the same file on disk:
            DigitizingOrderArtwork.objects.create(order=order, file=est_art.file)
        for uploaded_file in request.FILES.getlist('artwork[]'):
            # print("uploaded_file", uploaded_file)
            DigitizingOrderArtwork.objects.create(
                order=order,
                file=uploaded_file,  # Directly use the UploadedFile object
                order_file_type='quote_to_order'
            )
            
        for est_file in estimate.files.all():
            # Reference the same file:
            DigitizingOrderFile.objects.create(order=order, file=est_file.file)
        estimate.converted_to_order = True
        estimate.order_status = "Ordered"
        estimate.save()

        email_context = {
            "order": order,
            "user": request.user,
            "site_url": "https://portal.highfivedigitizing.com/",
            # "site_url":request.get_host()
        }

        email_subject = f"Your Quote Converted into Order ({estimate.estimate_id}) {estimate.design_name} Logo"
        email_body = render_to_string("app/emails/conver_quote_to_order.html", email_context)

        email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
        email_msg.content_subtype = "html"
        for file in request.FILES.getlist('artwork[]'):
            email_msg.attach(file.name, file.read(), file.content_type)
        email_msg.send()

        messages.success(request, "Your Estimate Successfully Converted into order")
        return redirect("/digitizing_order_list/")
        
    elif type == "vector conversion" or type == 'vector%20conversion':
        print('vector called')
        estimate = get_object_or_404(VectorEstimate, id=estimate_id)

        order = VectorOrder.objects.create(
            user = request.user,
            order_type = 'Vector Conversion',
            order_status = 'On Progress',
            payment_status = 'Pending Payment',
            design_name = estimate.design_name,
            po_no = estimate.po_no,
            number_of_colors = estimate.number_of_colors,
            height = estimate.height,
            width = estimate.width,
            unit = estimate.unit,
            color_separation = estimate.color_separation,
            design_format = estimate.design_format,
            addtitoanl_instructions = estimate.addtitoanl_instructions,
            addtitoanl_instructions_quote_to_order = add_inst_quote_to_order,

            number_of_stitches=estimate.number_of_stitches,
            amount=estimate.amount,
            instructions_for_user=estimate.instructions_for_user,
            thumbnail_image=estimate.thumbnail_image,
        )
        for est_art in estimate.artworks.all():
            # If you just want to reference the same file on disk:
            VectorOrderArtwork.objects.create(order=order, file=est_art.file)
            
        for est_file in estimate.files.all():
            # Reference the same file:
            VectorOrderFile.objects.create(order=order, file=est_file.file)
        estimate.converted_to_order = True
        estimate.order_status = "Ordered"
        estimate.save()

        email_context = {
            "order": order,
            "user": request.user,
            "site_url": "https://portal.highfivedigitizing.com/",
            # "site_url":request.get_host()
        }

        email_subject = f"Your Quote Converted into Order ({estimate.estimate_id}) {estimate.design_name} Logo"
        email_body = render_to_string("app/emails/conver_quote_to_order.html", email_context)

        email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
        email_msg.content_subtype = "html"
        for file in request.FILES.getlist('artwork[]'):
            email_msg.attach(file.name, file.read(), file.content_type)
        email_msg.send()

        messages.success(request, "Your Estimate Successfully Converted into order")
        return redirect("/vector_order_list/")
        
    elif type == "embroidery patches" or type == 'embroidery%patches':
        estimate = get_object_or_404(PatchesEstimates, id=estimate_id)

        order = PatchesOrder.objects.create(
            user = request.user,
            order_type = 'Embroidery Patches',
            order_status = 'On Progress',
            payment_status = 'Pending Payment',
            design_name = estimate.design_name,
            po_no = estimate.po_no,
            number_of_patches = estimate.number_of_patches,
            patch_type = estimate.patch_type,
            patch_backing = estimate.patch_backing,
            border = estimate.border,
            width = estimate.width,
            height = estimate.height,
            unit = estimate.unit,
            number_of_colors = estimate.number_of_colors,
            addtitoanl_instructions = estimate.addtitoanl_instructions,
            addtitoanl_instructions_quote_to_order = add_inst_quote_to_order,
            delivery_address = estimate.delivery_address,

            number_of_stitches=estimate.number_of_stitches,
            amount=estimate.amount,
            instructions_for_user=estimate.instructions_for_user,
            width_for_admin=estimate.width_for_admin,
            height_for_admin=estimate.height_for_admin,
            thumbnail_image=estimate.thumbnail_image,
            # stitched_image=estimate.stitched_image ,
            # preview_image=estimate.preview_image ,
            # preview_pdf=estimate.preview_pdf ,
        )
        for est_art in estimate.artworks.all():
            # If you just want to reference the same file on disk:
            PatchOrderArtwork.objects.create(order=order, file=est_art.file)

        for est_file in estimate.files.all():
            # Reference the same file:
            PatchOrderFile.objects.create(order=order, file=est_file.file)
        estimate.converted_to_order = True
        estimate.order_status = "Ordered"
        estimate.save()

        email_context = {
            "order": order,
            "user": request.user,
            "site_url": "https://portal.highfivedigitizing.com/",
            # "site_url":request.get_host()
        }

        email_subject = f"Your Quote Converted into Order ({estimate.estimate_id}) {estimate.design_name} Logo"
        email_body = render_to_string("app/emails/conver_quote_to_order.html", email_context)

        email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
        email_msg.content_subtype = "html"
        for file in request.FILES.getlist('artwork[]'):
            email_msg.attach(file.name, file.read(), file.content_type)
        email_msg.send()

        messages.success(request, "Your Estimate Successfully Converted into order")
        return redirect("/patch_order_list/")


    # Only allow conversion if payment is still pending or allowed
    # if estimate.payment_status != "Pending Payment":
    #     # You can add a message or redirect to show it's already processed
    #     return redirect("estimates_page")  # Change to your actual view name

    # Create new order from estimate
    # order = Order.objects.create(
    #     design_name=estimate.design_name,
    #     stitches=estimate.stitches,
    #     type=estimate.type,
    #     amount=estimate.amount,
    #     stitched_image=estimate.stitched_image,
    #     created_at=estimate.created_at,
    #     user=estimate.user,  # if you're associating users
    #     payment_status='Pending Payment',
    #     # Add other fields if necessary
    # )

    # Optional: Mark estimate as converted or link it to the order
    
    

  # or any page you want
@login_required(login_url='login')
def place_estimate_embroidery(request):
    # border_edge = BorderEdge.objects.all()
    # packages = Package.objects.all()
    # embroidery = Embroidery.objects.all()
    # base_material = BaseMaterial.objects.all()
    # backing_material = BackingMaterial.objects.all()
    
    if request.method == 'POST':
        # try:
            
            # Create order
            order = PatchesEstimates(
                user=request.user,
                order_type='Embroidery Patches',
                order_status='On Progress',
                payment_status='Pending Payment',
                design_name=request.POST.get('design_name'),
                po_no=request.POST.get('po_no'),
                number_of_patches=request.POST.get('no_of_patches'),
                patch_type=request.POST.get('patch_type'),
                patch_backing=request.POST.get('patch_backing'),
                border=request.POST.get('Border', ''),
                width=request.POST.get('Width', ''),
                height=request.POST.get('Height', ''),
                unit=request.POST.get('unit', ''),
                number_of_colors=request.POST.get('no_of_colors'),
                addtitoanl_instructions=request.POST.get('add_inst', ''),
                delivery_address=request.POST.get('shipping_addr', ''),
            )

            order.save()
            for file in request.FILES.getlist('artwork[]'):
                PatchEstimateArtwork.objects.create(estimate=order, file=file)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
                # "site_url":request.get_host()
            }

            email_subject = f"Your Patch Quote Received ({order.estimate_id}) {order.design_name} Logo"
            email_body = render_to_string("app/emails/quote_placed_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"
            for file in request.FILES.getlist('artwork[]'):
                email_msg.attach(file.name, file.read(), file.content_type)
            email_msg.send()

            messages.success(request, 'Quote placed successfully!')
            return redirect('/patch_quote_list/')

        # except Exception as e:
        #     messages.error(request, f'Error placing estimate: {str(e)}')
        #     return render(request, 'app/place_estimate_embroidery.html', {
        #         'form_data': request.POST,
        #         "border_edge": border_edge,
        #         "packages": packages,
        #         "embroidery": embroidery,
        #         "base_material": base_material,
        #         "backing_material": backing_material
        #     })

    params = {
        # "border_edge": border_edge,
        # "packages": packages,
        # "embroidery": embroidery,
        # "base_material": base_material,
        # "backing_material": backing_material
    }
    return render(request  ,"app/place_estimate_embroidery.html", params)

def reset_password(request):
    if request.method == "POST":
        uidb64 = request.GET["uid"]
        token = request.GET["token"]
        new_password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if not uidb64 or not token or not new_password or not confirm_password:
            return messages.error(request ,"Missing required fields.")

        if new_password != confirm_password:
            return messages.error(request ,"Passwords do not match.")
        try:
            # ✅ Fix: Check if UID is already an integer (not Base64)
            if uidb64.isdigit():
                uid = uidb64  # No need to decode
            else:
                uid = force_str(urlsafe_base64_decode(uidb64))  # Decode only if needed
            
            # ✅ Check if user exists
            user = User.objects.filter(pk=uid).first()
            if user is None:
                return messages.error(request ,"User not found")

            # ✅ Check if token is valid
            if not default_token_generator.check_token(user, token):
                return messages.error(request ,"Invalid or expired token.")

            user.set_password(new_password)
            user.save()
            messages.success(request ,"Password reset successfully!")
            return redirect("/login/")

        except Exception as e:
            return messages.error(request ,f"Error: {str(e)}")
    return render(request  ,"app/reset-password.html")


def forgot_password(request):
    if request.method == "POST":
        email = request.POST["email"]
        # print("email", email)
        if not email:
            return messages.error(request ,"Email is required")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return messages.error(request ,"User with this email does not exist")

        # Generate token
        token = default_token_generator.make_token(user)
        reset_link = f"https://portal.highfivedigitizing.com/reset_password?token={token}&uid={user.id}"  # Replace with your frontend URL

        # Send email
        send_mail(
            "Password Reset Request",
            f"Click the link to reset your password: {reset_link}",
            settings.DEFAULT_FROM_EMAIL,  # From email
            [email],
            fail_silently=False,
        )

        messages.success(request ,"Password reset link sent to your email")
        return redirect("/forgot_password/")
        # return redirect("")
    return render(request  ,"app/forgot-password.html")



def contact(request):
    if request.method == "POST":
        name = request.POST['name']
        email = request.POST['email']
        phone = request.POST['phone']
        organization_name = request.POST['organization_name']
        message = request.POST['message']

        # Save the contact details to the database
        Contact.objects.create(
            name=name,
            phone=phone,
            organization_name=organization_name,
            email=email,
            message=message,
        )

        # # Prepare email content
        # subject = "New Form Submission"
        # admin_email = 'kashanabid14@gmail.com'  # Admin email address

        # # Define context for email template
        # context = {
        #     'name': name,
        #     'phone': phone,
        #     'email': email,
        #     'organization_name': organization_name,
        #     'message': message,
        #     'submission_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        # }

        # # Render the email template
        # html_message = render_to_string('app/mail_template.html', context)
        # plain_message = strip_tags(html_message)

        # # Send the email
        # send_mail(
        #     subject,
        #     plain_message,
        #     settings.DEFAULT_FROM_EMAIL,  # From email
        #     [settings.EMAIL_HOST_USER],
        #     html_message=html_message,  # HTML content
        # )


        # Show success message and redirect
        messages.success(request, "Your Details have been Successfully Submitted. Thank You!")
        return redirect("/")

    return render(request, "app/contact.html")


# views.py
from django.http import JsonResponse
import zipfile, os, tempfile, shutil
from django.conf import settings
from .models import DigitizingOrder, VectorOrder, PatchesOrder

def prepare_extracted_files(request, order_id):
    type = request.GET.get('type', "Digitizing")
    if type == "Digitizing":
        order = DigitizingOrder.objects.get(pk=order_id)
    elif type == "Vector Conversion":
        order = VectorOrder.objects.get(pk=order_id)
    elif type == "Embroidery Patches":
        order = PatchesOrder.objects.get(pk=order_id)
    else:
        return JsonResponse({"error": "Invalid type"}, status=400)

    if not order.stitched_image.path.endswith('.zip'):
        return JsonResponse({"error": "Not a ZIP file"}, status=400)

    zip_path = order.stitched_image.path
    extract_dir_name = f"{order.design_name}_{order_id}"
    extract_dir = os.path.join(settings.MEDIA_ROOT, 'extracted', extract_dir_name)
    public_url_base = f"{settings.MEDIA_URL}extracted/{extract_dir_name}/"

    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    # Get file URLs
    file_urls = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), settings.MEDIA_ROOT)
            file_url = settings.MEDIA_URL + rel_path.replace("\\", "/")
            file_urls.append(file_url)

    return JsonResponse({"files": file_urls})



from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse

@staff_member_required
def custom_admin_dashboard(request):
    context = {
        "title": "Custom Dashboard",
        "all_digitizing_orders": DigitizingOrder.objects.all(),
        "pending_orders": DigitizingOrder.objects.filter(order_status='On Progress'),
        # "all_estimates": Estimate.objects.all(),
        # "all_edits": Edit.objects.all(),
        # "all_tickets": Ticket.objects.all(),
    }
    return TemplateResponse(request, "admin/custom_dashboard.html", context)




def pay_invoice(request):
    is_paid = False
    invoice_id = request.GET['invoice_id']
    get_inv = Invoice.objects.get(id=invoice_id)
    if get_inv.payment_status == "Success Payment":
        is_paid = True
    if request.method == "POST":
        paymentOption = request.POST['paymentOption']
        
        if paymentOption == "stripe":
            # print("okk")
            checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': get_inv.invoice_id,
                    },
                    'unit_amount': int(float(get_inv.grand_total if get_inv.grand_total else get_inv.total)) * 100,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://portal.highfivedigitizing.com/payment-done/?session_id={{CHECKOUT_SESSION_ID}}&invoice_id={get_inv.id}',
            cancel_url='https://portal.highfivedigitizing.com/payment_cancelled/',
        )
            return redirect(checkout_session.url, code=303)
        elif paymentOption == "paypal":
            # print("okkkkkkkkkkkkkk")
            host = request.get_host()
            paypal_dict = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': get_inv.grand_total if get_inv.grand_total else get_inv.total,
                'item_name': get_inv.invoice_id,
                'invoice': 'INV-'+str(get_inv.id),
                'currency_code': 'USD',
                'notify_url': 'http://{}{}'.format(host, reverse('paypal-ipn')),
                'return_url': 'http://{}{}'.format(host, reverse('payment_done')),
                'cancel_return': 'http://{}{}'.format(host, reverse('payment_cancelled')),
                'no_shipping': 1,
                'paymentaction': 'sale',
                'SOLUTIONTYPE': 'Sole',  # Enables guest checkout
                'LANDINGPAGE': 'Billing',  # Directs to credit card entry page
            }
            form = PayPalPaymentsForm(initial=paypal_dict)
            context = {"form": form}
            return render(request, "app/paypal_redirect.html", context)
            # return redirect(form)

    return render(request  ,"app/invoice_payment.html" , {"is_paid":is_paid, "get_inv":get_inv})



def create_invoice(request):
    # all_users = User.objects.filter(is_superuser=False)
    all_users = User.objects.all()
    last_invoice = Invoice.objects.last()
    if last_invoice:
        last_inv_no = last_invoice.id
    else:
        last_inv_no = 1
    invoice_no = f"INV-{last_inv_no + 1}"

    if request.method == 'POST':
        user = request.POST['user']
        try:
            get_user = User.objects.get(id=user)
        except:
            get_user = None
        other_amount_title = request.POST.get('other_input_title', '')
        other_amount = Decimal(request.POST.get('other_input_amount') or 0.00)
        discount_title = request.POST.get('discount_input_title', '')
        discount = Decimal(request.POST.get('discount_input_amount') or 0.00)
        shipping_title = request.POST.get('shipping_input_title', '')
        shipping = Decimal(request.POST.get('shipping_input_amount') or 0.00)
        notes = request.POST.get('notes', '')
        try:
            subtotal = Decimal(request.POST.get('subtotal') or 0)
        except InvalidOperation:
            subtotal = Decimal(0)

        try:
            total = Decimal(request.POST.get('total') or 0)
        except InvalidOperation:
            total = Decimal(0)

        # print("total", subtotal,"dfs", total)
        # payment_status = request.POST.get('payment_status', '')
        due_date = request.POST.get('due_date')

        # 2. Get item data (as lists)
        item_names = request.POST.getlist('item_name[]')
        item_amounts = request.POST.getlist('item_amount[]')
        item_qtys = request.POST.getlist('item_qty[]')

        # 3. Create invoice first (subtotal and total will be calculated next)
        invoice = Invoice.objects.create(
            user=get_user,
            notes=notes,
            other_amount_title=other_amount_title,
            other_amount=other_amount,
            discount_title=discount_title,
            discount=discount,
            shipping_title=shipping_title,
            shipping=shipping,
            payment_status="Pending Payment",
            due_date=due_date,
            subtotal=subtotal,
            total=total,
        )

        # 4. Loop through items and create InvoiceItem
        # subtotal = Decimal(0)
        for name, amount, qtys in zip(item_names, item_amounts, item_qtys):
            if name.strip():  # skip empty names
                price = Decimal(amount) if amount else Decimal(0)
                qty = int(qtys) if qtys else 1
                item = InvoiceItem.objects.create(
                    invoice=invoice,
                    item_name=name.strip(),
                    item_amount=price,
                    item_qty=qty  # Default quantity 1 unless you allow editing it
                )
                # subtotal += item.total  # item.total is qty * amount

        # 5. Update subtotal and total on Invoice
        # total = subtotal + other_amount + shipping - discount
        # invoice.subtotal = subtotal
        # invoice.total = total
        # invoice.save()
        
        invoice.send_invoice_email()

        
        return redirect(f'/invoice/{invoice.id}')  # or wherever

    return render(request, 'admin/create_invoice.html', {"all_users":all_users, "invoice_no":invoice_no})

def email_preview(request):
    return render(request, 'app/emails/account_registered_email.html',)


def send_edited_order_email(order):
    files = order.files.filter(is_visible=True)
    if not files.exists():
        return  # Skip if no files uploaded yet

    context = {
        "order": order,
        "user": order.user,
        "site_url": "https://portal.highfivedigitizing.com/",
    }

    subject = f"Your Order {order.order_id} has been Edited"
    body = render_to_string("app/emails/order_edited_email.html", context)

    email = EmailMessage(
        subject=subject,
        body=body,
        to=[order.user.email, 'info@highfivedigitizing.com'],
    )
    email.content_subtype = "html"

    for f in files:
        email.attach(f.file.name, f.file.read(), f.file.file.content_type)

    try:
        email.send()
    except Exception as e:
        print("Failed to send edited order email:", e)
def digitizing_edit(request, id):
    edit_type = request.GET.get("type", "order")
    order = []

    if edit_type == 'order':
        order = DigitizingOrder.objects.get(id=id)
    elif edit_type == 'quote':
        order = DigitizingEstimate.objects.get(id=id)

    if request.method == "POST":
        edit_remarks = request.POST.get("edit_remarks", '')
        artwork_files = request.FILES.getlist('artwork[]')

        if edit_type == 'order':
            DigitizingOrder.objects.filter(id=id).update(
                edit_remarks=edit_remarks,
                order_status="Edited"
            )

            for file in artwork_files:
                DigitizingOrderArtwork.objects.create(order=order, file=file, order_file_type='placing_edit')

            # Refresh the order object
            order = DigitizingOrder.objects.get(id=id)

            # Send email
            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
            }

            email_subject = f"Your Order {order.order_id} has been Edited"
            email_body = render_to_string("app/emails/order_edited_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"

            for file in artwork_files:
                file.seek(0)
                email_msg.attach(file.name, file.read(), file.content_type)

            email_msg.send()

            messages.success(request, "The Order has been successfully modified.")
            return redirect("/digitizing_order_list/")

        elif edit_type == 'quote':
            DigitizingEstimate.objects.filter(id=id).update(
                edit_remarks=edit_remarks,
                order_status="Edited"
            )

            for file in artwork_files:
                DigitizingEstimateArtwork.objects.create(estimate=order, file=file, order_file_type='placing_edit')

            # Refresh estimate
            order = DigitizingEstimate.objects.get(id=id)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
            }

            email_subject = f"Your Quote {order.estimate_id} has been Edited"
            email_body = render_to_string("app/emails/quote_edited_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"

            for file in artwork_files:
                file.seek(0)
                email_msg.attach(file.name, file.read(), file.content_type)

            email_msg.send()

            messages.success(request, "The Quote has been successfully modified.")
            return redirect("/digitizing_quote_list/")

    params = {
        "order": order,
    }
    return render(request, 'app/digitizing_edit.html', params)

def vector_edit(request, id):
    edit_type = request.GET.get("type", "order")
    order = []

    if edit_type == 'order':
        order = VectorOrder.objects.get(id=id)
    elif edit_type == 'quote':
        order = VectorEstimate.objects.get(id=id)

    if request.method == "POST":
        edit_remarks = request.POST.get("edit_remarks", '')
        artwork_files = request.FILES.getlist('artwork[]')

        if edit_type == 'order':
            VectorOrder.objects.filter(id=id).update(
                edit_remarks=edit_remarks,
                order_status="Edited"
            )

            for file in artwork_files:
                VectorOrderArtwork.objects.create(order=order, file=file, order_file_type='placing_edit')

            # Refresh the order object
            order = VectorOrder.objects.get(id=id)

            # Send email
            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
            }

            email_subject = f"Your Order {order.order_id} has been Edited"
            email_body = render_to_string("app/emails/order_edited_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"

            for file in artwork_files:
                file.seek(0)
                email_msg.attach(file.name, file.read(), file.content_type)

            email_msg.send()

            messages.success(request, "The Order has been successfully modified.")
            return redirect("/vector_order_list/")

        elif edit_type == 'quote':
            VectorEstimate.objects.filter(id=id).update(
                edit_remarks=edit_remarks,
                order_status="Edited"
            )

            for file in artwork_files:
                VectorEstimateArtwork.objects.create(estimate=order, file=file, order_file_type='placing_edit')

            # Refresh estimate
            order = VectorEstimate.objects.get(id=id)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
            }

            email_subject = f"Your Quote {order.estimate_id} has been Edited"
            email_body = render_to_string("app/emails/quote_edited_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"

            for file in artwork_files:
                file.seek(0)
                email_msg.attach(file.name, file.read(), file.content_type)

            email_msg.send()

            messages.success(request, "The Quote has been successfully modified.")
            return redirect("/vector_quote_list/")

    params = {
        "order": order,
    }
    return render(request, 'app/vector_edit.html', params)


def patch_edit(request, id):
    edit_type = request.GET.get("type", "order")
    order = []

    if edit_type == 'order':
        order = PatchesOrder.objects.get(id=id)
    elif edit_type == 'quote':
        order = PatchesEstimates.objects.get(id=id)

    if request.method == "POST":
        edit_remarks = request.POST.get("edit_remarks", '')
        artwork_files = request.FILES.getlist('artwork[]')

        if edit_type == 'order':
            PatchesOrder.objects.filter(id=id).update(
                edit_remarks=edit_remarks,
                order_status="Edited"
            )

            for file in artwork_files:
                PatchOrderArtwork.objects.create(order=order, file=file, order_file_type='placing_edit')

            # Refresh the order object
            order = PatchesOrder.objects.get(id=id)

            # Send email
            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
            }

            email_subject = f"Your Order {order.order_id} has been Edited"
            email_body = render_to_string("app/emails/order_edited_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"

            for file in artwork_files:
                file.seek(0)
                email_msg.attach(file.name, file.read(), file.content_type)

            email_msg.send()

            messages.success(request, "The Order has been successfully modified.")
            return redirect("/patch_order_list/")

        elif edit_type == 'quote':
            PatchesEstimates.objects.filter(id=id).update(
                edit_remarks=edit_remarks,
                order_status="Edited"
            )

            for file in artwork_files:
                PatchEstimateArtwork.objects.create(estimate=order, file=file, order_file_type='placing_edit')

            # Refresh estimate
            order = PatchesEstimates.objects.get(id=id)

            email_context = {
                "order": order,
                "user": request.user,
                "site_url": "https://portal.highfivedigitizing.com/",
            }

            email_subject = f"Your Quote {order.estimate_id} has been Edited"
            email_body = render_to_string("app/emails/quote_edited_email.html", email_context)

            email_msg = EmailMessage(email_subject, email_body, to=[request.user.email, 'info@highfivedigitizing.com'])
            email_msg.content_subtype = "html"

            for file in artwork_files:
                file.seek(0)
                email_msg.attach(file.name, file.read(), file.content_type)

            email_msg.send()

            messages.success(request, "The Estimate has been successfully modified.")
            return redirect("/patch_quote_list/")

    params = {
        "order": order,
    }
    return render(request, 'app/patch_edit.html', params)


def invoice(request, id):
    from decimal import Decimal

    try:
        get_inv = Invoice.objects.get(id=id)
        get_inv_items = InvoiceItem.objects.filter(invoice=get_inv)

        subtotal = Decimal('0.00')
        for item in get_inv_items:
            total = Decimal(item.unit_price)
            item.formatted_total = f"{total:.2f}"
            subtotal += total

        for item in get_inv_items:
            total = Decimal(item.unit_price)
            item.formatted_total = f"{total:.2f}"  # Adds attribute with 2 decimal places

    except Invoice.DoesNotExist:
        return redirect("/")

    params = {
        "get_inv": get_inv,
        "get_inv_items": get_inv_items,
        "subtotal": f"{subtotal:.2f}",
    }

    return render(request, 'app/invoice_pre.html',params)

def apply_coupon(request):
    if request.method == "POST":
        code = request.POST.get('coupon_code')
        order_id = request.POST.get('order_id')
        order_type = request.POST.get('type')

        # Identify order type
        if order_type == "Digitizing":
            order_model = DigitizingOrder
        elif order_type == "Vector Conversion":
            order_model = VectorOrder
        elif order_type == "Embroidery Patches":
            order_model = PatchesOrder
        else:
            return JsonResponse({'success': False, 'message': 'Invalid order type.'})

        # Get the order
        try:
            order = order_model.objects.get(id=order_id)
        except order_model.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found.'})

        # Get the user from the order
        user = order.user  # Assumes order model has a ForeignKey to User as `user`

        # Check if user has any paid orders
        has_paid_order = (
            DigitizingOrder.objects.filter(user=user, payment_status="Success Payment").exists() or
            VectorOrder.objects.filter(user=user, payment_status="Success Payment").exists() or
            PatchesOrder.objects.filter(user=user, payment_status="Success Payment").exists()
        )

        if has_paid_order:
            return JsonResponse({'success': False, 'message': 'This coupon is only for first-time customers.'})

        # Get and validate coupon
        try:
            coupon = Coupon.objects.get(code=code)
            ip_address = get_client_ip(request)

            if CouponUsage.objects.filter(coupon=coupon, ip_address=ip_address).exists():
                return JsonResponse({'success': False, 'message': 'This coupon has already been used from your network.'})
            else:
                CouponUsage.objects.create(coupon=coupon, ip_address=ip_address)
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid coupon code.'})

        if not coupon.is_valid():
            return JsonResponse({'success': False, 'message': 'Coupon is expired or has been fully used.'})

        # Apply discount based on type
        if coupon.discount_type == 'percent':
            discount_amount = float(order.amount) * (float(coupon.discount_value) / 100)
        else:  # fixed amount
            discount_amount = float(coupon.discount_value)

        discount_amount = min(discount_amount, float(order.amount))  # Avoid negative totals
        new_total = float(order.amount) - discount_amount

        # Optionally update used count (only if applying immediately)
        coupon.used_count += 1
        coupon.save()

        order.discount = discount_amount
        order.total = new_total
        order.coupon = coupon  # optional: store the code used
        order.save()

        return JsonResponse({
            'success': True,
            'message': f"Coupon applied! You saved ${discount_amount:.2f}.",
            'discount': f"{discount_amount:.2f}",
            'new_total': f"{new_total:.2f}"
        })

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def apply_coupon_for_invoice(request):
    print("DEBUG: Method =", request.method)
    print("DEBUG: POST data =", request.POST)
    if request.method == "POST":
        code = request.POST.get('coupon_code')
        order_id = request.POST.get('order_id')
        order_type = request.POST.get('type')

        # Get the order
        try:
            order = Invoice.objects.get(id=order_id)
        except Invoice.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invoice not found.'})

        # Get the user from the order
        user = order.user  # Assumes order model has a ForeignKey to User as `user`

        # Check if user has any paid orders
        has_paid_order = (
            DigitizingOrder.objects.filter(user=user, payment_status="Success Payment").exists() or
            VectorOrder.objects.filter(user=user, payment_status="Success Payment").exists() or
            PatchesOrder.objects.filter(user=user, payment_status="Success Payment").exists()
        )

        if has_paid_order:
            return JsonResponse({'success': False, 'message': 'This coupon is only for first-time customers.'})

        # Get and validate coupon
        # try:
        coupon = Coupon.objects.get(code=code)
        ip_address = get_client_ip(request)

        if CouponUsage.objects.filter(coupon=coupon, ip_address=ip_address).exists():
            return JsonResponse({'success': False, 'message': 'This coupon has already been used from your network.'})
        else:
            CouponUsage.objects.create(coupon=coupon, ip_address=ip_address)
        # except Coupon.DoesNotExist:
        #     return JsonResponse({'success': False, 'message': 'Invalid coupon code.'})

        if not coupon.is_valid():
            return JsonResponse({'success': False, 'message': 'Coupon is expired or has been fully used.'})

        # Apply discount based on type
        if coupon.discount_type == 'percent':
            discount_amount = float(order.total) * (float(coupon.discount_value) / 100)
        else:  # fixed amount
            discount_amount = float(coupon.discount_value)

        discount_amount = min(discount_amount, float(order.total))  # Avoid negative totals
        new_total = float(order.total) - discount_amount

        # Optionally update used count (only if applying immediately)
        coupon.used_count += 1
        coupon.save()

        order.coupon_discount = round(discount_amount, 2)
        order.grand_total = new_total
        order.coupon = coupon  # optional: store the code used
        order.save()

        return JsonResponse({
            'success': True,
            'message': f"Coupon applied! You saved ${discount_amount:.2f}.",
            'discount': f"{discount_amount:.2f}",
            'new_total': f"{new_total:.2f}"
        })

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required(login_url='login')
def digitizing_order_list(request):
    query = request.GET.get('q', '')

    orders_list = DigitizingOrder.objects.filter(user=request.user).order_by("-id")
    if query:
        orders_list = orders_list.filter(
            Q(order_id__icontains=query) |
            Q(design_name__icontains=query) |
            Q(po_no__icontains=query)
        )

    paginator = Paginator(orders_list, 8)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    return render(request, 'app/digitizing_order_list.html', {
        "orders": orders,
        "query": query
    })

@login_required(login_url='login')
def vector_order_list(request):
    query = request.GET.get('q', '')

    orders_list = VectorOrder.objects.filter(user=request.user).order_by("-id")
    if query:
        orders_list = orders_list.filter(
            Q(order_id__icontains=query) |
            Q(design_name__icontains=query) |
            Q(po_no__icontains=query)
        )

    paginator = Paginator(orders_list, 8)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    return render(request, 'app/vector_order_list.html', {
        "orders": orders,
        "query": query
    })

@login_required(login_url='login')
def patch_order_list(request):
    query = request.GET.get('q', '')

    orders_list = PatchesOrder.objects.filter(user=request.user).order_by("-id")
    if query:
        orders_list = orders_list.filter(
            Q(order_id__icontains=query) |
            Q(design_name__icontains=query) |
            Q(po_no__icontains=query)
        )

    paginator = Paginator(orders_list, 8)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    return render(request, 'app/patch_order_list.html', {
        "orders": orders,
        "query": query
    })

@login_required(login_url='login')
def digitizing_quote_list(request):
    query = request.GET.get('q', '')

    estimates_list = DigitizingEstimate.objects.filter(user=request.user).order_by("-id")
    if query:
        estimates_list = estimates_list.filter(
            Q(estimate_id__icontains=query) |
            Q(design_name__icontains=query) |
            Q(po_no__icontains=query)
        )

    paginator = Paginator(estimates_list, 8)
    page_number = request.GET.get('page')
    estimates = paginator.get_page(page_number)

    return render(request, 'app/digitizing_quote_list.html', {
        "estimates": estimates,
        "query": query
    })

@login_required(login_url='login')
def vector_quote_list(request):
    query = request.GET.get('q', '')

    estimates_list = VectorEstimate.objects.filter(user=request.user).order_by("-id")
    if query:
        estimates_list = estimates_list.filter(
            Q(estimate_id__icontains=query) |
            Q(design_name__icontains=query) |
            Q(po_no__icontains=query)
        )

    paginator = Paginator(estimates_list, 8)
    page_number = request.GET.get('page')
    estimates = paginator.get_page(page_number)

    return render(request, 'app/vector_quote_list.html', {
        "estimates": estimates,
        "query": query
    })

@login_required(login_url='login')
def patch_quote_list(request):
    query = request.GET.get('q', '')

    estimates_list = PatchesEstimates.objects.filter(user=request.user).order_by("-id")
    if query:
        estimates_list = estimates_list.filter(
            Q(estimate_id__icontains=query) |
            Q(design_name__icontains=query) |
            Q(po_no__icontains=query)
        )

    paginator = Paginator(estimates_list, 8)
    page_number = request.GET.get('page')
    estimates = paginator.get_page(page_number)

    return render(request, 'app/patch_quote_list.html', {
        "estimates": estimates,
        "query": query
    })

@login_required(login_url='login')
def download_all_files(request, order_id):
    type = request.GET.get("type", "Digitizing")
    # try:
    if type == "Digitizing":
        order = DigitizingOrder.objects.get(id=order_id , user=request.user)
        
    elif type == "Vector Conversion" or type == "Vector":
        # print("id", id)
        order = VectorOrder.objects.get(id=order_id , user=request.user)

    elif type == "Embroidery Patches" or type == "Patches":
        order = PatchesOrder.objects.get(id=order_id , user=request.user)
    
    # order = DigitizingOrder.objects.get(id=order_id, user=request.user)
    files = order.files.all()

    # Create a zip in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for f in files:
            filename = os.path.basename(f.file.name)
            zip_file.writestr(filename, f.file.read())

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=order_{order_id}_files.zip'
    return response



@login_required(login_url='login')
def get_user_orders(request, user_id):
    """AJAX endpoint to fetch user orders"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        digitizing_orders = DigitizingOrder.objects.filter(user__id=user_id, order_status__in=['Delivered', 'Edited'], payment_status='Pending Payment')
        vector_orders = VectorOrder.objects.filter(user__id=user_id, order_status__in=['Delivered', 'Edited'], payment_status='Pending Payment')
        patch_orders = PatchesOrder.objects.filter(user__id=user_id, order_status__in=['Delivered', 'Edited'], payment_status='Pending Payment')
        
        orders_data = []
        
        for order in digitizing_orders:
            orders_data.append({
                'id': order.order_id,
                'model_type': 'Digitizing',
                'order_number': order.order_id,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'total_amount': order.amount,
                'status': order.order_status,
                'design_name': order.design_name,
                'po_number': order.po_no,
                'type': order.order_type
            })

        for order in vector_orders:
            orders_data.append({
                'id': order.order_id,
                'model_type': 'Vector',
                'order_number': order.order_id,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'total_amount': order.amount,
                'status': order.order_status,
                'design_name': order.design_name,
                'po_number': order.po_no,
                'type': order.order_type
            })

        for order in patch_orders:
            orders_data.append({
                'id': order.order_id,
                'model_type': 'Patch',
                'order_number': order.order_id,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'total_amount': order.amount,
                'status': order.order_status,
                'design_name': order.design_name,
                'po_number': order.po_no,
                'type': order.order_type
            })
        
        orders_data.sort(key=lambda x: x['created_at'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'orders': orders_data,
            'user': {
                'id': user.id,
                'username': user.first_name,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required(login_url='login')
def generate_invoice(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        order_ids = request.POST.getlist('order_ids')

        if not user_id or not order_ids:
            return redirect('create_invoice')

        user = get_object_or_404(User, id=user_id)

        selected_orders = []
        total_amount = 0

        for order_id in order_ids:
            if order_id.startswith('DO-'):
                actual_id = order_id.replace('DO-', '')
                try:
                    order = DigitizingOrder.objects.get(id=actual_id, user=user)
                    # print("po no" , order.po_no)
                    selected_orders.append({
                        'order_number': order.order_id,
                        'po_number': order.po_no,
                        'design_name': order.design_name,
                        'order_date': order.created_at,
                        'type': 'Digitizing',
                        'price': order.amount
                    })
                    total_amount += order.amount
                except DigitizingOrder.DoesNotExist:
                    continue

            elif order_id.startswith('VO-'):
                actual_id = order_id.replace('VO-', '')
                try:
                    order = VectorOrder.objects.get(id=actual_id, user=user)
                    # print("po no" , order.po_no)
                    selected_orders.append({
                        'order_number': order.order_id,
                        'po_number': order.po_no,
                        'design_name': order.design_name,
                        'order_date': order.created_at,
                        'type': 'Vector',
                        'price': order.amount
                    })
                    total_amount += order.amount
                except VectorOrder.DoesNotExist:
                    continue

            elif order_id.startswith('PO-'):
                actual_id = order_id.replace('PO-', '')
                try:
                    order = PatchesOrder.objects.get(id=actual_id, user=user)
                    # print("po no" , order.po_no)
                    selected_orders.append({
                        'order_number': order.order_id,
                        'po_number': order.po_no,
                        'design_name': order.design_name,
                        'order_date': order.created_at,
                        'type': 'Patch',
                        'price': order.amount
                    })
                    total_amount += order.amount
                except PatchesOrder.DoesNotExist:
                    continue

        if not selected_orders:
            return redirect('create_invoice')

        try:
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    user=user,
                    payment_status='UNPAID',
                    total=total_amount,
                    due_date=now() + timedelta(days=5)
                )

                for item in selected_orders:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        item_name=item['design_name'],
                        order_date=item['order_date'],
                        po_no=item['po_number'],
                        item_type=item['type'],
                        order_number=item['order_number'],
                        unit_price=item['price'],
                        total=item['price']
                    )
                invoice.send_invoice_email()

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

        # ✅ Redirect to preview page with ID
        return redirect(f'/invoice_preview?token={invoice.preview_token}')

    return redirect('create_invoice')

# @login_required(login_url='login')
def download_invoice_pdf(request, invoice_id):
    """Download invoice as PDF from DB"""
    try:
        if request.user.is_superuser:
            invoice = Invoice.objects.select_related('user').prefetch_related('items').get(pk=invoice_id)
        else:
            invoice = Invoice.objects.select_related('user').prefetch_related('items').get(pk=invoice_id, user=request.user)
    except Invoice.DoesNotExist:
        return HttpResponse("Invoice not found.", status=404)

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    import os
    from django.conf import settings

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    # Custom styles
    styles = getSampleStyleSheet()
    
    # Company header style
    company_style = ParagraphStyle(
        'CompanyStyle',
        parent=styles['Title'],
        fontSize=28,
        textColor=colors.HexColor('#4285f4'),
        spaceAfter=5,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT
    )
    
    # Company tagline style
    tagline_style = ParagraphStyle(
        'TaglineStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        fontName='Helvetica',
        alignment=TA_LEFT
    )
    
    # Invoice title style
    invoice_title_style = ParagraphStyle(
        'InvoiceTitleStyle',
        parent=styles['Title'],
        fontSize=36,
        textColor=colors.HexColor('#4285f4'),
        spaceAfter=10,
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT
    )
    
    # Invoice details style
    invoice_details_style = ParagraphStyle(
        'InvoiceDetailsStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=20,
        fontName='Helvetica',
        alignment=TA_RIGHT
    )
    
    # Status style
    status_style = ParagraphStyle(
        'StatusStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.white,
        spaceAfter=20,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        backColor=colors.HexColor('#dc3545') if invoice.payment_status == 'UNPAID' else colors.HexColor('#28a745')
    )
    
    # Customer info style
    customer_style = ParagraphStyle(
        'CustomerStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=20,
        fontName='Helvetica',
        alignment=TA_LEFT
    )
    
    styles = getSampleStyleSheet()

    story = []

    # Get full image path
    image_path = os.path.join(settings.BASE_DIR, 'static/app/assets/images/high_five_FINALLL__1_-removebg-preview.png')

    # Create Image element (adjust size as needed)
    logo = Image(image_path, width=1.6 * inch, height=1.6 * inch)

    # Left side content (image + text)
    left_column = [
        logo,
        # Paragraph('<font size="10" color="#666666">Digitizing • Vector Art • Patches</font>', styles['Normal']),
    ]

    # Right side invoice details
    right_column = Paragraph(f'''
        <para align="right">
            <font size="36" color="#4285f4"><b>INVOICE</b></font><br/>
            <font size="10" color="#333333">
                <b>INVOICE NO:</b> {invoice.invoice_id}<br/>
                <b>INVOICE DATE:</b> {invoice.invoice_date.strftime('%d %b %Y')}<br/>
                <b>EXPIRY DATE:</b> {invoice.due_date.strftime('%d %b %Y') if invoice.due_date else 'N/A'}
            </font>
        </para>
    ''', styles['Normal'])

    # Table with logo + text on left and invoice details on right
    header_data = [[left_column, right_column]]

    header_table = Table(header_data, colWidths=[4 * inch, 3 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
    ]))

    story.append(header_table)
    
    # Blue line separator
    line_data = [['', '']]
    line_table = Table(line_data, colWidths=[7*inch])
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 3, colors.HexColor('#4285f4')),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(line_table)
    
    # Status Badge
    status_color = '#dc3545' if invoice.payment_status == 'UNPAID' else '#28a745'
    status_data = [[Paragraph(f'<para align="center"><font color="white"><b>{invoice.payment_status}</b></font></para>', styles['Normal'])]]
    status_table = Table(status_data, colWidths=[7*inch])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(status_color)),
        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 20))
    
    # Customer Information Section
    user = invoice.user
    customer_info = f'''
        <para>
            <font size="10" color="#666666"><b>INVOICE TO</b></font><br/>
            <font size="14" color="#333333"><b>{user.get_full_name() or user.first_name}</b></font><br/>
            <font size="11" color="#666666">{user.email}</font>
        </para>
    '''
    
    customer_data = [[Paragraph(customer_info, styles['Normal'])]]
    customer_table = Table(customer_data, colWidths=[7*inch])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('LINEBELOW', (0, 0), (-1, -1), 0, colors.HexColor('#4285f4')),
    ]))
    story.append(customer_table)
    story.append(Spacer(1, 25))
    
    # Items Table Header
    table_data = [['S.NO', 'ORDER NO', 'PO NUMBER', 'DESIGN NAME', 'ORDER DATE', 'TYPE', 'PRICE']]
    
    # Items Table Data
    for i, item in enumerate(invoice.items.all(), 1):
        # Color code for item types
        item_type_color = '#1565c0' if item.item_type == 'Digitizing' else '#2e7d32' if item.item_type == 'Vector' else '#ef6c00'
        
        table_data.append([
            str(i),
            item.order_number or '-',
            item.po_no or '-',
            item.item_name,
            item.order_date.strftime('%d %b %Y') if item.order_date else '-',
            f'{item.item_type}',
            f"${item.total:.2f}"
        ])
    
    # Create table with proper column widths
    table = Table(table_data, colWidths=[0.5*inch, 1*inch, 1*inch, 2*inch, 1*inch, 1*inch, 0.8*inch])
    
    # Enhanced table styling
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4285f4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        
        # Grid lines
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        
        # Price column alignment
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        
        # Order number column styling
        ('TEXTCOLOR', (1, 1), (1, -1), colors.HexColor('#4285f4')),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 25))
    
    # Totals Section
    totals_data = [
        ['', '', 'Subtotal:', f"${invoice.total:.2f}"],
    ]
    
    if hasattr(invoice, 'tax_amount') and invoice.tax_amount > 0:
        totals_data.append(['', '', 'Tax:', f"${invoice.tax_amount:.2f}"])
    
    totals_data.append(['', '', 'TOTAL AMOUNT:', f"${invoice.total:.2f} USD"])
    
    totals_table = Table(totals_data, colWidths=[2*inch, 2*inch, 1.5*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (2, 0), (2, -2), 'Helvetica'),
        ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (2, 0), (-1, -2), 11),
        ('FONTSIZE', (2, -1), (-1, -1), 14),
        ('TEXTCOLOR', (2, -1), (-1, -1), colors.HexColor('#4285f4')),
        ('TOPPADDING', (2, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (2, 0), (-1, -1), 8),
        ('LINEABOVE', (2, -1), (-1, -1), 2, colors.HexColor('#4285f4')),
    ]))
    
    story.append(totals_table)
    story.append(Spacer(1, 40))
    
    # Footer
    footer_text = '''
        <para align="center">
            <font size="11" color="#4285f4"><b>High Five Digitizing</b></font><br/>
            Thank you for your business!
        </para>
    '''
    
    footer_data = [[Paragraph(footer_text, styles['Normal'])]]
    footer_table = Table(footer_data, colWidths=[7*inch])
    footer_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
    ]))
    story.append(footer_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_id}.pdf"'

    return response


def invoice_preview_new(request):
    """Publicly accessible invoice preview using token"""
    token = request.GET.get("token")
    if not token:
        return HttpResponse("Missing token.", status=400)

    try:
        invoice = Invoice.objects.select_related('user').prefetch_related('items').get(preview_token=token)
    except Invoice.DoesNotExist:
        return HttpResponse("Invalid or expired link.", status=404)

    invoice_data = {
        'invoice_number': invoice.invoice_id,
        'invoice_id': invoice.id,
        'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d'),
        'due_date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else 'N/A',
        'customer': {
            'name': f"{invoice.user.first_name} {invoice.user.last_name}".strip() or invoice.user.first_name,
            'email': invoice.user.email,
        },
        'orders': [],
        'subtotal': invoice.total,
        'total': invoice.total,
        'status': invoice.payment_status
    }

    for item in invoice.items.all():
        invoice_data['orders'].append({
            'order_number': item.order_number or '-',
            'po_number': item.po_no,
            'design_name': item.item_name,
            'order_date': invoice.invoice_date.strftime('%Y-%m-%d'),
            'type': item.item_type or '-',
            'price': item.total
        })

    return render(request, 'admin/invoice_preview.html', {
        'invoice_data': invoice_data
    })