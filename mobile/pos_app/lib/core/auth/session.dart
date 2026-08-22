import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class Session {
  const Session({
    this.baseUrl = 'http://10.0.2.2:7101',
    this.accessToken,
    this.refreshToken,
    this.username,
    this.deviceCode = 'POS-001',
    this.deviceId,
    this.shiftId,
  });

  final String baseUrl;
  final String? accessToken;
  final String? refreshToken;
  final String? username;
  final String deviceCode;
  final int? deviceId;
  final int? shiftId;

  Session copyWith({
    String? baseUrl,
    String? accessToken,
    String? refreshToken,
    String? username,
    String? deviceCode,
    int? deviceId,
    int? shiftId,
    bool clearTokens = false,
    bool clearShift = false,
  }) {
    return Session(
      baseUrl: baseUrl ?? this.baseUrl,
      accessToken: clearTokens ? null : (accessToken ?? this.accessToken),
      refreshToken: clearTokens ? null : (refreshToken ?? this.refreshToken),
      username: clearTokens ? null : (username ?? this.username),
      deviceCode: deviceCode ?? this.deviceCode,
      deviceId: deviceId ?? this.deviceId,
      shiftId: clearShift ? null : (shiftId ?? this.shiftId),
    );
  }
}

class SessionNotifier extends StateNotifier<Session> {
  SessionNotifier() : super(const Session()) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    state = Session(
      baseUrl: prefs.getString('baseUrl') ?? state.baseUrl,
      accessToken: prefs.getString('accessToken'),
      refreshToken: prefs.getString('refreshToken'),
      username: prefs.getString('username'),
      deviceCode: prefs.getString('deviceCode') ?? 'POS-001',
      deviceId: prefs.getInt('deviceId'),
      shiftId: prefs.getInt('shiftId'),
    );
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('baseUrl', state.baseUrl);
    await prefs.setString('deviceCode', state.deviceCode);
    if (state.accessToken == null) {
      await prefs.remove('accessToken');
    } else {
      await prefs.setString('accessToken', state.accessToken!);
    }
    if (state.refreshToken == null) {
      await prefs.remove('refreshToken');
    } else {
      await prefs.setString('refreshToken', state.refreshToken!);
    }
    if (state.username == null) {
      await prefs.remove('username');
    } else {
      await prefs.setString('username', state.username!);
    }
    if (state.deviceId == null) {
      await prefs.remove('deviceId');
    } else {
      await prefs.setInt('deviceId', state.deviceId!);
    }
    if (state.shiftId == null) {
      await prefs.remove('shiftId');
    } else {
      await prefs.setInt('shiftId', state.shiftId!);
    }
  }

  Future<void> updateBaseUrl(String url) async {
    state = state.copyWith(baseUrl: url);
    await _persist();
  }

  Future<void> updateDeviceCode(String code) async {
    state = state.copyWith(deviceCode: code);
    await _persist();
  }

  Future<void> signedIn({
    required String accessToken,
    required String refreshToken,
    required String username,
    int? deviceId,
  }) async {
    state = state.copyWith(
      accessToken: accessToken,
      refreshToken: refreshToken,
      username: username,
      deviceId: deviceId,
    );
    await _persist();
  }

  Future<void> setShift(int? shiftId) async {
    state = state.copyWith(shiftId: shiftId, clearShift: shiftId == null);
    await _persist();
  }

  Future<void> signOut() async {
    state = state.copyWith(clearTokens: true, clearShift: true);
    await _persist();
  }
}

final sessionProvider = StateNotifierProvider<SessionNotifier, Session>((ref) {
  return SessionNotifier();
});
