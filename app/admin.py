from django.contrib import admin
from .models import *
from django.urls import path
from django.template.response import TemplateResponse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


from datetime import datetime, date
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.utils.text import capfirst
from admin_interface.models import Theme
from .forms import DigitizingOrderForm
from django.utils.timezone import now
from django.http import HttpResponseRedirect


class MyAdminSite(AdminSite):
    index_template = "admin/dashboard.html"

    def index(self, request, extra_context=None):
        date_from = request.GET.get('From_date')
        date_to = request.GET.get('To_date')

        if not (date_from and date_to):
            date_from = now().date()
            date_to = now().date()

        user = request.user

        # Initialize data
        digitizing_orders = digitizing_estimate = []
        vector_orders = vector_estimate = []
        patches_orders = patches_estimate = []

        # Collect only data user has permission for
        if user.has_perm("app.view_digitizingorder"):
            digitizing_orders = DigitizingOrder.objects.all()
            digitizing_estimate = DigitizingEstimate.objects.all()

        if user.has_perm("app.view_vectororder"):
            vector_orders = VectorOrder.objects.all()
            vector_estimate = VectorEstimate.objects.all()

        if user.has_perm("app.view_patchesorder"):
            patches_orders = PatchesOrder.objects.all()
            patches_estimate = PatchesEstimates.objects.all()

        # Redirect if user has no access at all
        if not (digitizing_orders or vector_orders or patches_orders):
            # Get all registered models
            for model, model_admin in self._registry.items():
                opts = model._meta
                app_label = opts.app_label
                model_name = opts.model_name

                permission = f"{app_label}.view_{model_name}"
                if user.has_perm(permission):
                    try:
                        url = reverse(f"admin:{app_label}_{model_name}_changelist")
                        return HttpResponseRedirect(url)
                    except:
                        continue  # If reverse fails, skip

        # Build estimates
        estimates = []
        for order in digitizing_estimate:
            estimates.append({
                'type': 'Digitizing',
                'id': order.id,
                'user': order.user,
                'order_status': order.order_status,
                'estimate_id': order.estimate_id,
                'converted': order.converted_to_order,
                'stitches': order.number_of_stitches,
                'design_name': order.design_name,
                'amount': order.amount,
                'created_at': order.created_at,
            })
        for order in vector_estimate:
            estimates.append({
                'type': 'Vector',
                'id': order.id,
                'user': order.user,
                'order_status': order.order_status,
                'estimate_id': order.estimate_id,
                'converted': order.converted_to_order,
                'design_name': order.design_name,
                'amount': order.amount,
                'created_at': order.created_at,
            })
        for order in patches_estimate:
            estimates.append({
                'type': 'Patches',
                'id': order.id,
                'user': order.user,
                'order_status': order.order_status,
                'estimate_id': order.estimate_id,
                'converted': order.converted_to_order,
                'design_name': order.design_name,
                'amount': order.amount,
                'created_at': order.created_at,
            })

        estimates.sort(key=lambda x: x['created_at'], reverse=True)
        estimates = estimates[:10]

        # Build actual orders
        orders = []
        for order in digitizing_orders:
            orders.append({
                'type': 'Digitizing',
                'id': order.id,
                'user': order.user,
                'order_status': order.order_status,
                'order_id': order.order_id,
                'stitches': order.number_of_stitches,
                'payment_status': order.payment_status,
                'design_name': order.design_name,
                'amount': order.amount,
                'created_at': order.created_at,
            })
        for order in vector_orders:
            orders.append({
                'type': 'Vector',
                'id': order.id,
                'user': order.user,
                'order_status': order.order_status,
                'order_id': order.order_id,
                'design_name': order.design_name,
                'payment_status': order.payment_status,
                'amount': order.amount,
                'created_at': order.created_at,
            })
        for order in patches_orders:
            orders.append({
                'type': 'Patches',
                'id': order.id,
                'user': order.user,
                'order_status': order.order_status,
                'order_id': order.order_id,
                'design_name': order.design_name,
                'payment_status': order.payment_status,
                'amount': order.amount,
                'created_at': order.created_at,
            })

        orders.sort(key=lambda x: x['created_at'], reverse=True)
        orders = orders[:10]

        app_list = sorted(
            [{
                "name": model._meta.app_label.title(),
                "models": [],
            } for model in self._registry.keys()],
            key=lambda x: x["name"]
        )

        if extra_context is None:
            extra_context = {}

        extra_context.update({
            "app_list": app_list,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "orders": orders,
            "estimates": estimates,
        })

        # Add individual counts only if user has permission
        if user.has_perm("app.view_digitizingorder"):
            extra_context.update({
                "total_dig_order": digitizing_orders.count(),
                "digitizing_quote": digitizing_estimate.count(),
                "digitizing_on_progress": digitizing_orders.filter(order_status="On Progress").count(),
                "digitizing_on_edit": digitizing_orders.filter(order_status="Edited").count(),
                "digitizing_on_progress_quote": digitizing_estimate.filter(order_status="On Progress").count(),
                "digitizing_on_edit_quote": digitizing_estimate.filter(order_status="Edited").count(),
                "digitizing_complete": digitizing_orders.filter(order_status="Delivered").count(),
            })

        if user.has_perm("app.view_vectororder"):
            extra_context.update({
                "total_vec_order": vector_orders.count(),
                "vector_quote": vector_estimate.count(),
                "vector_on_progress": vector_orders.filter(order_status="On Progress").count(),
                "vector_on_edit": vector_orders.filter(order_status="Edited").count(),
                "vector_on_progress_quote": vector_estimate.filter(order_status="On Progress").count(),
                "vector_on_edit_quote": vector_estimate.filter(order_status="Edited").count(),
                "vector_complete": vector_orders.filter(order_status="Delivered").count(),
            })

        if user.has_perm("app.view_patchesorder"):
            extra_context.update({
                "total_pat_order": patches_orders.count(),
                "patch_quote": patches_estimate.count(),
                "patch_on_progress": patches_orders.filter(order_status="On Progress").count(),
                "patch_on_edit": patches_orders.filter(order_status="Edited").count(),
                "patch_on_progress_quote": patches_estimate.filter(order_status="On Progress").count(),
                "patch_on_edit_quote": patches_estimate.filter(order_status="Edited").count(),
                "patch_complete": patches_orders.filter(order_status="Delivered").count(),
            })

        return super().index(request, extra_context=extra_context)

# Instantiate and use the custom admin site
custom_admin_site = MyAdminSite(name="myadmin")

# custom_admin_site.register(Theme)


custom_admin_site.register(User , UserAdmin)
custom_admin_site.register(Group , GroupAdmin)



class DigitizingEstimateArtworkInline(admin.TabularInline):
    model = DigitizingEstimateArtwork
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-order_file_type', 'id')  # True first, then by ID

class VectorEstimateArtworkInline(admin.TabularInline):
    model = VectorEstimateArtwork
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-order_file_type', 'id')  # True first, then by ID

class PatchEstimateArtworkInline(admin.TabularInline):
    model = PatchEstimateArtwork
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-order_file_type', 'id')  # True first, then by ID

class DigitizingOrderArtworkInline(admin.TabularInline):
    model = DigitizingOrderArtwork
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-order_file_type', 'id')  # True first, then by ID

class VectorOrderArtworkInline(admin.TabularInline):
    model = VectorOrderArtwork
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-order_file_type', 'id')  # True first, then by ID

class PatchOrderArtworkInline(admin.TabularInline):
    model = PatchOrderArtwork
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-order_file_type', 'id')  # True first, then by ID

class DigitizingEstimateFileInline(admin.TabularInline):
    model = DigitizingEstimateFile
    extra = 0

class VectorEstimateFileInline(admin.TabularInline):
    model = VectorEstimateFile
    extra = 0

class PatchEstimateFileInline(admin.TabularInline):
    model = PatchEstimateFile
    extra = 0

class DigitizingOrderFileInline(admin.TabularInline):
    model = DigitizingOrderFile
    extra = 0

class VectorOrderFileInline(admin.TabularInline):
    model = VectorOrderFile
    extra = 0

class PatchOrderFileInline(admin.TabularInline):
    model = PatchOrderFile
    extra = 0


class DigitizingOrderAdmin(admin.ModelAdmin):
    readonly_fields = ("order_type",)
    form = DigitizingOrderForm
    inlines = [DigitizingOrderFileInline , DigitizingOrderArtworkInline]
    # readonly_fields = ['Crop_perview', 'Profile_perview']
    search_fields = ("design_name", "order_status", "order_id")
    list_filter = ("user", "order_status")
    list_display = ("design_name", "user", "order_id", "number_of_colors", "amount", "height", "width", "unit", "order_status")
    list_editable = ("order_status",)
    fieldsets = [
        ("", {
            "classes": ("collapse"),
            "fields": (
                    #     ('Crop_perview'),
                    #    ('thumbnail_image' , 'Profile_perview'),
                       ('user', 'order_type'),
                       ('design_name' , 'number_of_colors'),
                       ('payment_status'),
                       ('po_no'),
                       ('height' , 'width' , 'unit'),
                       ('type'),
                       ('placement' , 'required_blending'),
                       ('design_format'),
                       ('addtitoanl_instructions'),
                       ('addtitoanl_instructions_quote_to_order'),
                       ('edit_remarks'),
                    #    ('artwork'),
                        
                ),
        }),
        
        ("Submit Order", {
            "classes": ("collapse"),
            "fields": (('number_of_stitches', 'width_for_admin', 'height_for_admin') ,
                       ('amount'),
                       ('instructions_for_user'),
                       ('thumbnail_image'),
                       ('order_status'),
                ),
        }),
        
        
       
    ]


class VectorOrderAdmin(admin.ModelAdmin):
    form = DigitizingOrderForm
    readonly_fields = ("order_type",)
    inlines = [VectorOrderFileInline , VectorOrderArtworkInline]
    search_fields = ("design_name", "order_status", 'order_id')
    list_filter = ("user", "order_status")
    list_display = ("design_name", "order_id", "user", "number_of_colors", "amount", "order_status")
    list_editable = ("order_status",)
    fieldsets = [
        ("", {
            "classes": ("collapse"),
            "fields": (

                       ('user', 'order_type'),
                       ("po_no"),
                       ('design_name' , 'number_of_colors'),
                       
                       ('payment_status'),
                       ('design_format'),
                       ('color_separation'),
                       ('unit', 'width', 'height'),
                       ('addtitoanl_instructions'),
                       ('addtitoanl_instructions_quote_to_order'),
                       ('edit_remarks'),
                        
                ),
        }),
        
        ("Submit Order", {
            "classes": ("collapse"),
            "fields": (('amount') ,
                    #    ('amount'),
                       ('instructions_for_user'),
                       ('thumbnail_image'),
                       ('order_status'),
                ),
        }),
        
       
    ]

class PatchesOrderAdmin(admin.ModelAdmin):
    form = DigitizingOrderForm
    readonly_fields = ("order_type",)
    inlines = [PatchOrderFileInline , PatchOrderArtworkInline]
    search_fields = ("design_name", "order_status", 'order_id')
    list_filter = ("user", "order_status")
    list_display = ("order_id", "user", "number_of_colors", "amount", "order_status")
    list_editable = ("order_status",)
    fieldsets = [
        ("", {
            "classes": ("collapse"),
            "fields": (

                       ('user', 'order_type'),
                       ("po_no"),
                       ('design_name' , 'number_of_colors'),
                       ('unit' , 'width', 'height'),
                       ('payment_status'),
                       ('number_of_patches', 'patch_type'),
                       ('patch_backing', 'border'),
                       ('delivery_address'),
                       ('addtitoanl_instructions'),
                       ('addtitoanl_instructions_quote_to_order'),
                       ('edit_remarks'),
                        
                ),
        }),
        
        ("Submit Order", {
            "classes": ("collapse"),
            "fields": (('number_of_colors_for_admin', 'width_for_admin', 'height_for_admin') ,
                       ('amount'),
                       ('instructions_for_user'),
                       ('shipping_address'),
                       ('thumbnail_image'),
                       ('order_status'),
                ),
        }),
        
       
    ]

class VectorEstimateAdmin(admin.ModelAdmin):
    form = DigitizingOrderForm
    readonly_fields = ("order_type",)
    inlines = [VectorEstimateFileInline , VectorEstimateArtworkInline]
    search_fields = ("design_name", "order_status", 'estimate_id')
    list_filter = ("user", "order_status")
    list_display = ("design_name", "estimate_id", "user", "number_of_colors", "amount", "order_status")
    list_editable = ("order_status",)
    fieldsets = [
        ("", {
            "classes": ("collapse"),
            "fields": (

                       ('user', 'order_type'),
                       ("po_no"),
                       ('design_name' , 'number_of_colors'),
                       
                    #    ('payment_status'),
                       ('color_separation'),
                       ('design_format'),
                       ('addtitoanl_instructions'),
                       ('edit_remarks'),
                        
                ),
        }),
        
        ("Submit Order", {
            "classes": ("collapse"),
            "fields": (('amount') ,
                       ('instructions_for_user'),
                       ('thumbnail_image'),
                       ('order_status'),
                ),
        }),
        
       
    ]
        
       

class DigitizingEstimateAdmin(admin.ModelAdmin):
    form = DigitizingOrderForm
    readonly_fields = ("order_type",)
    inlines = [DigitizingEstimateFileInline , DigitizingEstimateArtworkInline]
    search_fields = ("design_name", "order_status", 'estimate_id')
    list_filter = ("user", "order_status")
    list_display = ("design_name", "user", "estimate_id", "number_of_colors", "amount", "height", "width", "unit", "order_status")
    list_editable = ("order_status",)
    fieldsets = [
        ("", {
            "classes": ("collapse"),
            "fields": (

                       ('user', 'order_type'),
                       ('design_name' , 'number_of_colors'),
                       
                       ('po_no'),
                       ('height' , 'width' , 'unit'),
                       ('type'),
                       ('placement' , 'required_blending'),
                       ('design_format'),
                       ('addtitoanl_instructions'),
                       ('edit_remarks'),
                    #    ('artwork'),
                        
                ),
        }),
        
        ("Submit Order", {
            "classes": ("collapse"),
            "fields": (('number_of_stitches', 'width_for_admin', 'height_for_admin') ,
                       ('amount'),
                       ('instructions_for_user'),
                       ('thumbnail_image'),
                       ('order_status'),
                ),
        }),
        
        
       
    ]



class PatchesEstimateAdmin(admin.ModelAdmin):
    form = DigitizingOrderForm
    readonly_fields = ("order_type",)
    inlines = [PatchEstimateFileInline , PatchEstimateArtworkInline]
    search_fields = ("design_name", "order_status", 'estimate_id')
    list_filter = ("user", "order_status")
    list_display = ("design_name", "estimate_id", "user", "number_of_colors", "amount", "order_status")
    list_editable = ("order_status",)
    fieldsets = [
        ("", {
            "classes": ("collapse"),
            "fields": (

                       ('user', 'order_type'),
                       ("po_no"),
                       ('design_name' , 'number_of_colors'),
                    
                       ('number_of_patches', 'patch_type'),
                       ('patch_backing', 'border'),
                       ('delivery_address', 'converted_to_order'),
                       ('addtitoanl_instructions'),
                       ('edit_remarks'),
                        
                ),
        }),
        
        ("Submit Order", {
            "classes": ("collapse"),
            "fields": (('number_of_colors_for_admin', 'width_for_admin', 'height_for_admin') ,
                       ('amount'),
                       ('instructions_for_user'),
                       ('shipping_address'),
                       ('thumbnail_image'),
                       ('order_status'),
                ),
        }),
        
       
    ]


custom_admin_site.register(DigitizingOrder, DigitizingOrderAdmin)

class ProfileAdmin(admin.ModelAdmin):
    form = DigitizingOrderForm
    # readonly_fields = ('user',)
    list_display = ('user', 'mobile_no', 'country', 'company')
    fields = (
        ('user', 'mobile_no'),
        ('country', 'company'),
        ('city', 'state'),
        ('website', 'business_phone_no'),
        ('invoice_email', 'reference'),
        ('address',),
    )

custom_admin_site.register(Profile, ProfileAdmin)


# custom_admin_site.register(Contact)
# custom_admin_site.register(Package)
# custom_admin_site.register(Coupon)
# custom_admin_site.register(CouponUsage)
# custom_admin_site.register(BorderEdge)
# custom_admin_site.register(Embroidery)
custom_admin_site.register(VectorOrder, VectorOrderAdmin)
custom_admin_site.register(PatchesOrder, PatchesOrderAdmin)
custom_admin_site.register(VectorEstimate, VectorEstimateAdmin)
custom_admin_site.register(PatchesEstimates, PatchesEstimateAdmin)
custom_admin_site.register(DigitizingEstimate, DigitizingEstimateAdmin)
# custom_admin_site.register(BaseMaterial)
# custom_admin_site.register(BackingMaterial)

class NotificationAdmin(admin.ModelAdmin):
    class Media:
        js = ('tiny1.js',)

# custom_admin_site.register(Notification, NotificationAdmin)
# custom_admin_site.register(OpenTicket)
# custom_admin_site.register(Pricing)
# custom_admin_site.register(Edits)
# custom_admin_site.register(Profile)

class ServiceAdmin(admin.ModelAdmin):
    class Media:
        js=("tiny.js",)



# class CustomDashboardAdmin(admin.ModelAdmin):
#     def get_urls(self):
#         urls = super().get_urls()
#         custom_urls = [
#             path('custom-dashboard/', self.admin_site.admin_view(self.custom_dashboard_view), name="custom-dashboard"),
#         ]
#         return custom_urls + urls

#     def custom_dashboard_view(self, request):
#         context = dict(
#             self.admin_site.each_context(request),
#             all_digitizing_orders=DigitizingOrder.objects.all(),
#             pending_orders=DigitizingOrder.objects.filter(order_status='In Process'),
#             all_estimates=VectorEstimate.objects.all(),
#             all_edits=Edits.objects.all(),
#             all_tickets=OpenTicket.objects.all(),
#         )
#         return TemplateResponse(request, "admin/custom_dashboard.html", context)

# # Optionally register this with a dummy model to display in the menu
# custom_admin_site.register_view("custom-dashboard", view=CustomDashboardAdmin().custom_dashboard_view, name="Custom Dashboard")



class InvoiceItemInline(admin.TabularInline):  # or admin.StackedInline for vertical layout
    model = InvoiceItem
    extra = 0  # How many extra blank items to show
    fields = ('order_number', 'item_name', 'po_no', 'total')  # Optional: specify fields to show
    # readonly_fields = ('total',)  # Optional: make total read-only if it's auto-calculated

    class Media:
        js = ('custom.js',)


from rangefilter.filters import DateRangeFilter
class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInline]
    list_filter = (
        "user",
        "payment_status",
        ("invoice_date", DateRangeFilter),
    )
    search_fields = ("invoice_id",)
    list_display = ("invoice_id", "user", "total",'payment_status', "InvoicePreview")
    list_editable = ('payment_status', )

    fieldsets = [
        ("", {
            "classes": ("collapse"),
            "fields": (
            ("invoice_id", 'user'),
            # ("other_amount_title", 'other_amount'),
            # ("discount_title", 'discount'),
            # ("shipping_title", 'shipping'),
            ("payment_status", 'total'),
            ('due_date',),
            # ("notes",),
                       
                        
                ),
        }),
        
        
       
    ]

#     fieldsets = [
#     ("", {
#         "classes": ("collapse",),
#         "fields": (
#             ("invoice_id", 'user'),
#             ("other_amount_title", 'other_amount'),
#             ("discount_title", 'discount'),
#             ("shipping_title", 'shipping'),
#             ("payment_status", 'total'),
#             ('due_date',),
#             ("notes",),
#         ),
#     }),
#     ("Coupon", {
#         "classes": ("collapse",),
#         "fields": (
#             ('coupon', "coupon_discount"),
#             ('grand_total',),
#         ),
#     }),
# ]

    change_list_template = 'admin/invoice_change_list.html'

    def changelist_view(self, request, extra_context=None):
        custom_url = reverse('create_invoice')  # your custom add-invoice view
        extra_context = extra_context or {}
        extra_context['custom_add_url'] = custom_url
        return super().changelist_view(request, extra_context=extra_context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        invoice = form.instance
        items = invoice.items.all()

        # total_items_sum = sum(item.item_qty * item.item_amount for item in items)
        # invoice.total = total_items_sum + invoice.other_amount
        # invoice.save(update_fields=['total'])

        # Choose recipient
        # recipient_email = invoice.user.email

        # if recipient_email:
        # subject = "Your Invoice is Ready"
        # to_email = invoice.user.email
        # payment_url = f"http://192.168.18.81:8888/pay/?invoice_id={invoice.id}"  # update this to your real URL

        # context = {
        #     'user': invoice.user,
        #     'invoice': invoice,
        #     'payment_url': payment_url,
        # }

        # message = render_to_string('app/invoice_email.html', context)
        # email = EmailMessage(subject, message, to=[to_email])
        # email.content_subtype = 'html'
        # email.send()

custom_admin_site.register(Invoice, InvoiceAdmin)

class CustomOfferAdmin(admin.ModelAdmin):
    class Media:
        js = ("tiny.js",)
# custom_admin_site.register(CustomOffer, CustomOfferAdmin)


class InvoiceForPortalUserAdmin(admin.ModelAdmin):
    list_display = ("invoice_id", "user", "created_at")
    fields = (
        ("user",),
        ("order_digitizing"),
        ("order_vector"),
        ("order_patches"),
        ("status"),
    )


# custom_admin_site.register(InvoiceForPortalUser, InvoiceForPortalUserAdmin)