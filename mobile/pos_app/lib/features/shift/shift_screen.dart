import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../ui/widgets.dart';

class ShiftScreen extends ConsumerStatefulWidget {
  const ShiftScreen({super.key});

  @override
  ConsumerState<ShiftScreen> createState() => _ShiftScreenState();
}

class _ShiftScreenState extends ConsumerState<ShiftScreen> {
  Map<String, dynamic>? _shift;
  final _cash = TextEditingController(text: '0.00');
  String? _message;
  StatusTone _tone = StatusTone.info;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _cash.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final shift = await ref.read(apiProvider).currentShift();
      await ref.read(sessionProvider.notifier).setShift(shift?['id'] as int?);
      setState(() => _shift = shift);
    } catch (_) {
      setState(() {
        _message = 'Could not load shift.';
        _tone = StatusTone.bad;
      });
    }
  }

  Future<void> _open() async {
    setState(() => _busy = true);
    try {
      final shift = await ref.read(apiProvider).openShift(_cash.text);
      await ref.read(sessionProvider.notifier).setShift(shift['id'] as int);
      setState(() {
        _shift = shift;
        _message = 'Shift opened.';
        _tone = StatusTone.good;
      });
    } catch (_) {
      setState(() {
        _message = 'Could not open shift.';
        _tone = StatusTone.bad;
      });
    } finally {
      setState(() => _busy = false);
    }
  }

  Future<void> _close() async {
    final shiftId = _shift?['id'] as int?;
    if (shiftId == null) return;
    setState(() => _busy = true);
    try {
      final closed = await ref.read(apiProvider).closeShift(shiftId, _cash.text);
      await ref.read(sessionProvider.notifier).setShift(null);
      setState(() {
        _shift = null;
        _message = 'Closed. Over/short ₱ ${closed['over_short']}';
        _tone = StatusTone.info;
      });
    } catch (_) {
      setState(() {
        _message = 'Could not close shift.';
        _tone = StatusTone.bad;
      });
    } finally {
      setState(() => _busy = false);
    }
  }

  Future<void> _cashMove(bool cashIn) async {
    final shiftId = _shift?['id'] as int?;
    if (shiftId == null) return;
    final amount = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(cashIn ? 'Cash in' : 'Cash out'),
        content: TextField(
          controller: amount,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Amount', prefixText: '₱ '),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || amount.text.trim().isEmpty) return;
    try {
      await ref.read(apiProvider).cashMove(shiftId: shiftId, amount: amount.text.trim(), cashIn: cashIn);
      await _load();
      setState(() {
        _message = cashIn ? 'Cash in recorded.' : 'Cash out recorded.';
        _tone = StatusTone.good;
      });
    } catch (_) {
      setState(() {
        _message = 'Could not record cash movement.';
        _tone = StatusTone.bad;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final open = _shift != null;
    final opened = DateTime.tryParse('${_shift?['opened_at'] ?? ''}')?.toLocal();
    return Scaffold(
      appBar: AppBar(title: const Text('Shift summary')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: open ? accent : Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: open ? null : Border.all(color: line),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  open ? 'Open shift' : 'Register closed',
                  style: TextStyle(color: open ? Colors.white : ink, fontWeight: FontWeight.w800, fontSize: 20),
                ),
                const SizedBox(height: 4),
                Text(
                  open
                      ? 'Shift #${_shift!['id']}${opened == null ? '' : ' · ${DateFormat.jm().format(opened)}'}'
                      : 'Count the drawer, then open.',
                  style: TextStyle(color: open ? Colors.white70 : muted, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
          if (open) ...[
            const SizedBox(height: 12),
            PosCard(
              child: Column(
                children: [
                  _row('Opening cash', _shift!['opening_cash']),
                  const SizedBox(height: 8),
                  _row('Expected cash', _shift!['expected_cash']),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(onPressed: () => _cashMove(true), child: const Text('Cash in')),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(onPressed: () => _cashMove(false), child: const Text('Cash out')),
                ),
              ],
            ),
          ],
          const SizedBox(height: 16),
          const SectionLabel('Cash count'),
          const SizedBox(height: 8),
          TextField(
            controller: _cash,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: open ? 'Actual cash in drawer' : 'Opening cash',
              prefixText: '₱ ',
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy ? null : (open ? _close : _open),
            style: open ? FilledButton.styleFrom(backgroundColor: navy) : null,
            child: Text(_busy ? 'Working…' : (open ? 'Close shift' : 'Open shift')),
          ),
          if (_message != null)
            SoftBanner(message: _message!, tone: _tone, margin: const EdgeInsets.only(top: 12)),
        ],
      ),
    );
  }

  Widget _row(String label, dynamic value) {
    return Row(
      children: [
        Text(label, style: const TextStyle(color: muted, fontWeight: FontWeight.w600)),
        const Spacer(),
        MoneyText(value),
      ],
    );
  }
}
