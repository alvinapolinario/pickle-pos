import 'dart:convert';

class PosPairing {
  const PosPairing({required this.url, required this.key});

  final String url;
  final String key;

  static PosPairing? tryParse(String raw) {
    final text = raw.trim();
    if (text.isEmpty) return null;

    if (text.startsWith('{')) {
      try {
        final data = jsonDecode(text);
        if (data is Map) {
          return _fromParts(data['url']?.toString(), data['key']?.toString());
        }
      } catch (_) {
        return null;
      }
      return null;
    }

    final uri = Uri.tryParse(text);
    if (uri == null) return null;
    if (uri.scheme == 'picklepos' && uri.host == 'connect') {
      return _fromParts(uri.queryParameters['url'], uri.queryParameters['key']);
    }
    if (uri.queryParameters.containsKey('url') && uri.queryParameters.containsKey('key')) {
      return _fromParts(uri.queryParameters['url'], uri.queryParameters['key']);
    }
    return null;
  }

  static PosPairing? _fromParts(String? url, String? key) {
    final cleanUrl = (url ?? '').trim().replaceAll(RegExp(r'/+$'), '');
    final cleanKey = (key ?? '').trim();
    if (cleanUrl.isEmpty || cleanKey.isEmpty) return null;
    return PosPairing(url: cleanUrl, key: cleanKey);
  }
}
