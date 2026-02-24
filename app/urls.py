from django.urls import path , include
from . import views

urlpatterns = [
    path('', views.home),
    path('invoice_list/', views.invoice_list),
    # path('invoice_preview/', views.invoice_preview),
    path('orders/', views.orders),
    path('payment/', views.payment),
    path('pay/', views.pay_invoice),
    path('place_order/', views.place_order),
    path('order_preview/<int:id>/', views.order_preview),
    path('edit_preview/<int:id>/', views.edit_preview),
    path('estimate_preview/<int:id>/', views.estimate_preview),
    path('place_estimate/', views.place_estimate),
    path('place_edit/', views.place_edit),
    path('estimates/', views.estimates),
    path('edits/', views.edits),
    path('unpaid_invoices/', views.unpaid_invoices),
    path('notifications/', views.notifications),
    path('noti_preview/<int:id>', views.noti_preview),
    path('profile/', views.profile),
    path('select_pricing/', views.select_pricing),
    path('pricing/', views.select_pricing),
    path('login/', views.login_view, name="login"),
    path('logout/', views.user_logout),
    path('signup/', views.signup),
    path('open_ticket/', views.open_ticket),
    path('view_ticket/', views.view_ticket),
    path('place_order_vector/', views.place_order_vector),
    path('place_estimate_vector/', views.place_estimate_vector),
    path('place_order_embroidery/', views.place_order_embroidery),
    path('place_estimate_embroidery/', views.place_estimate_embroidery),
    path('reset_password/', views.reset_password),
    path('forgot_password/', views.forgot_password),
    path('update_profile/', views.update_profile),
    path('prepare-extracted-files/<int:order_id>/', views.prepare_extracted_files, name='download_extracted'),
    path('convert_estimate/<int:estimate_id>/<str:type>/', views.convert_estimate_to_order, name='convert_estimate'),
    path('change-password/', views.change_password, name='change_password'),
    path('invoice/<int:id>/', views.invoice, name='change_password'),
    path('digitizing_edit/<int:id>/', views.digitizing_edit, name='digitizing_edit'),
    path('vector_edit/<int:id>/', views.vector_edit, name='digitizing_edit'),
    path('patch_edit/<int:id>/', views.patch_edit, name='digitizing_edit'),


    path('custom-dashboard/', views.custom_admin_dashboard, name='custom-dashboard'),

    path('custom-invoice/add/', views.create_invoice, name='create_invoice'),

    path('apply_coupon/', views.apply_coupon, name='apply_coupon'),
    path('apply_coupon_for_invoice/', views.apply_coupon_for_invoice, name='apply_coupon'),

    # path('paypal/', include('paypal.standard.ipn.urls')),
    path('payment-done/', views.payment_done, name='payment_done'),
    path('payment-cancelled/', views.payment_canceled, name='payment_cancelled'),


    
    path('digitizing_order_list/', views.digitizing_order_list, name='digitizing_order_list'),
    path('vector_order_list/', views.vector_order_list, name='digitizing_order_list'),
    path('patch_order_list/', views.patch_order_list, name='patch_order_list'),
    
    path('digitizing_quote_list/', views.digitizing_quote_list, name='digitizing_quote_list'),
    path('vector_quote_list/', views.vector_quote_list, name='digitizing_quote_list'),
    path('patch_quote_list/', views.patch_quote_list, name='patch_quote_list'),

    path('download-all/<int:order_id>/', views.download_all_files, name='download_all_files'),

   
    path('api/user-orders/<int:user_id>/', views.get_user_orders, name='get_user_orders'),
    path('generate-invoice/', views.generate_invoice, name='generate_invoice'),
    path('download-invoice-pdf/<int:invoice_id>/', views.download_invoice_pdf, name='download_invoice_pdf'),
    path('invoice_preview/', views.invoice_preview_new, name='invoice_preview'),
] 
