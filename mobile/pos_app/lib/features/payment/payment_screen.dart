import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/customers/selected_customer.dart';
import '../../core/network/api_client.dart';
import '../../ui/format.dart';
import '../../ui/widgets.dart';
import '../customers/customer_picker.dart';
import '../pos/cart_controller.dart';

class PaymentScreen extends ConsumerStatefulWidget {
  const PaymentScreen({super.key});

  @override
  ConsumerState<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends ConsumerState<PaymentScreen> {
  String _method = 'cash';
  final _amount = TextEditingController();
  Map<String, dynamic>? _quote;
  String? _error;
  bool _busy = false;

  static const _methods = [
    ('cash', 'Cash', Icons.payments_outlined),
    ('gcash', 'GCash', Icons.phone_iphone),
    ('maya', 'Maya', Icons.account_balance_wallet_outlined),
    ('other', 'Card', Icons.credit_card),
    ('bank_transfer', 'Bank transfer', Icons.account_balance_outlined),
  ];

  @override
  void initState() {
    super.initState();
    _refreshQuote();
  }

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _refreshQuote() async {
    final items = ref.read(cartProvider.notifier).items;
    if (items.isEmpty) return;
    try {
      final quote = await ref.read(apiProvider).quote(items, customerId: ref.read(selectedCustomerProvider)?.id);
      setState(() {
        _quote = quote;
        _amount.text = '${quote['net_amount']}';
      });
    } catch (_) {
      setState(() => _error = 'Could not quote ticket.');
    }
  }

  Future<void> _complete() async {
    final session = ref.read(sessionProvider);
    if (session.shiftId == null) {
      setState(() => _error = 'Open a shift first.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = ref.read(apiProvider);
      final cart = ref.read(cartProvider.notifier);
      final payments = [
        {'method': _method, 'amount': _amount.text},
      ];
      final sale = cart.heldSaleId == null
          ? await api.createSale(
              shiftId: session.shiftId!,
              items: cart.items,
              payments: payments,
              clientSaleUuid: api.newSaleUuid(),
              deviceId: session.deviceId,
              customerId: ref.read(selectedCustomerProvider)?.id,
            )
          : await api.resumeSale(cart.heldSaleId!, payments);
      clearTicket(ref);
      if (mounted) context.go('/receipt/${sale['id']}');
    } catch (_) {
      setState(() => _error = 'Saved locally if offline. Open More to sync.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = ref.watch(cartProvider);
    final net = _quote?['net_amount'];
    final tendered = asMoney(_amount.text);
    final due = asMoney(net);
    final change = _method == 'cash' && tendered > due ? tendered - due : 0.0;

    if (cart.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Payment')),
        body: const EmptyState(
          icon: Icons.shopping_bag_outlined,
          title: 'Cart is empty',
          detail: 'Add items on the register before checkout.',
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Payment')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          Text('Total amount', style: TextStyle(color: muted, fontWeight: FontWeight.w700)),
          MoneyText(net, size: 36),
          CustomerBar(onChanged: _refreshQuote, padding: const EdgeInsets.only(top: 14)),
          const SizedBox(height: 18),
          const SectionLabel('Payment method'),
          const SizedBox(height: 8),
          PosCard(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                for (var i = 0; i < _methods.length; i++) ...[
                  if (i > 0) const Divider(),
                  ListTile(
                    leading: Icon(_methods[i].$3, color: _method == _methods[i].$1 ? accent : muted),
                    title: Text(_methods[i].$2, style: const TextStyle(fontWeight: FontWeight.w700)),
                    trailing: _method == _methods[i].$1
                        ? const Icon(Icons.check_circle, color: accent)
                        : const Icon(Icons.circle_outlined, color: line),
                    onTap: () => setState(() => _method = _methods[i].$1),
                  ),
                ],
              ],
            ),
          ),
          if (_method == 'cash') ...[
            const SizedBox(height: 16),
            TextField(
              controller: _amount,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Amount tendered', prefixText: '₱ '),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            PosCard(
              color: greenSoft,
              child: Row(
                children: [
                  const Text('Change', style: TextStyle(fontWeight: FontWeight.w800, color: ink)),
                  const Spacer(),
                  MoneyText(change, size: 22, color: accent),
                ],
              ),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: red, fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _complete,
            child: Text(_busy ? 'Posting…' : 'Complete sale'),
          ),
        ],
      ),
    );
  }
}
