import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/pos/cart_controller.dart';
import 'customer.dart';

final selectedCustomerProvider = StateProvider<PosCustomer?>((ref) => null);

void clearTicket(WidgetRef ref) {
  ref.read(cartProvider.notifier).clear();
  ref.read(selectedCustomerProvider.notifier).state = null;
}
