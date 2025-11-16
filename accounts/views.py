from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from .models import MainActuator, OrderDetails
from django.db.models import IntegerField
from django.db.models.functions import Cast, Substr
from django.http import HttpResponse

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from django.shortcuts import get_object_or_404
from datetime import datetime

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Login successful!')
            # Redirect to role-specific dashboard
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def dashboard_view(request):
    role = request.user.profile.role
    return redirect(f'{role.lower().replace(" ", "_")}_dashboard')

@login_required
def assembly_engineer_dashboard(request):
    if request.method == 'POST':
        try:
            data = {
                "sr_no": "001",
                "sales_order_no":"20011793",
                "order_no": "21002717",
                "order_qty": "5",
                "line_item": "30",
                "series": "25",
                "type": "DA",
                "size": "250",
                "cylinder size": "007",
                "spring size": "",
                "moc": "CS",
                "customer": "Japro Eng",
                "item_code": "ACT5588",
                "creation_date": "2025-10-30",
                "branch": "Pune"
                }
            order_no = data.get('order_no', '')
            if MainActuator.objects.filter(order_no=order_no).exists():
                messages.error(request, f'Order number {order_no} already exists. Cannot create duplicate entry.')
            else:
                actuator = MainActuator.objects.create(
                    sales_order_no=data.get('sales_order_no', ''),
                    order_no=order_no,
                    line_item=data.get('line_item', ''),
                    order_qty=data.get('order_qty', ''),
                    series=data.get('series', ''),
                    type=data.get('type', ''),
                    size=data.get('size', ''),
                    cylinder_size=data.get('cylinder size', ''),
                    spring_size=data.get('spring size', ''),
                    moc=data.get('moc', ''),
                    customer=data.get('customer', ''),
                    item_code=data.get('item_code', ''),
                    creation_date=data.get('creation_date', ''),
                    branch=data.get('branch', ''),
                    order_status='under_assembly'
                )
                # Auto-create OrderDetails entries
                qty = int(data.get('order_qty', '0'))
                for i in range(1, qty + 1):
                    serial_no = f"{order_no}-{i}"
                    OrderDetails.objects.create(
                        order_no=actuator,
                        actuator_serial_no=serial_no,
                    )
                messages.success(request, f'Actuator data for order {actuator.order_no} saved successfully! Created {qty} OrderDetails entries.')
        except Exception as e:
            messages.error(request, f'Error saving data: {str(e)}')
        return redirect('assembly_engineer_dashboard')
    return render(request, 'accounts/assembly_engineer_dashboard.html')

@login_required
@login_required
def assembler_dashboard(request):

    # Annotate all orders that are in assembly
    orders_under_assembly = MainActuator.objects.filter(order_status="under_assembly").annotate(
        total_qty=models.Count("order_details"),
        completed_qty=models.Count(
            "order_details",
            filter=models.Q(order_details__assembler_status="completed")
        )
    )

    # Calculate pending = total - completed
    for o in orders_under_assembly:
        o.pending_qty = o.total_qty - o.completed_qty

    # Find completed orders (where pending_qty = 0)
    completed_orders = [o for o in orders_under_assembly if o.pending_qty == 0]

    # Exclude completed from "under assembly"
    orders_under_assembly = [o for o in orders_under_assembly if o.pending_qty > 0]

    return render(request, 'accounts/assembler_dashboard.html', {
        "orders_under_assembly": orders_under_assembly,
        "completed_orders": completed_orders,
    })

@login_required
def tester_dashboard(request):
    return render(request, 'accounts/tester_dashboard.html')

@login_required
def painting_engineer_dashboard(request):
    return render(request, 'accounts/painting_engineer_dashboard.html')

@login_required
def painter_dashboard(request):
    return render(request, 'accounts/painter_dashboard.html')

@login_required
def blaster_dashboard(request):
    return render(request, 'accounts/blaster_dashboard.html')

@login_required
def name_plate_printer_dashboard(request):
    return render(request, 'accounts/name_plate_printer_dashboard.html')

@login_required
def finisher_dashboard(request):
    return render(request, 'accounts/finisher_dashboard.html')

@login_required
def qa_engineer_dashboard(request):
    return render(request, 'accounts/qa_engineer_dashboard.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

@login_required
def assembler_order_details(request, order_no):
    try:
        order = MainActuator.objects.get(order_no=order_no)
    except MainActuator.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('assembler_dashboard')

    actuators = (
        OrderDetails.objects
        .filter(order_no=order)
        .annotate(
            serial_num=Cast(
                Substr("actuator_serial_no", len(order_no) + 2),  # extract after "ORDERNO-"
                IntegerField()
            )
        )
        .order_by("serial_num"))

    # POST for SAVE / SUBMIT
    if request.method == "POST":
        order_detail_id = request.POST.get("order_detail_id")
        action = "save" if "save" in request.POST else "submit"

        try:
            detail = OrderDetails.objects.get(id=order_detail_id)

            if action == "save":
                detail.housing_heat_no = request.POST.get('housing_heat_no', "")
                detail.yoke_heat_no = request.POST.get('yoke_heat_no', "")
                detail.top_cover_heat_no = request.POST.get('top_cover_heat_no', "")
                detail.da_side_adaptor_plate_heat_no = request.POST.get('da_side_adaptor_plate_heat_no', "")
                detail.spring_side_adaptor_heat_no = request.POST.get('spring_side_adaptor_heat_no', "")
                detail.da_side_end_plate_heat_no = request.POST.get('da_side_end_plate_heat_no', "")
                detail.spring_side_end_plate_heat_no = request.POST.get('spring_side_end_plate_heat_no', "")
                detail.save()
                messages.success(request, "Heat numbers updated.")

            if action == "submit":
                # Backend validation: all fields must be filled
                required_fields = [
                    detail.housing_heat_no,
                    detail.yoke_heat_no,
                    detail.top_cover_heat_no,
                    detail.da_side_adaptor_plate_heat_no,
                    detail.spring_side_adaptor_heat_no,
                    detail.da_side_end_plate_heat_no,
                    detail.spring_side_end_plate_heat_no,
                ]

                if any(field in ["", None] for field in required_fields):
                    messages.error(request, "All heat numbers must be filled before marking as completed.")
                    return redirect('assembler_order_details', order_no=order_no)

                detail.assembler_status = "completed"
                detail.save()
                messages.success(request, "Actuator marked completed.")

        except Exception as e:
            messages.error(request, str(e))

        return redirect('assembler_order_details', order_no=order_no)

    return render(request, "accounts/assembler_order_details.html", {
        "order": order,
        "actuators": actuators,
    })

@login_required
def generate_heat_report(request, order_no):

    # Fetch order header
    order = get_object_or_404(MainActuator, order_no=order_no)

    # Fetch all actuators for this order
    actuators = OrderDetails.objects.filter(order_no=order).order_by("actuator_serial_no")

    # PDF response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Heat_Report_{order_no}.pdf"'

    pdf = canvas.Canvas(response, pagesize=landscape(A4))
    width, height = landscape(A4)

    y = height - 1.5 * cm

    # =========================================
    # 1. TITLE
    # =========================================
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(width / 2, y, "DELVAL FLOW CONTROLS PRIVATE LIMITED")
    y -= 1.2 * cm

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width / 2, y, "HEAT ANNEXTURE - ACTUATOR")
    y -= 1.5 * cm

    # =========================================
    # 2. TOP INFORMATION (TABLE STYLE)
    # =========================================
    pdf.setFont("Helvetica", 11)

    combined_size = f"{order.size}, {order.cylinder_size}, {order.spring_size or '-'}"
    today = datetime.now().strftime("%d-%m-%Y")

    top_data = [
        ["Item Code:", order.item_code, "Size:", combined_size],
        ["Qty:", order.order_qty, "Date:", today],
        ["Customer:", order.customer, "SO Number:", order.sales_order_no],
    ]

    top_table = Table(top_data, colWidths=[3*cm, 7*cm, 3*cm, 7*cm])
    top_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))

    top_table.wrapOn(pdf, width, height)
    top_table.drawOn(pdf, 1.0*cm, y - 3*cm)

    y -= 4 * cm  # Space before main table

    # =========================================
    # 3. MAIN TABLE HEADER
    # =========================================
    headers = [
        "Sr No", "Actuator Serial", "Housing Heat No", "Yoke Heat No",
        "Top Cover Heat No", "DA Adaptor Plate", "Spring Adaptor Plate",
        "DA End Plate", "Spring End Plate", "Assembler"
    ]

    table_data = [headers]

    assembler_name = request.user.get_full_name() or request.user.username

    # Add rows
    sr = 1
    for a in actuators:
        table_data.append([
            sr,
            a.actuator_serial_no,
            a.housing_heat_no or "-",
            a.yoke_heat_no or "-",
            a.top_cover_heat_no or "-",
            a.da_side_adaptor_plate_heat_no or "-",
            a.spring_side_adaptor_heat_no or "-",
            a.da_side_end_plate_heat_no or "-",
            a.spring_side_end_plate_heat_no or "-",
            assembler_name
        ])
        sr += 1

    # =========================================
    # 4. STYLE THE TABLE
    # =========================================
    table = Table(table_data, repeatRows=1, colWidths=[
        1.5*cm, 3*cm, 3*cm, 3*cm, 3*cm,
        3*cm, 3*cm, 3*cm, 3*cm, 3*cm
    ])

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
    ]))

    # Draw table
    table.wrapOn(pdf, width, height)
    table.drawOn(pdf, 1.0*cm, y - (len(table_data) * 0.7 * cm))

    pdf.showPage()
    pdf.save()
    return response
