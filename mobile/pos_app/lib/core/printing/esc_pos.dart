/// ESC/POS bytes for a 58mm/80mm thermal printer from server receipt text.
List<int> escPosTicket(String text, {int copies = 1, String? qrData}) {
  final safeCopies = copies < 1 ? 1 : (copies > 5 ? 5 : copies);
  final payload = <int>[];
  for (var i = 0; i < safeCopies; i++) {
    payload.addAll(const [0x1B, 0x40]); // initialize
    payload.addAll(const [0x1B, 0x61, 0x00]); // left align
    payload.addAll(const [0x1B, 0x21, 0x00]); // normal size
    payload.addAll(_latinBytes(_normalize(text)));
    if (!text.endsWith('\n')) {
      payload.add(0x0A);
    }
    final qr = (qrData ?? '').trim();
    if (qr.isNotEmpty) {
      payload.addAll(escPosQrCode(qr));
    }
    payload.addAll(const [0x0A, 0x0A, 0x0A]);
    payload.addAll(const [0x1D, 0x56, 0x41, 0x03]); // partial cut
  }
  return payload;
}

const List<int> escPosInit = [0x1B, 0x40];
const List<int> escPosPartialCut = [0x1D, 0x56, 0x41, 0x03];
const List<int> escPosQrPrint = [0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x51, 0x30];

/// Native ESC/POS QR (model 2) centered at the bottom of the ticket.
List<int> escPosQrCode(String data, {int moduleSize = 5}) {
  final bytes = data.codeUnits.map((unit) => unit <= 255 ? unit : 0x3F).toList();
  if (bytes.isEmpty) return const [];
  final size = moduleSize < 3 ? 3 : (moduleSize > 8 ? 8 : moduleSize);
  final storeLen = 3 + bytes.length;
  return [
    0x0A,
    0x1B, 0x61, 0x01, // center
    0x1D, 0x28, 0x6B, 0x04, 0x00, 0x31, 0x41, 0x32, 0x00, // model 2
    0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x43, size, // module size
    0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x45, 0x31, // error correction M
    0x1D, 0x28, 0x6B, storeLen & 0xFF, (storeLen >> 8) & 0xFF, 0x31, 0x50, 0x30,
    ...bytes,
    ...escPosQrPrint,
    0x0A,
    ..._latinBytes('Thank You\n'),
    0x1B, 0x61, 0x00, // left
  ];
}

String printerTestTicket({String name = 'Thermal printer', String mac = ''}) {
  const rule = '********************************';
  final lines = [
    rule,
    '      PICKLEBALL POS',
    '       Printer test',
    rule,
    name,
    if (mac.isNotEmpty) mac,
    '',
    'If you can read this, the',
    'register is ready to print',
    'receipts.',
    rule,
    '',
  ];
  return lines.join('\n');
}

bool containsBytes(List<int> haystack, List<int> needle) {
  if (needle.isEmpty || haystack.length < needle.length) return false;
  for (var i = 0; i <= haystack.length - needle.length; i++) {
    var match = true;
    for (var j = 0; j < needle.length; j++) {
      if (haystack[i + j] != needle[j]) {
        match = false;
        break;
      }
    }
    if (match) return true;
  }
  return false;
}

String _normalize(String text) {
  return text
      .replaceAll('₱', 'P')
      .replaceAll('—', '-')
      .replaceAll('–', '-')
      .replaceAll('’', "'")
      .replaceAll('‘', "'")
      .replaceAll('“', '"')
      .replaceAll('”', '"');
}

List<int> _latinBytes(String text) {
  return text.codeUnits.map((unit) => unit <= 255 ? unit : 0x3F).toList();
}
