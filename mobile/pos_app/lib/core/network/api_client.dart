import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../auth/session.dart';

final apiProvider = Provider<ApiClient>((ref) => ApiClient(ref));

class ApiClient {
  ApiClient(this.ref) {
    _dio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 20),
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final session = ref.read(sessionProvider);
          options.baseUrl = '${session.baseUrl}/api/v1';
          if (session.apiKey.isNotEmpty) {
            options.headers['X-Api-Key'] = session.apiKey;
          }
          if (session.accessToken != null) {
            options.headers['Authorization'] = 'Bearer ${session.accessToken}';
          }
          handler.next(options);
        },
      ),
    );
  }

  final Ref ref;
  late final Dio _dio;
  int _syncAttempt = 0;
  Timer? _syncTimer;

  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await _dio.post(
      '/auth/login',
      data: {
        'username': username,
        'password': password,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> registerDevice() async {
    final session = ref.read(sessionProvider);
    final response = await _dio.post(
      '/devices/register',
      data: {'device_code': session.deviceCode, 'name': session.deviceCode},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>?> currentShift() async {
    try {
      final response = await _dio.get('/shifts/current');
      return Map<String, dynamic>.from(response.data as Map);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<Map<String, dynamic>> openShift(String openingCash) async {
    final response = await _dio.post('/shifts/open', data: {'opening_cash': openingCash});
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> closeShift(int shiftId, String actualCash) async {
    final response = await _dio.post(
      '/shifts/close',
      data: {'shift_id': shiftId, 'actual_cash': actualCash},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<List<dynamic>> categories() async {
    try {
      final response = await _dio.get('/categories');
      final data = response.data as List<dynamic>;
      await _cacheJson('catalog_categories', data);
      return data;
    } on DioException {
      return await _cachedList('catalog_categories');
    }
  }

  Future<List<dynamic>> products({int? categoryId, String? q}) async {
    try {
      final response = await _dio.get(
        '/products',
        queryParameters: {
          if (categoryId != null) 'category_id': categoryId,
          if (q != null && q.isNotEmpty) 'q': q,
        },
      );
      final data = response.data as List<dynamic>;
      if (categoryId == null && (q == null || q.isEmpty)) {
        await _cacheJson('catalog_products', data);
      }
      return data;
    } on DioException {
      var cached = await _cachedList('catalog_products');
      if (categoryId != null) {
        cached = cached.where((row) => (row as Map)['category_id'] == categoryId).toList();
      }
      if (q != null && q.isNotEmpty) {
        final needle = q.toLowerCase();
        cached = cached.where((row) {
          final item = row as Map;
          return '${item['name']}'.toLowerCase().contains(needle) ||
              '${item['sku']}'.toLowerCase().contains(needle) ||
              '${item['barcode']}'.toLowerCase().contains(needle);
        }).toList();
      }
      if (cached.isEmpty) rethrow;
      return cached;
    }
  }

  Future<Map<String, dynamic>?> lookupProduct(String code) async {
    try {
      final response = await _dio.get('/products/lookup', queryParameters: {'code': code});
      return Map<String, dynamic>.from(response.data as Map);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) return null;
      final needle = code.toLowerCase();
      for (final row in await _cachedList('catalog_products')) {
        final item = Map<String, dynamic>.from(row as Map);
        if ('${item['barcode']}'.toLowerCase() == needle || '${item['sku']}'.toLowerCase() == needle) {
          return item;
        }
      }
      return null;
    }
  }

  Future<List<dynamic>> customers({String? q}) async {
    final response = await _dio.get(
      '/customers',
      queryParameters: {if (q != null && q.isNotEmpty) 'q': q},
    );
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>?> customer(int customerId) async {
    try {
      final response = await _dio.get('/customers/$customerId');
      return Map<String, dynamic>.from(response.data as Map);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<Map<String, dynamic>> createCustomer({required String name, String mobile = '', String email = ''}) async {
    final response = await _dio.post(
      '/customers',
      data: {
        'name': name,
        if (mobile.isNotEmpty) 'mobile': mobile,
        if (email.isNotEmpty) 'email': email,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> quote(List<Map<String, dynamic>> items, {String discount = '0', int? customerId}) async {
    final response = await _dio.post(
      '/sales/quote',
      data: {
        'items': items,
        'discount_amount': discount,
        if (customerId != null) 'customer_id': customerId,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> createSale({
    required int shiftId,
    required List<Map<String, dynamic>> items,
    required List<Map<String, dynamic>> payments,
    required String clientSaleUuid,
    int? deviceId,
    int? customerId,
    String discount = '0',
    bool hold = false,
  }) async {
    final path = hold ? '/sales/hold' : '/sales';
    final payload = {
      'shift_id': shiftId,
      'items': items,
      'discount_amount': discount,
      'client_sale_uuid': clientSaleUuid,
      if (deviceId != null) 'device_id': deviceId,
      if (customerId != null) 'customer_id': customerId,
      if (!hold) 'payments': payments,
    };
    try {
      final response = await _dio.post(path, data: payload);
      return Map<String, dynamic>.from(response.data as Map);
    } on DioException {
      await enqueueSale({...payload, 'hold': hold, 'client_sale_uuid': clientSaleUuid});
      scheduleSyncRetry();
      rethrow;
    }
  }

  Future<List<dynamic>> sales({String? status}) async {
    final response = await _dio.get('/sales', queryParameters: {if (status != null) 'status': status});
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> sale(int saleId) async {
    final response = await _dio.get('/sales/$saleId');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<List<dynamic>> balances() async {
    final response = await _dio.get('/inventory/balances');
    return response.data as List<dynamic>;
  }

  Future<void> cashMove({required int shiftId, required String amount, required bool cashIn, String reason = ''}) async {
    final path = cashIn ? '/shifts/$shiftId/cash-in' : '/shifts/$shiftId/cash-out';
    await _dio.post(path, data: {'amount': amount, 'reason': reason});
  }

  Future<Map<String, dynamic>> branchSettings() async {
    final response = await _dio.get('/settings');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> updateBranchSettings({required bool vatRegistered}) async {
    final response = await _dio.patch('/settings', data: {'vat_registered': vatRegistered});
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> receipt(int saleId) async {
    final response = await _dio.get('/sales/$saleId/receipt');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> resumeSale(int saleId, List<Map<String, dynamic>> payments) async {
    final response = await _dio.post('/sales/hold/$saleId/resume', data: {'payments': payments});
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> voidSale(int saleId, {required String passcode, String reason = 'Voided from POS'}) async {
    final response = await _dio.post(
      '/sales/$saleId/void',
      data: {'reason': reason, 'passcode': passcode},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> refundSale({
    required int saleId,
    required int shiftId,
    required List<Map<String, dynamic>> lines,
    required String method,
    required String passcode,
    String reason = '',
  }) async {
    final response = await _dio.post(
      '/sales/$saleId/refund',
      data: {
        'shift_id': shiftId,
        'lines': lines,
        'method': method,
        'reason': reason,
        'passcode': passcode,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<void> enqueueSale(Map<String, dynamic> sale) async {
    final prefs = await SharedPreferences.getInstance();
    final pending = prefs.getStringList('pending_sales') ?? [];
    pending.add(jsonEncode(sale));
    await prefs.setStringList('pending_sales', pending);
  }

  Future<int> pendingCount() async {
    final prefs = await SharedPreferences.getInstance();
    return (prefs.getStringList('pending_sales') ?? []).length;
  }

  Future<List<String>> syncPending() async {
    final prefs = await SharedPreferences.getInstance();
    final pending = prefs.getStringList('pending_sales') ?? [];
    if (pending.isEmpty) return [];
    final session = ref.read(sessionProvider);
    if (session.deviceId == null) {
      throw Exception('Register this device before syncing.');
    }
    final sales = pending.map((row) => jsonDecode(row) as Map<String, dynamic>).toList();
    final response = await _dio.post(
      '/sync/push',
      data: {'device_id': session.deviceId, 'sales': sales},
    );
    final results = (response.data['results'] as List<dynamic>).cast<Map>();
    final leftover = <String>[];
    for (var i = 0; i < results.length; i++) {
      final status = results[i]['status'];
      if (status != 'synced') leftover.add(pending[i]);
    }
    await prefs.setStringList('pending_sales', leftover);
    if (leftover.isEmpty) {
      _syncAttempt = 0;
      _syncTimer?.cancel();
    } else {
      scheduleSyncRetry();
    }
    return leftover;
  }

  void scheduleSyncRetry() {
    _syncAttempt = max(_syncAttempt, 1);
    final seconds = min(300, pow(2, _syncAttempt).toInt());
    _syncAttempt += 1;
    _syncTimer?.cancel();
    _syncTimer = Timer(Duration(seconds: seconds), () async {
      try {
        await syncPending();
      } catch (_) {
        scheduleSyncRetry();
      }
    });
  }

  Future<void> _cacheJson(String key, List<dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, jsonEncode(data));
  }

  Future<List<dynamic>> _cachedList(String key) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(key);
    if (raw == null || raw.isEmpty) return [];
    return jsonDecode(raw) as List<dynamic>;
  }

  Future<List<dynamic>> courts() async {
    final response = await _dio.get('/courts');
    return response.data as List<dynamic>;
  }

  Future<List<dynamic>> bookings({DateTime? date, int? courtId}) async {
    final response = await _dio.get(
      '/bookings',
      queryParameters: {
        if (date != null) 'date': '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}',
        if (courtId != null) 'court_id': courtId,
      },
    );
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> quoteBooking({
    required int courtId,
    required DateTime startAt,
    required DateTime endAt,
    int? customerId,
  }) async {
    final response = await _dio.post(
      '/bookings/quote',
      data: {
        'court_id': courtId,
        'start_at': startAt.toUtc().toIso8601String(),
        'end_at': endAt.toUtc().toIso8601String(),
        if (customerId != null) 'customer_id': customerId,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> createBooking({
    required int courtId,
    required DateTime startAt,
    required DateTime endAt,
    String paymentMethod = 'cash',
    String notes = '',
    int? customerId,
  }) async {
    final response = await _dio.post(
      '/bookings',
      data: {
        'court_id': courtId,
        'start_at': startAt.toUtc().toIso8601String(),
        'end_at': endAt.toUtc().toIso8601String(),
        'payment_method': paymentMethod,
        'notes': notes,
        if (customerId != null) 'customer_id': customerId,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> cancelBooking(int bookingId) async {
    final response = await _dio.post('/bookings/$bookingId/cancel');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> refundBooking(int bookingId, {String method = 'cash', String reason = ''}) async {
    final response = await _dio.post(
      '/bookings/$bookingId/refund',
      data: {'method': method, 'reason': reason},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  String newSaleUuid() => const Uuid().v4();
}
