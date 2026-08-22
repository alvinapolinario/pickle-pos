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
    HapticFeedback.mediumImpact();
    ref.read(cartProvider.notifier).add(product);
  }

  @override
  Widget build(BuildContext context) {
    final cart = ref.watch(cartProvider);
    final shiftId = ref.watch(sessionProvider).shiftId;
    final items = cart.fold<int>(0, (sum, line) => sum + line.qty);
    final total = cart.fold<double>(0, (sum, line) => sum + asMoney(line.price) * line.qty);
    final qtyById = {for (final line in cart) line.id: line.qty};
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
                              qty: qtyById[product['id']] ?? 0,
                              onAdd: () => _add(product, shiftId),
                            );
                          },
                        ),
                      ),
          ),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            switchInCurve: Curves.easeOutCubic,
            switchOutCurve: Curves.easeInCubic,
            transitionBuilder: (child, animation) {
              return SlideTransition(
                position: Tween<Offset>(begin: const Offset(0, 0.35), end: Offset.zero).animate(animation),
                child: FadeTransition(opacity: animation, child: child),
              );
            },
            child: cart.isEmpty
                ? const SizedBox.shrink(key: ValueKey('cart-empty'))
                : _CartDock(
                    key: const ValueKey('cart-dock'),
                    items: items,
                    total: total,
                    onTap: () => context.push('/cart'),
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

class _ProductCard extends StatefulWidget {
  const _ProductCard({required this.product, required this.onAdd, this.qty = 0});

  final Map<String, dynamic> product;
  final VoidCallback onAdd;
  final int qty;

  @override
  State<_ProductCard> createState() => _ProductCardState();
}

class _ProductCardState extends State<_ProductCard> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scale;
  bool _justAdded = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 240));
    _scale = TweenSequence<double>([
      TweenSequenceItem(tween: Tween<double>(begin: 1, end: 0.9).chain(CurveTween(curve: Curves.easeOut)), weight: 35),
      TweenSequenceItem(tween: Tween<double>(begin: 0.9, end: 1.04).chain(CurveTween(curve: Curves.easeOut)), weight: 35),
      TweenSequenceItem(tween: Tween<double>(begin: 1.04, end: 1).chain(CurveTween(curve: Curves.easeOutBack)), weight: 30),
    ]).animate(_controller);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _handleAdd() async {
    widget.onAdd();
    setState(() => _justAdded = true);
    await _controller.forward(from: 0);
    if (!mounted) return;
    await Future<void>.delayed(const Duration(milliseconds: 320));
    if (mounted) setState(() => _justAdded = false);
  }

  @override
  Widget build(BuildContext context) {
    final inCart = widget.qty > 0;
    return ScaleTransition(
      scale: _scale,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          boxShadow: _justAdded
              ? const [BoxShadow(color: Color(0x4D1E8A3C), blurRadius: 16, offset: Offset(0, 6))]
              : const [],
        ),
        child: PosCard(
          padding: EdgeInsets.zero,
          color: _justAdded ? accentSoft : Colors.white,
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: _handleAdd,
              borderRadius: BorderRadius.circular(16),
              child: Padding(
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
                              name: widget.product['name'] as String,
                              imageUrl: widget.product['image_url'] as String?,
                              seed: widget.product['id'] as int,
                              expand: true,
                              radius: 12,
                            ),
                          ),
                          AnimatedOpacity(
                            opacity: _justAdded ? 1 : 0,
                            duration: const Duration(milliseconds: 140),
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                color: accent.withValues(alpha: 0.42),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Center(
                                child: Icon(Icons.check_rounded, color: Colors.white, size: 42),
                              ),
                            ),
                          ),
                          if (inCart && !_justAdded)
                            Positioned(
                              left: 6,
                              top: 6,
                              child: _QtyBadge(qty: widget.qty),
                            ),
                          Positioned(
                            right: 6,
                            bottom: 6,
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 160),
                              width: 36,
                              height: 36,
                              decoration: BoxDecoration(
                                color: _justAdded || inCart ? const Color(0xFF166534) : accent,
                                shape: BoxShape.circle,
                                boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 6, offset: Offset(0, 2))],
                              ),
                              child: AnimatedSwitcher(
                                duration: const Duration(milliseconds: 160),
                                child: Icon(
                                  _justAdded ? Icons.check_rounded : Icons.add,
                                  key: ValueKey(_justAdded),
                                  color: Colors.white,
                                  size: 22,
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
                            widget.product['name'] as String,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontWeight: FontWeight.w800, height: 1.2, color: ink),
                          ),
                          const Spacer(),
                          MoneyText(widget.product['selling_price'], size: 15, color: accent),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _QtyBadge extends StatelessWidget {
  const _QtyBadge({required this.qty});

  final int qty;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 160),
      transitionBuilder: (child, animation) => ScaleTransition(scale: animation, child: child),
      child: Container(
        key: ValueKey(qty),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: accent,
          borderRadius: BorderRadius.circular(99),
        ),
        child: Text(
          '×$qty',
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12),
        ),
      ),
    );
  }
}

class _CartDock extends StatefulWidget {
  const _CartDock({super.key, required this.items, required this.total, required this.onTap});

  final int items;
  final double total;
  final VoidCallback onTap;

  @override
  State<_CartDock> createState() => _CartDockState();
}

class _CartDockState extends State<_CartDock> with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;
  late final Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(vsync: this, duration: const Duration(milliseconds: 260));
    _scale = TweenSequence<double>([
      TweenSequenceItem(tween: Tween<double>(begin: 1, end: 1.045).chain(CurveTween(curve: Curves.easeOut)), weight: 50),
      TweenSequenceItem(tween: Tween<double>(begin: 1.045, end: 1).chain(CurveTween(curve: Curves.easeOutBack)), weight: 50),
    ]).animate(_pulse);
    _pulse.forward();
  }

  @override
  void didUpdateWidget(covariant _CartDock oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.items != widget.items || oldWidget.total != widget.total) {
      _pulse.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        child: ScaleTransition(
          scale: _scale,
          child: Material(
            color: accent,
            borderRadius: BorderRadius.circular(16),
            child: InkWell(
              onTap: widget.onTap,
              borderRadius: BorderRadius.circular(16),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                child: Row(
                  children: [
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 180),
                      transitionBuilder: (child, animation) => ScaleTransition(scale: animation, child: child),
                      child: Container(
                        key: ValueKey(widget.items),
                        width: 28,
                        height: 28,
                        alignment: Alignment.center,
                        decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                        child: Text(
                          '${widget.items}',
                          style: const TextStyle(color: accent, fontWeight: FontWeight.w800, fontSize: 13),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        widget.items == 1 ? '1 item in cart' : '${widget.items} items in cart',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
                      ),
                    ),
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 180),
                      child: Text(
                        peso(widget.total),
                        key: ValueKey(widget.total),
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16),
                      ),
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
    );
  }
}
