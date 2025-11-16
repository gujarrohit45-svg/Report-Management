from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import MainActuator, OrderDetails

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
                "order_no": "21002715",
                "order_qty": "10",
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
def assembler_dashboard(request):
    # Fetch OrderDetails for orders that are under_assembly
    order_details = OrderDetails.objects.filter(order_no__order_status='under_assembly').order_by('created_at')
    return render(request, 'accounts/assembler_dashboard.html', {'order_details': order_details})

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
