import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:pos_app/app/app.dart';

void main() {
  testWidgets('shows sign in', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: PicklePosApp()));
    await tester.pump();
    expect(find.text('Sign in'), findsWidgets);
  });
}
