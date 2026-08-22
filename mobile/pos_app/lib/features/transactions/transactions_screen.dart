import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../ui/format.dart';
import '../../ui/widgets.dart';
import '../pos/cart_controller.dart';

class TransactionsScreen extends ConsumerStatefulWidget {
  const TransactionsScreen({super.key});

  @override
  ConsumerState<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends ConsumerState<TransactionsScreen> {
  String _status = 'held';
  List<dynamic> _sales = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _sales = await ref.read(apiProvider).sales(status: _status);
    } catch (_) {
      _sales = const [];
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  StatusTone _tone(String status) {
    return switch (status) {
      'completed' => StatusTone.good,
      'held' => StatusTone.warn,
      'void' => StatusTone.bad,
      _ => StatusTone.neutral,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Orders')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
            child: SegmentedButton<String>(
              showSelectedIcon: false,
              style: ButtonStyle(
                visualDensity: VisualDensity.compact,
                backgroundColor: WidgetStateProperty.resolveWith((states) {
                  return states.contains(WidgetState.selected) ? accentSoft : Colors.white;
                }),
              ),
              segments: const [
                ButtonSegment(value: 'held', label: Text('Held')),
                ButtonSegment(value: 'completed', label: Text('Done')),
                ButtonSegment(value: 'void', label: Text('Void')),
              ],
              selected: {_status},
              onSelectionChanged: (value) {
                _status = value.first;
                _load();
              },
            ),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _sales.isEmpty
                    ? EmptyState(
                        icon: Icons.receipt_long_outlined,
                        title: 'No ${_status == 'completed' ? 'completed' : _status} orders',
                        detail: 'Held tickets and completed sales show up here.',
                      )
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.separated(
                          padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
                          itemCount: _sales.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (context, index) {
                            final sale = _sales[index] as Map;
                            final status = '${sale['status']}';
                            return PosCard(
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          sale['transaction_number'] as String? ?? 'Order',
                                          style: const TextStyle(fontWeight: FontWeight.w800, color: ink),
                                        ),
                                        const SizedBox(height: 4),
                                        MoneyText(sale['net_amount'], size: 16, color: accent),
                                      ],
                                    ),
                                  ),
                                  StatusPill(label: status, tone: _tone(status)),
                                  if (_status == 'held') ...[
                                    const SizedBox(width: 8),
                                    FilledButton(
                                      onPressed: () async {
                                        final detail = await ref.read(apiProvider).sale(sale['id'] as int);
                                        final lines = [
                                          for (final raw in (detail['items'] as List<dynamic>? ?? const []))
                                            CartLine(
                                              product: {
                                                'id': raw['product_id'],
                                                'name': raw['name'],
                                                'selling_price': raw['unit_price'],
                                                'sku': raw['sku'],
                                              },
                                              qty: asMoney(raw['quantity']).round(),
                                            ),
                                        ];
                                        ref.read(cartProvider.notifier).loadHeld(sale['id'] as int, lines);
                                        if (context.mounted) context.push('/cart');
                                      },
                                      style: FilledButton.styleFrom(minimumSize: const Size(88, 40)),
                                      child: const Text('Resume'),
                                    ),
                                  ] else if (_status == 'completed') ...[
                                    IconButton(
                                      tooltip: 'Refund',
                                      onPressed: () => context.push('/refund/${sale['id']}'),
                                      icon: const Icon(Icons.replay, color: accent),
                                    ),
                                    IconButton(
                                      onPressed: () => context.push('/receipt/${sale['id']}'),
                                      icon: const Icon(Icons.chevron_right, color: muted),
                                    ),
                                  ] else
                                    IconButton(
                                      onPressed: () => context.push('/receipt/${sale['id']}'),
                                      icon: const Icon(Icons.chevron_right, color: muted),
                                    ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}
