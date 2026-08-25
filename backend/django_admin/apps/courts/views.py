from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.branches.models import Branch
from apps.courts.forms import BookingForm, BookingRefundForm, CourtForm, CourtRateForm
from apps.courts.models import Booking, Court, CourtRate
from core.domain.exceptions import DomainError
from core.services.booking_service import BookingService


def _page(page_name: str, title: str, subtitle: str, extra: dict | None = None) -> dict:
    context = {
        "page_name": page_name,
        "page_title": title,
        "page_subtitle": subtitle,
        "report_date": date.today(),
    }
    if extra:
        context.update(extra)
    return context


def _working_branch(request: HttpRequest) -> Branch | None:
    if request.user.branch_id:
        return request.user.branch
    return Branch.objects.filter(is_active=True).first()


def _lock_branch(request: HttpRequest) -> bool:
    return bool(request.user.branch_id)


def _is_partial(request: HttpRequest) -> bool:
    return request.GET.get("partial") == "1" or request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _form_response(request, form, *, title: str, action_url: str, list_url: str, page_name: str, status: int = 200):
    context = {
        "form": form,
        "modal_title": title,
        "action_url": action_url,
        "list_url": list_url,
    }
    if _is_partial(request):
        return render(request, "console/partials/catalog_form.html", context, status=status)
    context.update(_page(page_name, title, title))
    context["form_partial"] = "console/partials/catalog_form.html"
    return render(request, "console/catalog_form.html", context, status=status)


def _saved(request, list_name: str, message: str) -> HttpResponse:
    messages.success(request, message)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse(list_name)
        return response
    return redirect(list_name)


@login_required
def court_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    courts = Court.objects.select_related("branch")
    if branch:
        courts = courts.filter(branch=branch)
    return render(
        request,
        "console/court_list.html",
        _page(
            "courts",
            "Courts",
            "Court status and configuration",
            {"courts": courts, "create_url": reverse("courts:court_create")},
        ),
    )


@login_required
def court_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = CourtForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        court = form.save(commit=False)
        if _lock_branch(request):
            court.branch = request.user.branch
        court.save()
        return _saved(request, "courts:court_list", f"Court “{court.name}” created.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("courts:court_list") + "?modal=create")
    return _form_response(
        request,
        form,
        title="New court",
        action_url=reverse("courts:court_create"),
        list_url=reverse("courts:court_list"),
        page_name="courts",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def court_edit(request: HttpRequest, pk: int) -> HttpResponse:
    court = get_object_or_404(Court, pk=pk)
    form = CourtForm(request.POST or None, instance=court, branch=court.branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if _lock_branch(request):
            saved.branch = request.user.branch
        saved.save()
        return _saved(request, "courts:court_list", f"Court “{saved.name}” updated.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("courts:court_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        form,
        title=f"Edit {court.name}",
        action_url=reverse("courts:court_edit", args=[pk]),
        list_url=reverse("courts:court_list"),
        page_name="courts",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def rate_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    rates = CourtRate.objects.select_related("court", "court__branch")
    if branch:
        rates = rates.filter(court__branch=branch)
    return render(
        request,
        "console/court_rate_list.html",
        _page(
            "court_rates",
            "Rates & Pricing",
            "Hourly rates and weekday overrides",
            {"rates": rates, "create_url": reverse("courts:rate_create")},
        ),
    )


@login_required
def rate_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = CourtRateForm(request.POST or None, branch=branch)
    if request.method == "POST" and form.is_valid():
        rate = form.save()
        return _saved(request, "courts:rate_list", f"Rate saved for {rate.court}.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("courts:rate_list") + "?modal=create")
    return _form_response(
        request,
        form,
        title="New weekday rate",
        action_url=reverse("courts:rate_create"),
        list_url=reverse("courts:rate_list"),
        page_name="court_rates",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def rate_edit(request: HttpRequest, pk: int) -> HttpResponse:
    rates = CourtRate.objects.select_related("court", "court__branch")
    branch = _working_branch(request)
    if branch:
        rates = rates.filter(court__branch=branch)
    rate = get_object_or_404(rates, pk=pk)
    form = CourtRateForm(request.POST or None, instance=rate, branch=rate.court.branch)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        return _saved(request, "courts:rate_list", f"Rate updated for {saved.court}.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("courts:rate_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        form,
        title=f"Edit {rate.court.name} · {rate.get_weekday_display()}",
        action_url=reverse("courts:rate_edit", args=[pk]),
        list_url=reverse("courts:rate_list"),
        page_name="court_rates",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def booking_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    day = request.GET.get("date")
    try:
        on_date = date.fromisoformat(day) if day else timezone.localdate()
    except ValueError:
        on_date = timezone.localdate()
    bookings = BookingService().list_bookings(branch_id=branch.id if branch else None, on_date=on_date, include_cancelled=True)
    return render(
        request,
        "console/booking_list.html",
        _page(
            "bookings",
            "Bookings",
            "Reservations and walk-in court time",
            {
                "bookings": bookings,
                "on_date": on_date.isoformat(),
                "create_url": reverse("courts:booking_create"),
            },
        ),
    )


@login_required
def booking_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = BookingForm(request.POST or None, branch=branch)
    if request.method == "POST" and form.is_valid():
        try:
            booking = BookingService().create_booking(
                court_id=form.cleaned_data["court"].id,
                booked_by_id=request.user.id,
                start_at=form.cleaned_data["start_at"],
                end_at=form.cleaned_data["end_at"],
                customer_id=form.cleaned_data["customer"].id if form.cleaned_data["customer"] else None,
                payment_method=form.cleaned_data["payment_method"],
                notes=form.cleaned_data["notes"],
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            return _saved(request, "courts:booking_list", f"Booking {booking.booking_number} confirmed.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("courts:booking_list") + "?modal=create")
    return _form_response(
        request,
        form,
        title="New booking",
        action_url=reverse("courts:booking_create"),
        list_url=reverse("courts:booking_list"),
        page_name="bookings",
        status=422 if request.method == "POST" else 200,
    )


@login_required
@require_POST
def booking_cancel(request: HttpRequest, pk: int) -> HttpResponse:
    booking = get_object_or_404(Booking, pk=pk)
    try:
        BookingService().cancel_booking(booking_id=booking.id, booked_by_id=request.user.id)
    except DomainError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"Booking {booking.booking_number} cancelled.")
    return redirect("courts:booking_list")


@login_required
def booking_refund(request: HttpRequest, pk: int) -> HttpResponse:
    booking = get_object_or_404(Booking.objects.select_related("court"), pk=pk)
    form = BookingRefundForm(request.POST or None, initial={"method": booking.payment_method or "cash"})
    if request.method == "POST" and form.is_valid():
        try:
            refund = BookingService().refund_booking(
                booking_id=booking.id,
                refunded_by_id=request.user.id,
                method=form.cleaned_data["method"],
                reason=form.cleaned_data["reason"],
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            return _saved(request, "courts:booking_list", f"Refunded {refund.refund_number} for {booking.booking_number}.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("courts:booking_list") + f"?modal=refund&id={pk}")
    return _form_response(
        request,
        form,
        title=f"Refund {booking.booking_number} · ₱ {booking.amount}",
        action_url=reverse("courts:booking_refund", args=[pk]),
        list_url=reverse("courts:booking_list"),
        page_name="bookings",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def court_schedule(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    day = request.GET.get("date")
    try:
        on_date = date.fromisoformat(day) if day else timezone.localdate()
    except ValueError:
        on_date = timezone.localdate()
    courts = BookingService().list_courts(branch_id=branch.id if branch else None)
    bookings = list(BookingService().list_bookings(branch_id=branch.id if branch else None, on_date=on_date))
    hours = list(range(8, 22))
    rows = []
    for court in courts:
        slots = []
        for hour in hours:
            start = timezone.make_aware(datetime.combine(on_date, time(hour, 0)))
            end = start + timedelta(hours=1)
            hit = next((b for b in bookings if b.court_id == court.id and b.start_at < end and b.end_at > start), None)
            slots.append({"hour": hour, "label": f"{hour:02d}:00", "booking": hit})
        rows.append({"court": court, "slots": slots})
    return render(
        request,
        "console/court_schedule.html",
        _page(
            "court_schedule",
            "Court Schedule",
            "Daily occupancy and availability",
            {"rows": rows, "hours": hours, "on_date": on_date.isoformat()},
        ),
    )
