import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../ui/format.dart';
import '../../ui/widgets.dart';
import 'cart_controller.dart';

class CartScreen extends ConsumerStatefulWidget {
  const CartScreen({super.key});

  @override
  ConsumerState<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends ConsumerState<CartScreen> {
  Map<String, dynamic>? _quote;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _refreshQuote();
  }

  Future<void> _refreshQuote() async {
    final items = ref.read(cartProvider.notifier).items;
    if (items.isEmpty) {
      setState(() => _quote = null);
      return;
    }
    try {
      final quote = await ref.read(apiProvider).quote(items);
      if (mounted) setState(() => _quote = quote);
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not refresh totals.');
    }
  }

  Future<void> _hold() async {
    final session = ref.read(sessionProvider);
    if (session.shiftId == null) {
      setState(() => _error = 'Open a shift first.');
      return;
    }
    setState(() => _busy = true);
    try {
      final api = ref.read(apiProvider);
      await api.createSale(
        shiftId: session.shiftId!,
        items: ref.read(cartProvider.notifier).items,
        payments: const [],
        clientSaleUuid: api.newSaleUuid(),
        deviceId: session.deviceId,
        hold: true,
      );
      ref.read(cartProvider.notifier).clear();
      if (mounted) context.go('/tickets');
    } catch (_) {
      setState(() => _error = 'Could not hold this order.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = ref.watch(cartProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Cart'),
        actions: [
          if (cart.isNotEmpty)
            IconButton(
              onPressed: () {
                ref.read(cartProvider.notifier).clear();
                context.pop();
              },
              icon: const Icon(Icons.delete_outline),
            ),
        ],
      ),
      body: cart.isEmpty
          ? const EmptyState(icon: Icons.shopping_bag_outlined, title: 'Cart is empty', detail: 'Add items from the catalog.')
          : Column(
              children: [
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                    itemCount: cart.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final line = cart[index];
                      return PosCard(
                        child: Row(
                          children: [
                            ProductThumb(name: line.name, imageUrl: line.imageUrl, seed: line.id, size: 56),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(line.name, style: const TextStyle(fontWeight: FontWeight.w800)),
                                  const SizedBox(height: 2),
                                  MoneyText(line.price, size: 13, color: muted, weight: FontWeight.w600),
                                  const SizedBox(height: 8),
                                  QtyStepper(
                                    qty: line.qty,
                                    onMinus: () {
                                      ref.read(cartProvider.notifier).remove(line.id);
                                      _refreshQuote();
                                    },
                                    onPlus: () {
                                      ref.read(cartProvider.notifier).add(line.product);
                                      _refreshQuote();
                                    },
                                  ),
                                ],
                              ),
                            ),
                            MoneyText(asMoney(line.price) * line.qty, size: 16),
                          ],
                        ),
                      );
                    },
                  ),
                ),
                Container(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                  decoration: const BoxDecoration(
                    color: Colors.white,
                    border: Border(top: BorderSide(color: line)),
                  ),
                  child: SafeArea(
                    top: false,
                    child: Column(
                      children: [
                        _row('Discount', _quote?['discount_amount'] ?? 0, color: accent),
                        const SizedBox(height: 6),
                        _row('Subtotal', _quote?['gross_amount']),
                        if (_quote?['vat_registered'] != false) ...[
                          const SizedBox(height: 6),
                          _row('VAT (12%)', _quote?['tax_amount']),
                        ],
                        const SizedBox(height: 10),
                        _row('Total', _quote?['net_amount'], emphasize: true),
                        if (_error != null) ...[
                          const SizedBox(height: 8),
                          Text(_error!, style: const TextStyle(color: red, fontWeight: FontWeight.w600)),
                        ],
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: _busy ? null : _hold,
                                child: const Text('Hold order'),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: FilledButton(
                                onPressed: _busy ? null : () => context.push('/pay'),
                                child: const Text('Checkout'),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _row(String label, dynamic value, {bool emphasize = false, Color? color}) {
    return Row(
      children: [
        Text(label, style: TextStyle(color: muted, fontWeight: emphasize ? FontWeight.w800 : FontWeight.w600)),
        const Spacer(),
        MoneyText(value, size: emphasize ? 22 : 15, color: color ?? ink),
      ],
    );
  }
}
