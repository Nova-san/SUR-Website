import io

from datetime import date, timedelta, datetime
import xlsxwriter

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .forms import (
    RunnerRegistrationForm,
    RunnerExportForm,
    EventForm,
    DistanceForm,
    EventSelectForm,
)
from .models import Event, Distance, Runner


# =========================
# Public Views
# =========================

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        if self.request.user.is_staff:
            return '/dashboard/'
        return '/'

def home(request):
    today = date.today()
    events = Event.objects.filter(date__gte=today).order_by('date')

    # Prefetch only if events exist
    if events.exists():
        events = events.prefetch_related('distances')

    return render(request, 'registration/home.html', {
        'events': events
    })


def register_runner(request):
    if request.method == 'POST':
        form = RunnerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            runner = form.save()

            # 🔔 Send confirmation email (plain text)
            EmailMessage(
                subject="✅ SUR Registration Received",
                body=(
                    f"{runner.full_name}\n\n"
                    f"Thanks for registering for:\n\n"
                    f"🏁 Event: {runner.event.name}\n"
                    f"📏 Distance: {runner.distance.label} KM\n"
                    f"📅 Date: {runner.event.date.strftime('%B %d, %Y')}\n\n"
                    f"We’ll verify your proof of payment shortly.\n"
                    f"Once confirmed, you’ll get another email.\n\n"
                    f"Thanks for joining Surigao Ultra Runners!\n"
                    f"– The SUR Team 🏃‍♂️💚"
                ),
                from_email=None,  # uses settings.DEFAULT_FROM_EMAIL
                to=[runner.email]
            ).send()

    return render(request, 'registration/register.html', {'form': form})

def load_distances(request):
    try:
        event_id = int(request.GET.get('event_id'))
        distances = Distance.objects.filter(event__id=event_id).values('id', 'label', 'fee')
        print("event_id received:", event_id)
        print("distances found:", list(distances))  # ← full debug
        return JsonResponse(list(distances), safe=False)
    except (TypeError, ValueError) as e:
        print("ERROR in load_distances:", e)
        return JsonResponse([], safe=False)

# =========================
# Dashboard & Staff Views
# =========================
@staff_member_required
def dashboard(request):
    """Admin dashboard with metrics and quick links."""
    # Metrics
    event_count    = Event.objects.count()
    distance_count = Distance.objects.count()
    runner_count   = Runner.objects.count()
    unverified     = Runner.objects.filter(is_verified=False).count()
    upcoming_week  = Event.objects.filter(
                         date__gte=date.today(),
                         date__lte=date.today() + timedelta(days=7)
                     ).count()

    # Recent registrations
    recent_runners = Runner.objects.order_by('-pk')[:5]

    # Dashboard feature cards
    features = [
        {
            'name': 'New Event',
            'desc': 'Create a new race event',
            'icon': 'fa-calendar-plus',
            'url': reverse('registration:add_event'),
            'count': None
        },
        {
            'name': 'New Distance',
            'desc': 'Add a new distance/fee category',
            'icon': 'fa-route',
            'url': reverse('registration:add_distance'),
            'count': None
        },
        {
            'name': 'New Runner',
            'desc': 'Manually register a runner',
            'icon': 'fa-user-plus',
            'url': reverse('registration:manual_runner'),
            'count': None
        },
        {
            'name': 'Runners by Event',
            'desc': 'View runners by selected event',
            'icon': 'fa-list',
            'url': reverse('registration:runners_by_event'),
            'count': None
        },
        {
            'name': 'Payment Stats',
            'desc': 'View verified vs pending counts',
            'icon': 'fa-chart-pie',
            'url': reverse('registration:verification_stats'),
            'count': None
        },
        {
            'name': 'Current Events',
            'desc': 'Edit or delete upcoming races',
            'icon': 'fa-calendar-alt',
            'url': reverse('registration:current_events'),
            'count': None
        },
        {
            'name': 'Export XLSX',
            'desc': 'Download full report with images',
            'icon': 'fa-file-excel',
            'url': reverse('registration:export_xlsx'),
            'count': None
        },
        {
            'name': 'Edit Distances',
            'desc': 'Manage existing distance categories',
            'icon': 'fa-edit',
            'url': reverse('admin:registration_distance_changelist'),
            'count': None
        },
        {
            'name': 'Verify Runners',
            'desc': 'Approve pending registrations',
            'icon': 'fa-check-circle',
            'url': reverse('registration:unverified_runners'),
            'count': unverified
        }
    ]

    return render(request, 'registration/dashboard.html', {
        'features': features,
        'recent_runners': recent_runners,
        'event_count': event_count,
        'distance_count': distance_count,
        'runner_count': runner_count,
        'unverified': unverified,
        'upcoming_week': upcoming_week,
    })


@staff_member_required
def export_xlsx(request):
    """Export filtered runners to a styled XLSX file using XlsxWriter."""
    export_type = "xlsx"  # Default value for export_type

    form = RunnerExportForm(request.GET or None)
    if request.GET and form.is_valid():
        cd = form.cleaned_data
        qs = Runner.objects.select_related('event', 'distance')
        export_type = request.GET.get("export_type", export_type)

        # Move dictionary ABOVE filters
        age_map = {
            '20_below': (0, 20),
            '21_29': (21, 29),
            '30_39': (30, 39),
            '40_49': (40, 49),
            '50_59': (50, 59),
            '60_75': (60, 75),
        }

        # Apply filters
        if cd['event']:
            qs = qs.filter(event=cd['event'])
        if cd['distance']:
            qs = qs.filter(distance=cd['distance'])
        if cd['shirt_size']:
            qs = qs.filter(shirt_size=cd['shirt_size'])
        if cd['gender']:
            qs = qs.filter(gender=cd['gender'])
        if cd['is_verified'] == 'yes':
            qs = qs.filter(is_verified=True)
        elif cd['is_verified'] == 'no':
            qs = qs.filter(is_verified=False)
        if cd['age_category'] in age_map:
            low, high = age_map[cd['age_category']]
            qs = qs.filter(age__gte=low, age__lte=high)

        # Build filter summary (only what's selected)
        filter_parts = []

        if cd['event']:
            filter_parts.append(f"Event: {cd['event'].name} on {cd['event'].date}")
        if cd['distance']:
            filter_parts.append(f"Distance: {cd['distance'].label} KM")
        if cd['is_verified'] in ['yes', 'no']:
            filter_parts.append(f"Verified: {'Yes' if cd['is_verified'] == 'yes' else 'No'}")
        if cd['gender']:
            gender_display = dict(Runner.GENDER_CHOICES).get(cd['gender'], cd['gender'])
            filter_parts.append(f"Gender: {gender_display}")
        if cd['shirt_size']:
            filter_parts.append(f"Shirt Size: {cd['shirt_size']}")
        if cd['age_category']:
            category_map = dict(RunnerExportForm.AGE_CATEGORY_CHOICES)
            filter_parts.append(f"Age Category: {category_map.get(cd['age_category'], cd['age_category'])}")

        filters_text = "Filters – " + ", ".join(filter_parts) if filter_parts else "All runners (no filters applied)"

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Runners")

        # Header styles
        summary_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#004400',
            'align': 'left'
        })
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#00cc44',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        cell_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'vcenter'
        })
        bold_name_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'text_wrap': True,
            'valign': 'vcenter'
        })

        # Title & summary
        worksheet.merge_range('A1:H1', 'Surigao Ultra Runners – Exported Data', summary_format)
        worksheet.merge_range('A2:H2', filters_text, workbook.add_format({'italic': True, 'bg_color': '#002200', 'font_color': '#ccffcc'}))

        # Headers
        headers = ['Name', 'Email', 'Distance', 'Age', 'Gender', 'Shirt Size']
        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_format)

    # Data rows
    for row_num, runner in enumerate(qs, start=4):
        full_name = runner.full_name
        worksheet.write(row_num, 0, runner.full_name, bold_name_format)
    # Data rows
    for row_num, runner in enumerate(qs, start=4):
        worksheet.write(row_num, 0, runner.full_name, bold_name_format)
        worksheet.write(row_num, 1, runner.email, cell_format)
        worksheet.write(row_num, 2, runner.distance.label, cell_format)
        worksheet.write(row_num, 3, runner.age, cell_format)
        worksheet.write(row_num, 4, runner.get_gender_display(), cell_format)
        worksheet.write(row_num, 5, runner.shirt_size, cell_format)
        worksheet.set_column('C:C', 15)  # Distance
        worksheet.set_column('D:D', 6)   # Age
        worksheet.set_column('E:E', 10)  # Gender
        worksheet.set_column('F:F', 12)  # Shirt Size

        workbook.close()
        output.seek(0)

        event_name = cd['event'].name.replace(" ", "_") if cd['event'] else 'all_events'
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
        filename = f"{event_name}_runners_{timestamp}.xlsx"

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    return render(request, 'registration/export_xslx.html', {'form': form})

# =========================
# Event Management
# =========================

@staff_member_required
def add_event(request):
    """Add a new event."""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('registration:dashboard')
    else:
        form = EventForm()
    return render(request, 'registration/event_form.html', {
        'form': form,
        'title': 'New Event'
    })

@staff_member_required
def add_distance(request):
    """Add a new distance category."""
    if request.method == 'POST':
        form = DistanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('registration:dashboard')
    else:
        form = DistanceForm()
    
    return render(request, 'registration/distance_form.html', {
    'form': form,
    'title': 'New Distance',
    'km_presets': [1, 3, 5, 10, 21, 42, 50]
})


@staff_member_required
def manual_runner(request):
    """Manually register a runner (admin only)."""
    if request.method == 'POST':
        form = RunnerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('registration:dashboard')
    else:
        form = RunnerRegistrationForm()
    return render(request, 'registration/register.html', {
        'form': form,
        'manual': True
    })

# =========================
# Runner Listings & Filters
# =========================

@staff_member_required
def runners_by_event(request):
    form = EventSelectForm(request.GET or None)
    runners = None
    selected_event = None

    if request.GET and form.is_valid():
        cd = form.cleaned_data
        selected_event = cd['event']
        runner_list = Runner.objects.filter(event=selected_event)

        search_query = cd.get('search', '').strip()
        if search_query:
            runner_list = runner_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
            )

        if cd['distance']:
            runner_list = runner_list.filter(distance=cd['distance'])
        if cd['shirt_size']:
            runner_list = runner_list.filter(shirt_size=cd['shirt_size'])
        if cd['gender']:
            runner_list = runner_list.filter(gender=cd['gender'])
        if cd['is_verified'] == 'yes':
            runner_list = runner_list.filter(is_verified=True)
        elif cd['is_verified'] == 'no':
            runner_list = runner_list.filter(is_verified=False)

        age_map = {
            '20_below': (0, 20),
            '21_29': (21, 29),
            '30_39': (30, 39),
            '40_49': (40, 49),
            '50_59': (50, 59),
            '60_75': (60, 75),
        }
        if cd['age_category'] in age_map:
            low, high = age_map[cd['age_category']]
            runner_list = runner_list.filter(age__gte=low, age__lte=high)

        runner_list = runner_list.select_related('distance').order_by('last_name', 'first_name')

        # Pagination
        paginator = Paginator(runner_list, 25)
        page_number = request.GET.get('page', 1)
        try:
            runners = paginator.page(page_number)
        except PageNotAnInteger:
            runners = paginator.page(1)
        except EmptyPage:
            runners = paginator.page(paginator.num_pages)

    return render(request, 'registration/runners_by_event.html', {
        'form': form,
        'runners': runners,
        'selected_event': selected_event,
        'title': 'Runners by Event',
    })


@staff_member_required
def unverified_runners(request):
    """List unverified runners for a selected event."""
    form = EventSelectForm(request.GET or None)
    runners = None
    selected_event = None

    if request.GET and form.is_valid():
        selected_event = form.cleaned_data['event']
        runner_list = Runner.objects.filter(event=selected_event, is_verified=False).order_by('-created_at')

        paginator = Paginator(runner_list, 25)
        page = request.GET.get('page', 1)
        try:
            runners = paginator.page(page)
        except PageNotAnInteger:
            runners = paginator.page(1)
        except EmptyPage:
            runners = paginator.page(paginator.num_pages)

    return render(request, 'registration/unverified_runners.html', {
        'form': form,
        'runners': runners,
        'selected_event': selected_event,
        'title': 'Unverified Runners'
    })

@staff_member_required
def all_runners(request):
    """List all runners."""
    runners = Runner.objects.order_by('name')
    return render(request, 'registration/runners_list.html', {
        'runners': runners,
        'title':   'All Runners'
    })

# =========================
# Event Editing & Deletion
# =========================

@staff_member_required
def current_events(request):
    """List all current/upcoming events."""
    events = Event.objects.filter(date__gte=date.today()).order_by('date')
    return render(request, 'registration/current_events.html', {
        'events': events,
        'title': 'Current Events'
    })

@staff_member_required
def delete_event(request, pk):
    """Delete an event (confirmation required)."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        event.delete()
        return redirect('registration:current_events')
    return render(request, 'registration/confirm_delete.html', {
        'object': event,
        'title':  'Delete Event'
    })

@staff_member_required
def edit_event(request, pk):
    """Edit an existing event."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            return redirect('registration:current_events')
    else:
        form = EventForm(instance=event)

    return render(request, 'registration/event_form.html', {
        'form':  form,
        'title': 'Edit Event'
    })

# =========================
# Runner Editing & Deletion
# =========================

@staff_member_required
def verify_runner(request, pk):
    """Mark a runner as verified and send confirmation email."""
    runner = get_object_or_404(Runner, pk=pk)
    runner.is_verified = True
    runner.save()

    # ✅ Send verification email
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string

    subject = "✅ Your SUR Registration Is Verified!"
    to_email = [runner.email]

    text_content = (
        f"Hi {runner.full_name},\n\n"
        f"✅ You're officially verified for:\n\n"
        f"🏁 Event: {runner.event.name}\n"
        f"📏 Distance: {runner.distance.label} KM\n"
        f"📅 Date: {runner.event.date.strftime('%B %d, %Y')}\n\n"
        "You may now consider your registration confirmed.\n"
        "We’ll see you at the starting line!\n\n"
        "– The SUR Team 🏃‍♂️💚"
    )

    html_content = render_to_string("emails/verification_email.html", {
        "name": runner.full_name,
        "event": runner.event.name,
        "distance": runner.distance.label,
        "date": runner.event.date.strftime("%B %d, %Y"),
    })

    email = EmailMultiAlternatives(subject, text_content, None, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()

    return redirect('registration:unverified_runners')

@staff_member_required
def edit_runner(request, pk):
    """Edit runner details."""
    runner = get_object_or_404(Runner, pk=pk)
    if request.method == 'POST':
        form = RunnerRegistrationForm(request.POST, request.FILES, instance=runner)
        if form.is_valid():
            form.save()
            return redirect('registration:runners_by_event')
    else:
        form = RunnerRegistrationForm(instance=runner)
    return render(request, 'registration/edit_runner.html', {
        'form': form,
        'title': 'Edit Runner',
        'runner': runner
    })

@staff_member_required
def delete_runner(request, pk):
    """Delete a runner (confirmation required)."""
    runner = get_object_or_404(Runner, pk=pk)
    if request.method == 'POST':
        runner.delete()
        return redirect('registration:runners_by_event')
    return render(request, 'registration/confirm_delete.html', {
        'object': runner,
        'title': 'Delete Runner'
    })

# =========================
# Statistics & Reports
# =========================

@staff_member_required
def verification_stats(request):
    """Show verification stats (overall and per event)."""
    # Overall counts
    total      = Runner.objects.count()
    verified   = Runner.objects.filter(is_verified=True).count()
    unverified = total - verified

    # Breakdown per event
    by_event = (
        Event.objects
             .annotate(
                 total_reg=Count('runner'),
                 verified_reg=Count('runner', filter=Q(runner__is_verified=True))
             )
             .values('name', 'total_reg', 'verified_reg')
    )

    # Compute percentages in Python
    stats = []
    for ev in by_event:
        tot = ev['total_reg'] or 0
        ver = ev['verified_reg'] or 0
        pct = (ver / tot * 100) if tot else 0
        stats.append({
            'event': ev['name'],
            'total': tot,
            'verified': ver,
            'percent': f"{pct:.0f}%"
        })

    return render(request, 'registration/verification_stats.html', {
        'total': total,
        'verified': verified,
        'unverified': unverified,
        'stats': stats,
        'title': 'Payment Stats',
    })

# =========================

@staff_member_required
def list_distances(request):
    """List all distances grouped by event."""
    events = Event.objects.prefetch_related('distances').order_by('date')
    return render(request, 'registration/distances_list.html', {
        'events': events,
        'title': 'Edit Distances'
    })

@staff_member_required
def edit_distance(request, pk):
    """Edit a single distance."""
    distance = get_object_or_404(Distance, pk=pk)
    if request.method == 'POST':
        form = DistanceForm(request.POST, instance=distance)
        if form.is_valid():
            form.save()
            return redirect('registration:list_distances')
    else:
        form = DistanceForm(instance=distance)

    return render(request, 'registration/distance_form.html', {
        'form': form,
        'title': 'Edit Distance'
    })

@staff_member_required
def delete_distance(request, pk):
    """Delete a distance (with confirmation)."""
    distance = get_object_or_404(Distance, pk=pk)
    if request.method == 'POST':
        distance.delete()
        return redirect('registration:list_distances')

    return render(request, 'registration/confirm_delete.html', {
        'object': distance,
        'title': 'Delete Distance'
    })


@staff_member_required
def edit_distances(request):
    distances = Distance.objects.select_related('event').order_by('event__date', 'label')
    return render(request, 'registration/edit_distances.html', {
        'distances': distances,
        'title': 'Edit Distances'
    })

@staff_member_required
def edit_distance(request, pk):
    distance = get_object_or_404(Distance, pk=pk)
    if request.method == 'POST':
        form = DistanceForm(request.POST, instance=distance)
        if form.is_valid():
            form.save()
            return redirect('registration:edit_distances')
    else:
        form = DistanceForm(instance=distance)
    return render(request, 'registration/distance_form.html', {
        'form': form,
        'title': 'Edit Distance'
    })

@staff_member_required
def delete_distance(request, pk):
    distance = get_object_or_404(Distance, pk=pk)
    if request.method == 'POST':
        distance.delete()
        return redirect('registration:edit_distances')
    return render(request, 'registration/confirm_delete.html', {
        'object': distance,
        'title': 'Delete Distance'
    })