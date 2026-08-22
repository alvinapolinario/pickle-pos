import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/theme.dart';
import '../../core/customers/customer.dart';
import '../../core/network/api_client.dart';
import '../../ui/format.dart';
import '../../ui/widgets.dart';
import '../customers/customer_picker.dart';

class BookingsScreen extends ConsumerStatefulWidget {
  const BookingsScreen({super.key});

  @override
  ConsumerState<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends ConsumerState<BookingsScreen> {
  int _day = 0;
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _courts = const [];
  List<Map<String, dynamic>> _bookings = const [];

  List<DateTime> get _days => List.generate(7, (index) => DateTime.now().add(Duration(days: index)));

  DateTime get _selectedDay {
    final day = _days[_day];
    return DateTime(day.year, day.month, day.day);
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiProvider);
      final courts = await api.courts();
      final bookings = await api.bookings(date: _selectedDay);
      if (!mounted) return;
      setState(() {
        _courts = courts.map((row) => Map<String, dynamic>.from(row as Map)).toList();
        _bookings = bookings.map((row) => Map<String, dynamic>.from(row as Map)).toList();
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = 'Could not load courts. Check the API connection.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<Map<String, dynamic>> _bookingsFor(int courtId) {
    final rows = _bookings.where((booking) {
      if (booking['court_id'] != courtId) return false;
      if (booking['status'] == 'cancelled') return false;
      return _bookingStart(booking) != null && _bookingEnd(booking) != null;
    }).toList();
    rows.sort((a, b) => _bookingStart(a)!.compareTo(_bookingStart(b)!));
    return rows;
  }

  String _apiMessage(Object error) {
    if (error is DioException) {
      final detail = error.response?.data;
      if (detail is Map && detail['detail'] != null) return '${detail['detail']}';
    }
    return 'Could not save that booking.';
  }

  Future<void> _openExisting(Map<String, dynamic> court, Map<String, dynamic> booking) async {
    final start = _bookingStart(booking);
    final end = _bookingEnd(booking);
    final paid = booking['payment_status'] == 'paid';
    final action = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) => _BookingSheet(
        title: '${court['name']}',
        subtitle: '${_rangeLabel(start, end)} · ${booking['booking_number']}',
        amount: booking['amount'],
        actionLabel: paid ? 'Refund & cancel' : 'Cancel booking',
        destructive: true,
      ),
    );
    if (action == null) return;
    try {
      if (action == 'refund') {
        await ref.read(apiProvider).refundBooking(booking['id'] as int, method: '${booking['payment_method'] ?? 'cash'}');
      } else {
        await ref.read(apiProvider).cancelBooking(booking['id'] as int);
      }
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_apiMessage(error))));
      }
    }
  }

  Future<void> _openNew(Map<String, dynamic> court) async {
    if (court['status'] == 'maintenance') {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('This court is under maintenance.')));
      return;
    }
    final start = _suggestedStart();
    final result = await showModalBottomSheet<_NewBookingResult>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => _NewBookingSheet(
        court: court,
        day: _selectedDay,
        initialStart: start,
        existing: _bookingsFor(court['id'] as int),
      ),
    );
    if (result == null) return;
    try {
      await ref.read(apiProvider).createBooking(
            courtId: court['id'] as int,
            startAt: result.start,
            endAt: result.end,
            paymentMethod: result.method,
            customerId: result.customer?.id,
          );
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_apiMessage(error))));
      }
    }
  }

  DateTime _suggestedStart() {
    final now = DateTime.now();
    final day = _selectedDay;
    if (day.year == now.year && day.month == now.month && day.day == now.day) {
      final rounded = now.add(const Duration(minutes: 1));
      final minute = ((rounded.minute + 4) ~/ 5) * 5;
      final overflow = minute >= 60;
      return DateTime(day.year, day.month, day.day, overflow ? rounded.hour + 1 : rounded.hour, overflow ? 0 : minute);
    }
    return DateTime(day.year, day.month, day.day, 8);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Court booking')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            SizedBox(
              height: 74,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _days.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, index) {
                  final day = _days[index];
                  final selected = index == _day;
                  return GestureDetector(
                    onTap: () {
                      setState(() => _day = index);
                      _load();
                    },
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      width: 64,
                      decoration: BoxDecoration(
                        color: selected ? accent : Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: selected ? accent : line),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            DateFormat.E().format(day).toUpperCase(),
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              color: selected ? Colors.white70 : muted,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${day.day}',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.w800,
                              color: selected ? Colors.white : ink,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 12),
            if (_error != null) SoftBanner(message: _error!, tone: StatusTone.bad, margin: EdgeInsets.zero),
            if (_loading) const Padding(padding: EdgeInsets.symmetric(vertical: 24), child: Center(child: CircularProgressIndicator())),
            if (!_loading && _courts.isEmpty && _error == null)
              const SoftBanner(message: 'No courts yet. Seed courts in the console.', tone: StatusTone.info, margin: EdgeInsets.zero),
            if (!_loading)
              for (final court in _courts) ...[
                Builder(
                  builder: (context) {
                    final booked = _bookingsFor(court['id'] as int);
                    return PosCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text('${court['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                          ),
                          StatusPill(
                            label: court['status'] == 'maintenance' ? 'Maintenance' : peso(court['hourly_rate']),
                            tone: court['status'] == 'maintenance' ? StatusTone.warn : StatusTone.good,
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      ...booked.map((booking) {
                        final start = _bookingStart(booking);
                        final end = _bookingEnd(booking);
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Material(
                            color: accentSoft,
                            borderRadius: BorderRadius.circular(12),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(12),
                              onTap: () => _openExisting(court, booking),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        '${_rangeLabel(start, end)} · ${booking['booking_number']}',
                                        style: const TextStyle(fontWeight: FontWeight.w700, color: accent),
                                      ),
                                    ),
                                    const Icon(Icons.chevron_right, color: accent, size: 18),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        );
                      }),
                      if (booked.isEmpty)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Text(
                            court['status'] == 'maintenance' ? 'Closed for maintenance' : 'No bookings yet',
                            style: const TextStyle(color: muted, fontWeight: FontWeight.w600),
                          ),
                        ),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.tonal(
                          onPressed: court['status'] == 'maintenance' ? null : () => _openNew(court),
                          child: const Text('New booking'),
                        ),
                      ),
                    ],
                  ),
                );
                  },
                ),
                const SizedBox(height: 10),
              ],
          ],
        ),
      ),
    );
  }
}

class _NewBookingResult {
  const _NewBookingResult({required this.method, required this.start, required this.end, this.customer});

  final String method;
  final DateTime start;
  final DateTime end;
  final PosCustomer? customer;
}

class _NewBookingSheet extends ConsumerStatefulWidget {
  const _NewBookingSheet({
    required this.court,
    required this.day,
    required this.initialStart,
    required this.existing,
  });

  final Map<String, dynamic> court;
  final DateTime day;
  final DateTime initialStart;
  final List<Map<String, dynamic>> existing;

  @override
  ConsumerState<_NewBookingSheet> createState() => _NewBookingSheetState();
}

class _NewBookingSheetState extends ConsumerState<_NewBookingSheet> {
  static const _durations = [30, 60, 90, 120];

  late DateTime _start;
  late DateTime _end;
  PosCustomer? _customer;
  Map<String, dynamic>? _quote;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _start = widget.initialStart;
    _end = _start.add(const Duration(hours: 1));
    _refreshQuote();
  }

  Duration get _duration => _end.difference(_start);

  bool get _overlaps {
    for (final booking in widget.existing) {
      final from = _bookingStart(booking);
      final to = _bookingEnd(booking);
      if (from == null || to == null) continue;
      if (from.isBefore(_end) && to.isAfter(_start)) return true;
    }
    return false;
  }

  Future<void> _pickStart() async {
    final picked = await _pickTime(_start);
    if (picked == null) return;
    final next = _onDay(picked);
    final length = _duration.inMinutes <= 0 ? 60 : _duration.inMinutes;
    setState(() {
      _start = next;
      _end = next.add(Duration(minutes: length));
    });
    await _refreshQuote();
  }

  Future<void> _pickEnd() async {
    final picked = await _pickTime(_end);
    if (picked == null) return;
    setState(() => _end = _onDay(picked));
    await _refreshQuote();
  }

  Future<void> _setDuration(int minutes) async {
    setState(() => _end = _start.add(Duration(minutes: minutes)));
    await _refreshQuote();
  }

  DateTime _onDay(TimeOfDay time) {
    return DateTime(widget.day.year, widget.day.month, widget.day.day, time.hour, time.minute);
  }

  Future<TimeOfDay?> _pickTime(DateTime current) {
    return showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(current),
      helpText: 'Choose any time',
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: false),
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
  }

  Future<void> _refreshQuote() async {
    if (!_end.isAfter(_start)) {
      setState(() {
        _quote = null;
        _error = 'End time must be after start time.';
        _loading = false;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final quote = await ref.read(apiProvider).quoteBooking(
            courtId: widget.court['id'] as int,
            startAt: _start,
            endAt: _end,
            customerId: _customer?.id,
          );
      if (!mounted) return;
      setState(() => _quote = quote);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error is DioException ? '${error.response?.data ?? error.message}' : 'Could not quote this time.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final canBook = !_loading && _quote != null && _end.isAfter(_start) && !_overlaps;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(20, 8, 20, 16 + MediaQuery.viewInsetsOf(context).bottom),
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.78),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('${widget.court['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20, color: ink)),
                const SizedBox(height: 4),
                Text(
                  '${DateFormat.EEEE().format(_start)} · ${_durationLabel(_start, _end)}',
                  style: const TextStyle(color: muted, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(child: _TimeField(label: 'Start', value: DateFormat.jm().format(_start), onTap: _pickStart)),
                    const SizedBox(width: 8),
                    Expanded(child: _TimeField(label: 'End', value: DateFormat.jm().format(_end), onTap: _pickEnd)),
                  ],
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final minutes in _durations)
                      ChoiceChip(
                        label: Text(_chipLabel(minutes)),
                        selected: _duration.inMinutes == minutes,
                        onSelected: (_) => _setDuration(minutes),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                Material(
                  color: canvas,
                  borderRadius: BorderRadius.circular(14),
                  child: ListTile(
                    onTap: () async {
                      final picked = await showCustomerPicker(context, selected: _customer, applyGlobally: false);
                      if (picked == null) return;
                      setState(() => _customer = picked.customer);
                      await _refreshQuote();
                    },
                    leading: Icon(_customer == null ? Icons.person_outline : Icons.person, color: accent),
                    title: Text(_customer?.name ?? 'Walk-in', style: const TextStyle(fontWeight: FontWeight.w800)),
                    subtitle: Text(
                      _customer?.courtLabel ?? 'Regular court rate',
                      style: const TextStyle(color: muted),
                    ),
                    trailing: const Icon(Icons.chevron_right, color: muted),
                  ),
                ),
                const SizedBox(height: 12),
                if (_overlaps)
                  const SoftBanner(
                    message: 'That time overlaps an existing booking.',
                    tone: StatusTone.bad,
                    margin: EdgeInsets.zero,
                  )
                else if (_loading)
                  const Padding(padding: EdgeInsets.symmetric(vertical: 16), child: Center(child: CircularProgressIndicator()))
                else if (_error != null)
                  Text(_error!, style: const TextStyle(color: red, fontWeight: FontWeight.w600))
                else ...[
                  MoneyText(_quote?['amount'], size: 28),
                  if (_customer?.isMember == true) ...[
                    const SizedBox(height: 4),
                    Text(_customer!.courtLabel, style: const TextStyle(color: accent, fontWeight: FontWeight.w700)),
                  ],
                ],
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: canBook ? () => Navigator.pop(context, _NewBookingResult(method: 'cash', start: _start, end: _end, customer: _customer)) : null,
                  child: const Text('Book · Cash'),
                ),
                const SizedBox(height: 8),
                OutlinedButton(
                  onPressed: canBook ? () => Navigator.pop(context, _NewBookingResult(method: 'gcash', start: _start, end: _end, customer: _customer)) : null,
                  child: const Text('Book · GCash'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TimeField extends StatelessWidget {
  const _TimeField({required this.label, required this.value, required this.onTap});

  final String label;
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: canvas,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label.toUpperCase(), style: const TextStyle(color: muted, fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 0.7)),
              const SizedBox(height: 4),
              Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: ink)),
            ],
          ),
        ),
      ),
    );
  }
}

class _BookingSheet extends StatelessWidget {
  const _BookingSheet({
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    this.amount,
    this.destructive = false,
  });

  final String title;
  final String subtitle;
  final dynamic amount;
  final String actionLabel;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20, color: ink)),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(color: muted, fontWeight: FontWeight.w600)),
          if (amount != null) ...[
            const SizedBox(height: 12),
            MoneyText(amount, size: 28),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () => Navigator.pop(context, destructive ? (actionLabel.startsWith('Refund') ? 'refund' : 'cancel') : 'cash'),
            style: destructive ? FilledButton.styleFrom(backgroundColor: red) : null,
            child: Text(actionLabel),
          ),
        ],
      ),
    );
  }
}

DateTime? _bookingStart(Map<String, dynamic> booking) => DateTime.tryParse('${booking['start_at']}')?.toLocal();

DateTime? _bookingEnd(Map<String, dynamic> booking) => DateTime.tryParse('${booking['end_at']}')?.toLocal();

String _rangeLabel(DateTime? start, DateTime? end) {
  if (start == null || end == null) return 'Open time';
  return '${DateFormat.jm().format(start)} – ${DateFormat.jm().format(end)}';
}

String _durationLabel(DateTime start, DateTime end) {
  final minutes = end.difference(start).inMinutes;
  if (minutes <= 0) return 'Choose end time';
  if (minutes < 60) return '$minutes min';
  if (minutes % 60 == 0) {
    final hours = minutes ~/ 60;
    return hours == 1 ? '1 hour' : '$hours hours';
  }
  return '${minutes ~/ 60}h ${minutes % 60}m';
}

String _chipLabel(int minutes) {
  if (minutes < 60) return '$minutes min';
  if (minutes % 60 == 0) return minutes == 60 ? '1 hour' : '${minutes ~/ 60} hours';
  return '${minutes ~/ 60}h ${minutes % 60}m';
}
