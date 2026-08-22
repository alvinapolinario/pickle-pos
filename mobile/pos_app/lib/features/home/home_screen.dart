import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../ui/format.dart';
import '../../ui/widgets.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  Map<String, dynamic>? _shift;
  List<Map<String, dynamic>> _lowStock = const [];
  double _sales = 0;
  int _tickets = 0;
  double _average = 0;
  int _customers = 0;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String get _greeting {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  bool _isToday(dynamic iso) {
    final parsed = DateTime.tryParse('$iso')?.toLocal();
    if (parsed == null) return false;
    final now = DateTime.now();
    return parsed.year == now.year && parsed.month == now.month && parsed.day == now.day;
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiProvider);
      final shift = await api.currentShift();
      await ref.read(sessionProvider.notifier).setShift(shift?['id'] as int?);
      final sales = await api.sales(status: 'completed');
      final today = sales.where((row) => _isToday((row as Map)['created_at'])).map((row) => Map<String, dynamic>.from(row as Map)).toList();
      final total = today.fold<double>(0, (sum, sale) => sum + asMoney(sale['net_amount']));
      final customers = today.map((sale) => sale['customer_id'] ?? sale['id']).toSet().length;
      List<Map<String, dynamic>> low = const [];
      try {
        final balances = await api.balances();
        low = balances
            .map((row) => Map<String, dynamic>.from(row as Map))
            .where((row) => row['is_low'] == true)
            .toList();
      } catch (_) {}
      if (!mounted) return;
      setState(() {
        _shift = shift;
        _sales = total;
        _tickets = today.length;
        _average = today.isEmpty ? 0 : total / today.length;
        _customers = customers;
        _lowStock = low;
      });
    } catch (_) {
      if (!mounted) return;
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final name = session.username ?? 'Cashier';
    final opened = DateTime.tryParse('${_shift?['opened_at'] ?? ''}')?.toLocal();

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              Row(
                children: [
                  const BrandMark(size: 40),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Pickleball POS', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18, color: ink)),
                        Text('Canteen register', style: TextStyle(color: muted, fontWeight: FontWeight.w600, fontSize: 12)),
                      ],
                    ),
                  ),
                  IconButton(onPressed: _load, icon: const Icon(Icons.notifications_none_rounded)),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  CircleAvatar(
                    radius: 22,
                    backgroundColor: accentSoft,
                    child: Text(name.isEmpty ? 'C' : name[0].toUpperCase(), style: const TextStyle(color: accent, fontWeight: FontWeight.w800)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('$_greeting, $name', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18, color: ink)),
                        const Text('Ready for the next ticket', style: TextStyle(color: muted, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Material(
                color: accent,
                borderRadius: BorderRadius.circular(18),
                child: InkWell(
                  onTap: () => context.go('/shift'),
                  borderRadius: BorderRadius.circular(18),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(18, 18, 16, 18),
                    child: Row(
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Icon(_shift == null ? Icons.lock_clock : Icons.lock_open_rounded, color: Colors.white),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _shift == null ? 'No open shift' : 'Open shift',
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16),
                              ),
                              Text(
                                _shift == null
                                    ? 'Open the drawer before selling'
                                    : 'Shift #${_shift!['id']}${opened == null ? '' : ' · ${DateFormat.jm().format(opened)}'}',
                                style: TextStyle(color: Colors.white.withValues(alpha: 0.82), fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                        ),
                        const Text('View', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: Center(child: CircularProgressIndicator()),
                )
              else
                GridView.count(
                  crossAxisCount: MediaQuery.sizeOf(context).width >= 840 ? 4 : 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 10,
                  childAspectRatio: MediaQuery.sizeOf(context).width >= 840 ? 1.7 : 1.35,
                  children: [
                    _metric('Today’s sales', peso(_sales), Icons.trending_up),
                    _metric('Transactions', '$_tickets', Icons.receipt_long_outlined),
                    _metric('Avg. order', peso(_average), Icons.payments_outlined),
                    _metric('Customers', '$_customers', Icons.people_outline),
                  ],
                ),
              const SizedBox(height: 20),
              const SectionLabel('Quick actions'),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: QuickAction(
                      label: 'New sale',
                      icon: Icons.point_of_sale,
                      color: accent,
                      onTap: () => context.go('/pos'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: QuickAction(
                      label: 'Court booking',
                      icon: Icons.calendar_month_outlined,
                      color: purple,
                      onTap: () => context.go('/bookings'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: QuickAction(
                      label: 'Held orders',
                      icon: Icons.pause_circle_outline,
                      color: orange,
                      onTap: () => context.go('/tickets'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: QuickAction(
                      label: 'Refund',
                      icon: Icons.replay,
                      color: red,
                      onTap: () => context.go('/tickets'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              const SectionLabel('Low stock alerts'),
              const SizedBox(height: 8),
              if (_lowStock.isEmpty)
                const PosCard(
                  child: Text('No low-stock items right now.', style: TextStyle(color: muted, fontWeight: FontWeight.w600)),
                )
              else
                ..._lowStock.take(5).map((item) {
                  final onHand = asMoney(item['on_hand']);
                  final reorder = asMoney(item['reorder_level']);
                  final ratio = reorder <= 0 ? 0.0 : (onHand / reorder).clamp(0.0, 1.0);
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: PosCard(
                      child: Row(
                        children: [
                          ProductThumb(name: '${item['name']}', seed: item['product_id'] as int? ?? 0, size: 48),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${item['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                                const SizedBox(height: 6),
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(99),
                                  child: LinearProgressIndicator(
                                    value: ratio,
                                    minHeight: 6,
                                    color: red,
                                    backgroundColor: redSoft,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text('Stock: ${item['on_hand']}', style: const TextStyle(color: red, fontWeight: FontWeight.w800)),
                        ],
                      ),
                    ),
                  );
                }),
            ],
          ),
        ),
      ),
    );
  }

  Widget _metric(String label, String value, IconData icon) {
    return PosCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: accentSoft,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: accent, size: 26),
          ),
          const Spacer(),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18, color: ink)),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(color: muted, fontWeight: FontWeight.w600, fontSize: 12)),
        ],
      ),
    );
  }
}
