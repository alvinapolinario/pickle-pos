import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/customers/customer.dart';
import '../../core/customers/selected_customer.dart';
import '../../core/network/api_client.dart';
import '../../ui/widgets.dart';

class CustomerPick {
  const CustomerPick(this.customer);

  final PosCustomer? customer;
}

Future<CustomerPick?> showCustomerPicker(
  BuildContext context, {
  PosCustomer? selected,
  bool applyGlobally = true,
}) {
  return showModalBottomSheet<CustomerPick>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => CustomerPickerSheet(selected: selected, applyGlobally: applyGlobally),
  );
}

class CustomerBar extends ConsumerWidget {
  const CustomerBar({super.key, this.onChanged, this.padding = const EdgeInsets.fromLTRB(16, 12, 16, 0)});

  final VoidCallback? onChanged;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final customer = ref.watch(selectedCustomerProvider);
    return Padding(
      padding: padding,
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () async {
            final picked = await showCustomerPicker(context, selected: customer);
            if (picked != null) onChanged?.call();
          },
          child: Ink(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: line),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 18,
                    backgroundColor: customer == null ? const Color(0xFFF1F4F8) : accentSoft,
                    child: Icon(
                      customer == null ? Icons.person_outline : Icons.person,
                      color: customer == null ? muted : accent,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          customer?.name ?? 'Walk-in',
                          style: const TextStyle(fontWeight: FontWeight.w800, color: ink),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          customer?.canteenLabel ?? 'No member rates',
                          style: const TextStyle(color: muted, fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                  if (customer?.isMember == true) const StatusPill(label: 'Member', tone: StatusTone.good),
                  const Icon(Icons.chevron_right, color: muted),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class CustomerPickerSheet extends ConsumerStatefulWidget {
  const CustomerPickerSheet({super.key, this.selected, this.applyGlobally = true});

  final PosCustomer? selected;
  final bool applyGlobally;

  @override
  ConsumerState<CustomerPickerSheet> createState() => _CustomerPickerSheetState();
}

class _CustomerPickerSheetState extends ConsumerState<CustomerPickerSheet> {
  final _search = TextEditingController();
  final _name = TextEditingController();
  final _mobile = TextEditingController();
  Timer? _debounce;
  List<PosCustomer> _results = const [];
  bool _loading = true;
  bool _adding = false;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    _name.dispose();
    _mobile.dispose();
    super.dispose();
  }

  Future<void> _load([String query = '']) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final rows = await ref.read(apiProvider).customers(q: query);
      if (!mounted) return;
      setState(() {
        _results = [
          for (final row in rows) PosCustomer.fromJson(Map<String, dynamic>.from(row as Map)),
        ];
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = 'Could not load customers.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _onQuery(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 280), () => _load(value.trim()));
  }

  void _choose(PosCustomer? customer) {
    if (widget.applyGlobally) {
      ref.read(selectedCustomerProvider.notifier).state = customer;
    }
    Navigator.pop(context, CustomerPick(customer));
  }

  Future<void> _create() async {
    final name = _name.text.trim();
    if (name.isEmpty) {
      setState(() => _error = 'Name is required.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final row = await ref.read(apiProvider).createCustomer(name: name, mobile: _mobile.text.trim());
      if (!mounted) return;
      _choose(PosCustomer.fromJson(row));
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = 'Could not save that customer. Check the mobile is unique.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final selectedId = widget.selected?.id;
    final media = MediaQuery.of(context);
    final keyboard = media.viewInsets.bottom;
    final height = (media.size.height - keyboard - 32).clamp(280.0, media.size.height * 0.72);
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 8, 20, 16 + keyboard),
      child: SizedBox(
        height: height,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Customer', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 20, color: ink)),
            const SizedBox(height: 4),
            const Text('Walk-in keeps regular prices. Members get their canteen or court rate.', style: TextStyle(color: muted)),
            const SizedBox(height: 12),
            TextField(
              controller: _search,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Search name or mobile',
              ),
              onChanged: _onQuery,
            ),
            const SizedBox(height: 8),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const CircleAvatar(
                backgroundColor: Color(0xFFF1F4F8),
                child: Icon(Icons.person_outline, color: muted),
              ),
              title: const Text('Walk-in', style: TextStyle(fontWeight: FontWeight.w800)),
              subtitle: const Text('No membership discount'),
              trailing: selectedId == null ? const Icon(Icons.check_circle, color: accent) : null,
              onTap: () => _choose(null),
            ),
            const Divider(height: 8),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _results.isEmpty
                      ? const EmptyState(
                          icon: Icons.person_search_outlined,
                          title: 'No matches',
                          detail: 'Try another search or add a customer.',
                        )
                      : ListView.separated(
                          itemCount: _results.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final customer = _results[index];
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: CircleAvatar(
                                backgroundColor: accentSoft,
                                child: Text(
                                  customer.name[0].toUpperCase(),
                                  style: const TextStyle(color: accent, fontWeight: FontWeight.w800),
                                ),
                              ),
                              title: Text(customer.name, style: const TextStyle(fontWeight: FontWeight.w800)),
                              subtitle: Text(customer.subtitle, style: const TextStyle(color: muted)),
                              trailing: customer.id == selectedId
                                  ? const Icon(Icons.check_circle, color: accent)
                                  : customer.isMember
                                      ? const StatusPill(label: 'Member', tone: StatusTone.good)
                                      : null,
                              onTap: () => _choose(customer),
                            );
                          },
                        ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: red, fontWeight: FontWeight.w600)),
            ],
            if (_adding) ...[
              const SizedBox(height: 8),
              TextField(controller: _name, decoration: const InputDecoration(labelText: 'Name'), textCapitalization: TextCapitalization.words),
              const SizedBox(height: 8),
              TextField(controller: _mobile, decoration: const InputDecoration(labelText: 'Mobile (optional)'), keyboardType: TextInputType.phone),
              const SizedBox(height: 10),
              FilledButton(
                onPressed: _saving ? null : _create,
                child: Text(_saving ? 'Saving…' : 'Save customer'),
              ),
            ] else
              TextButton.icon(
                onPressed: () => setState(() => _adding = true),
                icon: const Icon(Icons.person_add_outlined),
                label: const Text('Add customer'),
              ),
          ],
        ),
      ),
    );
  }
}
