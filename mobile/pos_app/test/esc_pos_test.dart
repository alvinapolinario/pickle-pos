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

  test('escPosTicket appends a QR command block before the cut', () {
    final bytes = escPosTicket('TOTAL P 45.00', qrData: 'R-00042');
    expect(containsBytes(bytes, escPosQrPrint), isTrue);
    expect(containsBytes(bytes, 'R-00042'.codeUnits), isTrue);
    expect(containsBytes(bytes, 'Scan receipt'.codeUnits), isFalse);
    expect(containsBytes(bytes, 'Thank You'.codeUnits), isTrue);
    final cutAt = _indexOf(bytes, escPosPartialCut);
    final qrAt = _indexOf(bytes, escPosQrPrint);
    final thanksAt = _indexOf(bytes, 'Thank You'.codeUnits);
    expect(qrAt, greaterThan(0));
    expect(thanksAt, greaterThan(qrAt));
    expect(cutAt, greaterThan(thanksAt));
  });

  test('escPosTicket omits QR when no payload is given', () {
    final bytes = escPosTicket('TOTAL P 45.00');
    expect(containsBytes(bytes, escPosQrPrint), isFalse);
  });
}

int _indexOf(List<int> haystack, List<int> needle) {
  for (var i = 0; i <= haystack.length - needle.length; i++) {
    var match = true;
    for (var j = 0; j < needle.length; j++) {
      if (haystack[i + j] != needle[j]) {
        match = false;
        break;
      }
    }
    if (match) return i;
  }
  return -1;
}
