import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/bookings/bookings_screen.dart';
import '../features/home/home_screen.dart';
import '../features/login/login_screen.dart';
import '../features/payment/payment_screen.dart';
import '../features/refunds/refund_screen.dart';
import '../features/pos/barcode_scan_screen.dart';
import '../features/pos/cart_screen.dart';
import '../features/pos/pos_screen.dart';
import '../features/receipt/receipt_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/shift/shift_screen.dart';
import '../features/shell/shell_screen.dart';
import '../features/transactions/transactions_screen.dart';
import '../core/auth/session.dart';
import 'theme.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final loggedIn = ref.watch(sessionProvider.select((s) => s.accessToken != null));
  return GoRouter(
    initialLocation: '/login',
    redirect: (context, state) {
      final loggingIn = state.matchedLocation == '/login';
      if (!loggedIn && !loggingIn) return '/login';
      if (loggedIn && loggingIn) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      ShellRoute(
        builder: (_, __, child) => ShellScreen(child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
          GoRoute(path: '/pos', builder: (_, __) => const PosScreen()),
          GoRoute(path: '/tickets', builder: (_, __) => const TransactionsScreen()),
          GoRoute(path: '/bookings', builder: (_, __) => const BookingsScreen()),
          GoRoute(path: '/shift', builder: (_, __) => const ShiftScreen()),
          GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
        ],
      ),
      GoRoute(path: '/scan', builder: (_, __) => const BarcodeScanScreen()),
      GoRoute(path: '/cart', builder: (_, __) => const CartScreen()),
      GoRoute(path: '/pay', builder: (_, __) => const PaymentScreen()),
      GoRoute(
        path: '/receipt/:id',
        builder: (_, state) => ReceiptScreen(saleId: int.parse(state.pathParameters['id']!)),
      ),
      GoRoute(
        path: '/refund/:id',
        builder: (_, state) => RefundScreen(saleId: int.parse(state.pathParameters['id']!)),
      ),
    ],
  );
});

class PicklePosApp extends ConsumerWidget {
  const PicklePosApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Pickleball POS',
      theme: pickleTheme(),
      debugShowCheckedModeBanner: false,
      routerConfig: router,
    );
  }
}
