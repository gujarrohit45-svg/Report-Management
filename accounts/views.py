from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import IntegerField
from django.db.models.functions import Cast, Substr
from django.http import HttpResponse
from datetime import datetime
import json  # <-- CRITICAL FIX: Added this import

from .models import MainActuator, OrderDetails

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm



# ================================================================
#  USER AUTHENTICATION
# ================================================================
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
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')



# ================================================================
#   ROLE-BASED DASHBOARD
# ================================================================
@login_required
def dashboard_view(request):
    role = request.user.profile.role
    return redirect(f"{role.lower().replace(' ', '_')}_dashboard")



# ================================================================
#   ASSEMBLY ENGINEER – QR INSERT LOGIC
# ================================================================
@login_required
def assembly_engineer_dashboard(request):
    """
    Accepts POSTed JSON in 'actuator_data' (hidden input).
    The JSON can come from QR scan (scanned payload) or manual entry.
    """

    if request.method == "POST":
        # parse posted actuator JSON
        raw = request.POST.get("actuator_data", "") or request.POST.dict()
        data = None
        try:
            # If actuator_data is a JSON string, parse it
            if isinstance(raw, str) and raw.strip():
                data = json.loads(raw)  # <-- This line needs 'import json'
            elif isinstance(raw, dict):
                # some browsers may send form dict; try to extract known keys
                data = {k: v for k, v in raw.items()}
            else:
                data = {}
        except Exception as e:
            messages.error(request, f"Invalid actuator data JSON: {e}")
            return redirect("assembly_engineer_dashboard")

        # Normalize keys - prefer snake_case keys expected by the form
        def get(d, *keys):
            for k in keys:
                if k in d and d[k] not in (None, ""):
                    return d[k]
            return ""

        order_no = get(data, "order_no", "order no", "orderno")
        sales_order_no = get(data, "sales_order_no", "sales order no", "salesorder")
        order_qty = get(data, "order_qty", "order qty", "qty", "quantity") or "1"

        if not order_no or not sales_order_no:
            messages.error(request, "Order No and Sales Order No are required.")
            return redirect("assembly_engineer_dashboard")

        # duplicate check
        if MainActuator.objects.filter(order_no=order_no).exists():
            messages.error(request, f"Order {order_no} already exists.")
            return redirect("assembly_engineer_dashboard")

        # Create MainActuator record (fill missing keys with empty string)
        try:
            actuator = MainActuator.objects.create(
                sales_order_no = sales_order_no,
                order_no = order_no,
                line_item = get(data, "line_item", "line item"),
                order_qty = order_qty,
                series = get(data, "series"),
                type = get(data, "type"),
                size = get(data, "size"),
                cylinder_size = get(data, "cylinder_size", "cylinder size"),
                spring_size = get(data, "spring_size", "spring size"),
                moc = get(data, "moc"),
                customer = get(data, "customer"),
                item_code = get(data, "item_code", "item code"),
                creation_date = get(data, "creation_date"),
                branch = get(data, "branch"),
                order_status = "under_assembly"
            )
        except Exception as e:
            messages.error(request, f"Failed to create actuator: {e}")
            return redirect("assembly_engineer_dashboard")

        # Create OrderDetails serials
        try:
            qty = int(order_qty)
        except:
            qty = 1

        order_details = [
            OrderDetails(order_no=actuator, actuator_serial_no=f"{order_no}-{i}")
            for i in range(1, qty + 1)
        ]
        OrderDetails.objects.bulk_create(order_details)

        messages.success(request, f"Added order {order_no} • Created {qty} serial units")
        return redirect("assembly_engineer_dashboard")

    # GET: render template
    return render(request, "accounts/assembly_engineer_dashboard.html")


# ================================================================
#   ASSEMBLER DASHBOARD
# ================================================================
@login_required
def assembler_dashboard(request):

    orders = MainActuator.objects.filter(order_status="under_assembly").annotate(
        total_qty=models.Count("order_details"),
        completed_qty=models.Count(
            "order_details",
            filter=models.Q(order_details__assembler_status="completed")
        )
    )

    for o in orders:
        o.pending_qty = o.total_qty - o.completed_qty

    return render(request, "accounts/assembler_dashboard.html", {
        "orders_under_assembly": [o for o in orders if o.pending_qty > 0],
        "completed_orders": [o for o in orders if o.pending_qty == 0],
    })



# ================================================================
#   ASSEMBLER – ORDER DETAILS PAGE
# ================================================================
@login_required
def assembler_order_details(request, order_no):

    order = get_object_or_404(MainActuator, order_no=order_no)

    actuators = (
        OrderDetails.objects.filter(order_no=order)
        .annotate(serial_num=Cast(Substr("actuator_serial_no",
                                        len(order_no) + 2), IntegerField()))
        .order_by("serial_num")
    )

    if request.method == "POST":
        try:
            pk = request.POST["order_detail_id"]
            detail = OrderDetails.objects.get(id=pk)

            if "save" in request.POST:
                # Update only heat numbers
                fields = [
                    'housing_heat_no', 'yoke_heat_no', 'top_cover_heat_no',
                    'da_side_adaptor_plate_heat_no', 'spring_side_adaptor_heat_no',
                    'da_side_end_plate_heat_no', 'spring_side_end_plate_heat_no'
                ]

                for f in fields:
                    setattr(detail, f, request.POST.get(f, ""))

                detail.save()
                messages.success(request, "Heat numbers saved.")

            if "submit" in request.POST:

                # Validate all required heat numbers
                required = [
                    detail.housing_heat_no,
                    detail.yoke_heat_no,
                    detail.top_cover_heat_no,
                    detail.da_side_adaptor_plate_heat_no,
                    detail.spring_side_adaptor_heat_no,
                    detail.da_side_end_plate_heat_no,
                    detail.spring_side_end_plate_heat_no,
                ]

                if any(v in ["", None] for v in required):
                    messages.error(request, "All heat numbers required!")
                    return redirect("assembler_order_details", order_no=order_no)

                detail.assembler_status = "completed"
                detail.save()

                messages.success(request, "Actuator marked completed.")

        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect("assembler_order_details", order_no=order_no)

    return render(request, "accounts/assembler_order_details.html", {
        "order": order,
        "actuators": actuators,
    })



# ================================================================
#   HEAT REPORT – PDF GENERATION
# ================================================================
@login_required
def generate_heat_report(request, order_no):

    order = get_object_or_404(MainActuator, order_no=order_no)
    items = OrderDetails.objects.filter(order_no=order).order_by("actuator_serial_no")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Heat_Report_{order_no}.pdf"'

    pdf = canvas.Canvas(response, pagesize=landscape(A4))
    width, height = landscape(A4)

    y = height - 1.5 * cm

    # ------------------------------
    # TITLE
    # ------------------------------
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(width / 2, y, "DELVAL FLOW CONTROLS PRIVATE LIMITED")
    y -= 1.2 * cm

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(width / 2, y, "HEAT ANNEXTURE - ACTUATOR")
    y -= 1.5 * cm

    # ------------------------------
    # TOP TABLE
    # ------------------------------
    top_data = [
        ["Item Code:", order.item_code, "Size:", f"{order.size}, {order.cylinder_size}, {order.spring_size or '-'}"],
        ["Qty:", order.order_qty, "Date:", datetime.now().strftime("%d-%m-%Y")],
        ["Customer:", order.customer, "SO Number:", order.sales_order_no],
    ]

    top_table = Table(top_data, colWidths=[3*cm, 7*cm, 3*cm, 7*cm])
    top_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 11),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))

    top_table.wrapOn(pdf, width, height)
    top_table.drawOn(pdf, 1*cm, y-3*cm)

    y -= 4*cm

    # ------------------------------
    # MAIN TABLE
    # ------------------------------
    headers = [
        "Sr No", "Actuator Serial", "Housing Heat No", "Yoke Heat No",
        "Top Cover", "DA Adaptor", "Spring Adaptor", "DA End Plate",
        "Spring End Plate", "Assembler"
    ]

    assembler = request.user.get_full_name() or request.user.username

    table_data = [headers]
    for i, a in enumerate(items, start=1):
        table_data.append([
            i,
            a.actuator_serial_no,
            a.housing_heat_no or "-",
            a.yoke_heat_no or "-",
            a.top_cover_heat_no or "-",
            a.da_side_adaptor_plate_heat_no or "-",
            a.spring_side_adaptor_heat_no or "-",
            a.da_side_end_plate_heat_no or "-",
            a.spring_side_end_plate_heat_no or "-",
            assembler
        ])

    table = Table(table_data, repeatRows=1, colWidths=[1.5*cm] + [3*cm]*9)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))

    table.wrapOn(pdf, width, height)

    # Auto calculate table height
    table_height = len(table_data) * 0.7 * cm

    table.drawOn(pdf, 1*cm, y - table_height)

    pdf.showPage()
    pdf.save()

    return response


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