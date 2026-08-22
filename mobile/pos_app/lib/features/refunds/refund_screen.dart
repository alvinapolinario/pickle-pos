import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../ui/format.dart';
import '../../ui/widgets.dart';

class RefundScreen extends ConsumerStatefulWidget {
  const RefundScreen({super.key, required this.saleId});

  final int saleId;

  @override
  ConsumerState<RefundScreen> createState() => _RefundScreenState();
}

class _RefundScreenState extends ConsumerState<RefundScreen> {
  Map<String, dynamic>? _sale;
  final Map<int, int> _qty = {};
  String _method = 'cash';
  final _reason = TextEditingController();
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final sale = await ref.read(apiProvider).sale(widget.saleId);
      final items = (sale['items'] as List<dynamic>? ?? const []).cast<dynamic>();
      setState(() {
        _sale = sale;
        for (final item in items) {
          final row = item as Map;
          _qty[row['id'] as int] = 0;
        }
      });
    } catch (_) {
      setState(() => _error = 'Could not load this sale.');
    }
  }

  int _refundable(Map item) {
    return asMoney(item['quantity_refundable'] ?? item['quantity']).round();
  }

  Future<void> _submit() async {
    final session = ref.read(sessionProvider);
    if (session.shiftId == null) {
      setState(() => _error = 'Open a shift before refunding.');
      return;
    }
    final lines = [
      for (final entry in _qty.entries)
        if (entry.value > 0) {'sale_item_id': entry.key, 'quantity': '${entry.value}'},
    ];
    if (lines.isEmpty) {
      setState(() => _error = 'Choose at least one item to refund.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(apiProvider).refundSale(
            saleId: widget.saleId,
            shiftId: session.shiftId!,
            lines: lines,
            method: _method,
            reason: _reason.text.trim(),
          );
      if (mounted) context.go('/tickets');
    } catch (_) {
      setState(() => _error = 'Refund failed. Check remaining quantities and shift.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sale = _sale;
    final items = (sale?['items'] as List<dynamic>? ?? const []).cast<dynamic>();
    return Scaffold(
      appBar: AppBar(title: const Text('Refund')),
      body: sale == null
          ? Center(child: _error == null ? const CircularProgressIndicator() : Text(_error!, style: const TextStyle(color: red)))
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
              children: [
                Text(sale['transaction_number'] as String? ?? 'Sale', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
                MoneyText(sale['net_amount'], size: 16, color: accent),
                const SizedBox(height: 16),
                const SectionLabel('Items'),
                const SizedBox(height: 8),
                for (final raw in items)
                  Builder(
                    builder: (context) {
                      final item = raw as Map;
                      final id = item['id'] as int;
                      final maxQty = _refundable(item);
                      final current = _qty[id] ?? 0;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: PosCard(
                          child: Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('${item['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                                    Text('Refundable $maxQty · ${peso(item['line_net'])}', style: const TextStyle(color: muted, fontWeight: FontWeight.w600)),
                                  ],
                                ),
                              ),
                              QtyStepper(
                                qty: current,
                                onMinus: () {
                                  if (current > 0) setState(() => _qty[id] = current - 1);
                                },
                                onPlus: () {
                                  if (current < maxQty) setState(() => _qty[id] = current + 1);
                                },
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                const SizedBox(height: 8),
                const SectionLabel('Refund method'),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: _method,
                  items: const [
                    DropdownMenuItem(value: 'cash', child: Text('Cash')),
                    DropdownMenuItem(value: 'gcash', child: Text('GCash')),
                    DropdownMenuItem(value: 'maya', child: Text('Maya')),
                    DropdownMenuItem(value: 'bank_transfer', child: Text('Bank transfer')),
                  ],
                  onChanged: (value) => setState(() => _method = value ?? 'cash'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _reason,
                  decoration: const InputDecoration(labelText: 'Reason (optional)'),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: red, fontWeight: FontWeight.w600)),
                ],
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _busy ? null : _submit,
                  child: Text(_busy ? 'Refunding…' : 'Complete refund'),
                ),
              ],
            ),
    );
  }
}
