import '../core/network/api_client.dart';

/// Thin wrapper around the offline sale queue.
class SyncEngine {
  SyncEngine(this.api);

  final ApiClient api;

  Future<List<String>> pushQueue() => api.syncPending();

  void scheduleRetry() => api.scheduleSyncRetry();
}
