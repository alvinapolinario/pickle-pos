import 'package:flutter_riverpod/flutter_riverpod.dart';

class CartLine {
  CartLine({required this.product, this.qty = 1});

  final Map<String, dynamic> product;
  int qty;

  int get id => product['id'] as int;
  String get name => product['name'] as String;
  String get price => '${product['selling_price']}';
  String? get imageUrl => product['image_url'] as String?;
}

class CartNotifier extends StateNotifier<List<CartLine>> {
  CartNotifier() : super(const []);

  int? heldSaleId;

  void add(Map<String, dynamic> product, {int qty = 1}) {
    heldSaleId = null;
    final next = [...state];
    final index = next.indexWhere((line) => line.id == product['id']);
    if (index >= 0) {
      next[index] = CartLine(product: product, qty: next[index].qty + qty);
    } else {
      next.add(CartLine(product: product, qty: qty));
    }
    state = next;
  }

  void loadHeld(int saleId, List<CartLine> lines) {
    heldSaleId = saleId;
    state = lines;
  }

  void remove(int productId) {
    heldSaleId = null;
    state = [
      for (final line in state)
        if (line.id != productId) line else if (line.qty > 1) CartLine(product: line.product, qty: line.qty - 1),
    ];
  }

  void removeLine(int productId) {
    heldSaleId = null;
    state = [for (final line in state) if (line.id != productId) line];
  }

  void clear() {
    heldSaleId = null;
    state = const [];
  }

  List<Map<String, dynamic>> get items => [
        for (final line in state) {'product_id': line.id, 'quantity': '${line.qty}'},
      ];
}

final cartProvider = StateNotifierProvider<CartNotifier, List<CartLine>>((ref) {
  return CartNotifier();
});
