import 'package:flutter_test/flutter_test.dart';
import 'package:pos_app/core/printing/esc_pos.dart';

void main() {
  test('escPosTicket initializes, normalizes pesos, and cuts', () {
    final bytes = escPosTicket('₱12.00 — hello');
    expect(bytes.take(2), escPosInit);
    expect(containsBytes(bytes, escPosPartialCut), isTrue);
    final printable = String.fromCharCodes(bytes.where((unit) => unit >= 32 && unit < 127));
    expect(printable, contains('P12.00 - hello'));
    expect(printable, isNot(contains('₱')));
  });

  test('escPosTicket repeats a full ticket per copy', () {
    final one = escPosTicket('A');
    final two = escPosTicket('A', copies: 2);
    expect(two, [...one, ...one]);
  });

  test('printerTestTicket is 32-column friendly', () {
    final text = printerTestTicket(name: 'Xprinter', mac: 'AA:BB:CC:DD:EE:FF');
    expect(text, contains('PICKLEBALL POS'));
    expect(text, contains('Xprinter'));
    expect(text.split('\n').every((line) => line.length <= 32), isTrue);
  });
}
