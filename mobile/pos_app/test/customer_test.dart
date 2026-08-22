import 'package:flutter_test/flutter_test.dart';
import 'package:pos_app/core/customers/customer.dart';

void main() {
  test('PosCustomer parses membership fields', () {
    final customer = PosCustomer.fromJson({
      'id': 7,
      'name': 'Mia Santos',
      'mobile': '09170009999',
      'membership_tier': 'PREMIUM',
      'canteen_discount_pct': '10.00',
      'court_discount_pct': '20.00',
      'loyalty_points': 32,
    });
    expect(customer.isMember, isTrue);
    expect(customer.subtitle, '09170009999 · PREMIUM · 32 pts');
    expect(customer.canteenLabel, 'PREMIUM · 10.00% canteen');
    expect(customer.courtLabel, 'PREMIUM · 20.00% court');
  });

  test('walk-in profile has no member label', () {
    final customer = PosCustomer.fromJson({'id': 1, 'name': 'Walk-in guest'});
    expect(customer.isMember, isFalse);
    expect(customer.subtitle, 'Saved profile');
    expect(customer.canteenLabel, 'Member');
  });
}
