String peso(dynamic value) {
  if (value == null || value == '') return '₱ —';
  final amount = value is num ? value.toDouble() : double.tryParse('$value');
  if (amount == null) return '₱ $value';
  final parts = amount.toStringAsFixed(2).split('.');
  final whole = parts[0];
  final buffer = StringBuffer();
  for (var i = 0; i < whole.length; i++) {
    final fromEnd = whole.length - i;
    buffer.write(whole[i]);
    if (fromEnd > 1 && fromEnd % 3 == 1) buffer.write(',');
  }
  return '₱ ${buffer.toString()}.${parts[1]}';
}

double asMoney(dynamic value) {
  if (value is num) return value.toDouble();
  return double.tryParse('$value') ?? 0;
}
