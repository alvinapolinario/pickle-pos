import 'package:flutter_test/flutter_test.dart';
import 'package:pos_app/features/pos/cart_controller.dart';

void main() {
  Map<String, dynamic> drink() => {
        'id': 1,
        'name': 'Sports Drink',
        'selling_price': '45.00',
      };

  test('keeps heldSaleId when editing a resumed cart', () {
    final cart = CartNotifier();
    cart.loadHeld(42, [CartLine(product: drink(), qty: 1)]);
    expect(cart.heldSaleId, 42);

    cart.add(drink());
    expect(cart.heldSaleId, 42);
    expect(cart.state.single.qty, 2);

    cart.remove(1);
    expect(cart.heldSaleId, 42);
    expect(cart.state.single.qty, 1);

    cart.removeLine(1);
    expect(cart.heldSaleId, 42);
    expect(cart.state, isEmpty);
  });

  test('clear drops heldSaleId', () {
    final cart = CartNotifier();
    cart.loadHeld(42, [CartLine(product: drink(), qty: 1)]);
    cart.clear();
    expect(cart.heldSaleId, isNull);
    expect(cart.state, isEmpty);
  });
}
