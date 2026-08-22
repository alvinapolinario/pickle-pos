import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../ui/format.dart';
import '../../ui/widgets.dart';
import '../customers/customer_picker.dart';
import 'cart_controller.dart';

class PosScreen extends ConsumerStatefulWidget {
  const PosScreen({super.key});

  @override
  ConsumerState<PosScreen> createState() => _PosScreenState();
}

class _PosScreenState extends ConsumerState<PosScreen> {
  List<dynamic> _categories = const [];
  List<dynamic> _products = const [];
  int? _categoryId;
  String _query = '';
  String? _error;
  bool _loading = true;
  bool _showSearch = false;
  final _search = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiProvider);
      if (ref.read(sessionProvider).shiftId == null) {
        final shift = await api.currentShift();
        await ref.read(sessionProvider.notifier).setShift(shift?['id'] as int?);
      }
      final categories = await api.categories();
      final products = await api.products(categoryId: _categoryId, q: _query);
      setState(() {
        _categories = categories;
        _products = products;
      });
    } catch (error) {
      setState(() => _error = 'Could not load catalog. Pull to retry or check More.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _handleSubmitted(String raw) async {
    final code = raw.trim();
    if (code.isEmpty) {
      _query = '';
      await _load();
      return;
    }
    if (ref.read(sessionProvider).shiftId != null) {
      try {
        final product = await ref.read(apiProvider).lookupProduct(code);
        if (product != null && mounted) {
          HapticFeedback.mediumImpact();
          ref.read(cartProvider.notifier).add(product);
          _search.clear();
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Added ${product['name']}'), duration: const Duration(milliseconds: 900)),
          );
          return;
        }
      } catch (_) {}
    }
    _query = code;
    await _load();
  }

  void _add(Map<String, dynamic> product, int? shiftId) {
    if (shiftId == null) {
      context.go('/shift');
      return;
    }
    HapticFeedback.selectionClick();
    ref.read(cartProvider.notifier).add(product);
  }

  @override
  Widget build(BuildContext context) {
    final cart = ref.watch(cartProvider);
    final shiftId = ref.watch(sessionProvider).shiftId;
    final items = cart.fold<int>(0, (sum, line) => sum + line.qty);
    final total = cart.fold<double>(0, (sum, line) => sum + asMoney(line.price) * line.qty);
    final columns = MediaQuery.sizeOf(context).width >= 900 ? 4 : MediaQuery.sizeOf(context).width >= 600 ? 3 : 2;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Canteen'),
        actions: [
          IconButton(
            onPressed: () => setState(() => _showSearch = !_showSearch),
            icon: const Icon(Icons.search),
          ),
          IconButton(onPressed: () => context.push('/scan'), icon: const Icon(Icons.qr_code_scanner)),
        ],
      ),
      body: Column(
        children: [
          if (shiftId == null)
            SoftBanner(
              message: 'Open a shift before selling.',
              actionLabel: 'Open',
              onAction: () => context.go('/shift'),
            ),
          const CustomerBar(),
          if (_showSearch)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: TextField(
                controller: _search,
                autofocus: true,
                textInputAction: TextInputAction.search,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  hintText: 'Search or scan barcode',
                ),
                onSubmitted: _handleSubmitted,
              ),
            ),
          SizedBox(
            height: 52,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              children: [
                _chip('All', _categoryId == null, () {
                  _categoryId = null;
                  _load();
                }),
                ..._categories.map(
                  (category) => _chip(
                    category['name'] as String,
                    _categoryId == category['id'],
                    () {
                      _categoryId = category['id'] as int;
                      _load();
                    },
                  ),
                ),
              ],
            ),
          ),
          if (_error != null) SoftBanner(message: _error!, tone: StatusTone.bad),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _products.isEmpty
                    ? const EmptyState(
                        icon: Icons.inventory_2_outlined,
                        title: 'No products',
                        detail: 'Try another category or search.',
                      )
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: GridView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: columns,
                            childAspectRatio: 0.78,
                            crossAxisSpacing: 10,
                            mainAxisSpacing: 10,
                          ),
                          itemCount: _products.length,
                          itemBuilder: (context, index) {
                            final product = Map<String, dynamic>.from(_products[index] as Map);
                            return _ProductCard(
                              product: product,
                              onAdd: () => _add(product, shiftId),
                            );
                          },
                        ),
                      ),
          ),
          if (cart.isNotEmpty)
            SafeArea(
              top: false,
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                child: Material(
                  color: accent,
                  borderRadius: BorderRadius.circular(16),
                  child: InkWell(
                    onTap: () => context.push('/cart'),
                    borderRadius: BorderRadius.circular(16),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                      child: Row(
                        children: [
                          Text(
                            'Cart ($items ${items == 1 ? 'item' : 'items'})',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
                          ),
                          const Spacer(),
                          Text(
                            peso(total),
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16),
                          ),
                          const SizedBox(width: 4),
                          const Icon(Icons.chevron_right, color: Colors.white),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _chip(String label, bool selected, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        selectedColor: accent,
        labelStyle: TextStyle(
          color: selected ? Colors.white : ink,
          fontWeight: FontWeight.w800,
        ),
        side: BorderSide(color: selected ? accent : line),
        onSelected: (_) => onTap(),
      ),
    );
  }
}

class _ProductCard extends StatelessWidget {
  const _ProductCard({required this.product, required this.onAdd});

  final Map<String, dynamic> product;
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    return PosCard(
      padding: const EdgeInsets.all(10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 3,
            child: Stack(
              children: [
                Positioned.fill(
                  child: ProductThumb(
                    name: product['name'] as String,
                    imageUrl: product['image_url'] as String?,
                    seed: product['id'] as int,
                    expand: true,
                    radius: 12,
                  ),
                ),
                Positioned(
                  right: 6,
                  bottom: 6,
                  child: Material(
                    color: accent,
                    shape: const CircleBorder(),
                    child: InkWell(
                      customBorder: const CircleBorder(),
                      onTap: onAdd,
                      child: const SizedBox(
                        width: 32,
                        height: 32,
                        child: Icon(Icons.add, color: Colors.white, size: 20),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            flex: 2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  product['name'] as String,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, height: 1.2, color: ink),
                ),
                const Spacer(),
                MoneyText(product['selling_price'], size: 15, color: accent),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
