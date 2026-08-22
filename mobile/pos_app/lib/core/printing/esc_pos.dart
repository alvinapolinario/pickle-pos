/// ESC/POS bytes for a 58mm/80mm thermal printer from server receipt text.
List<int> escPosTicket(String text, {int copies = 1}) {
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
    payload.addAll(const [0x0A, 0x0A, 0x0A]);
    payload.addAll(const [0x1D, 0x56, 0x41, 0x03]); // partial cut
  }
  return payload;
}

const List<int> escPosInit = [0x1B, 0x40];
const List<int> escPosPartialCut = [0x1D, 0x56, 0x41, 0x03];

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
