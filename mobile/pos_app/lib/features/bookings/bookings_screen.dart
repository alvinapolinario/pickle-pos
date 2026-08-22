import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../ui/format.dart';
import '../../ui/widgets.dart';

class BookingsScreen extends ConsumerStatefulWidget {
  const BookingsScreen({super.key});

  @override
  ConsumerState<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends ConsumerState<BookingsScreen> {
  static const _hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21];

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

  Map<String, dynamic>? _bookingAt(int courtId, DateTime start, DateTime end) {
    for (final booking in _bookings) {
      if (booking['court_id'] != courtId) continue;
      if (booking['status'] == 'cancelled') continue;
      final from = DateTime.tryParse('${booking['start_at']}')?.toLocal();
      final to = DateTime.tryParse('${booking['end_at']}')?.toLocal();
      if (from == null || to == null) continue;
      if (from.isBefore(end) && to.isAfter(start)) return booking;
    }
    return null;
  }

  String _apiMessage(Object error) {
    if (error is DioException) {
      final detail = error.response?.data;
      if (detail is Map && detail['detail'] != null) return '${detail['detail']}';
    }
    return 'Could not save that booking.';
  }

  Future<void> _bookSlot(Map<String, dynamic> court, DateTime start) async {
    if (court['status'] == 'maintenance') {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('This court is under maintenance.')));
      return;
    }
    final end = start.add(const Duration(hours: 1));
    if (end.isBefore(DateTime.now()) || end.isAtSameMomentAs(DateTime.now())) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('That slot has already ended.')));
      return;
    }
    final existing = _bookingAt(court['id'] as int, start, end);
    if (existing != null) {
      final paid = existing['payment_status'] == 'paid';
      final action = await showModalBottomSheet<String>(
        context: context,
        showDragHandle: true,
        builder: (context) => _BookingSheet(
          title: '${court['name']}',
          subtitle: '${DateFormat.jm().format(start)} · ${existing['booking_number']}',
          amount: existing['amount'],
          actionLabel: paid ? 'Refund & cancel' : 'Cancel booking',
          secondaryLabel: paid ? 'Cancel without refund' : null,
          destructive: true,
        ),
      );
      if (action == null) return;
      try {
        if (action == 'refund') {
          await ref.read(apiProvider).refundBooking(existing['id'] as int, method: '${existing['payment_method'] ?? 'cash'}');
        } else {
          await ref.read(apiProvider).cancelBooking(existing['id'] as int);
        }
        await _load();
      } catch (error) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_apiMessage(error))));
        }
      }
      return;
    }

    Map<String, dynamic>? quote;
    try {
      quote = await ref.read(apiProvider).quoteBooking(courtId: court['id'] as int, startAt: start, endAt: end);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_apiMessage(error))));
      }
      return;
    }
    if (!mounted) return;
    final method = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) => _BookingSheet(
        title: '${court['name']}',
        subtitle: '${DateFormat.EEEE().format(start)} · ${DateFormat.jm().format(start)}–${DateFormat.jm().format(end)}',
        amount: quote?['amount'],
        actionLabel: 'Book · Cash',
        secondaryLabel: 'Book · GCash',
      ),
    );
    if (method == null) return;
    try {
      await ref.read(apiProvider).createBooking(
            courtId: court['id'] as int,
            startAt: start,
            endAt: end,
            paymentMethod: method,
          );
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_apiMessage(error))));
      }
    }
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
                PosCard(
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
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final hour in _hours)
                            _SlotChip(
                              hour: hour,
                              booking: _bookingAt(
                                court['id'] as int,
                                DateTime(_selectedDay.year, _selectedDay.month, _selectedDay.day, hour),
                                DateTime(_selectedDay.year, _selectedDay.month, _selectedDay.day, hour + 1),
                              ),
                              closed: court['status'] == 'maintenance',
                              onTap: () => _bookSlot(
                                court,
                                DateTime(_selectedDay.year, _selectedDay.month, _selectedDay.day, hour),
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
              ],
          ],
        ),
      ),
    );
  }
}

class _SlotChip extends StatelessWidget {
  const _SlotChip({required this.hour, required this.onTap, this.booking, this.closed = false});

  final int hour;
  final Map<String, dynamic>? booking;
  final bool closed;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final taken = booking != null;
    final label = '${hour.toString().padLeft(2, '0')}:00';
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: taken
              ? accentSoft
              : closed
                  ? const Color(0xFFF1F5F9)
                  : Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: taken ? accent : line),
        ),
        child: Text(
          taken ? '$label · booked' : label,
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 12,
            color: taken
                ? accent
                : closed
                    ? muted
                    : ink,
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
    this.secondaryLabel,
    this.destructive = false,
  });

  final String title;
  final String subtitle;
  final dynamic amount;
  final String actionLabel;
  final String? secondaryLabel;
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
          if (secondaryLabel != null) ...[
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () => Navigator.pop(context, destructive ? 'cancel' : 'gcash'),
              child: Text(secondaryLabel!),
            ),
          ],
        ],
      ),
    );
  }
}
