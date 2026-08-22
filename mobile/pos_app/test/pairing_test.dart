import 'package:flutter_test/flutter_test.dart';
import 'package:pos_app/core/network/pairing.dart';

void main() {
  test('parses picklepos pairing URI', () {
    final pairing = PosPairing.tryParse(
      'picklepos://connect?url=http%3A%2F%2F10.0.0.12%3A7101%2F&key=abc-key',
    );
    expect(pairing, isNotNull);
    expect(pairing!.url, 'http://10.0.0.12:7101');
    expect(pairing.key, 'abc-key');
  });

  test('parses JSON pairing payload', () {
    final pairing = PosPairing.tryParse('{"url":"http://10.0.0.12:7101/","key":"secret"}');
    expect(pairing?.url, 'http://10.0.0.12:7101');
    expect(pairing?.key, 'secret');
  });

  test('rejects unrelated barcodes', () {
    expect(PosPairing.tryParse('4801234560001'), isNull);
    expect(PosPairing.tryParse(''), isNull);
  });
}
