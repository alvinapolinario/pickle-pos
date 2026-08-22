import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:print_bluetooth_thermal/print_bluetooth_thermal.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'esc_pos.dart';

enum PrinterNotice { good, info, warn, bad }

class PrinterSnapshot {
  const PrinterSnapshot({
    this.name,
    this.mac,
    this.connected = false,
    this.bluetoothOn = false,
    this.permissionGranted = false,
    this.pluginReady = true,
    this.paired = const [],
    this.message,
    this.notice = PrinterNotice.info,
  });

  final String? name;
  final String? mac;
  final bool connected;
  final bool bluetoothOn;
  final bool permissionGranted;
  final bool pluginReady;
  final List<BluetoothInfo> paired;
  final String? message;
  final PrinterNotice notice;

  bool get hasSaved => mac != null && mac!.isNotEmpty;

  String get detail {
    if (!pluginReady) return 'Android tablet required';
    if (connected && name != null) return 'Connected · $name';
    if (hasSaved) return 'Saved · ${name ?? mac!}';
    return 'No printer saved';
  }

  PrinterSnapshot copyWith({
    String? name,
    String? mac,
    bool? connected,
    bool? bluetoothOn,
    bool? permissionGranted,
    bool? pluginReady,
    List<BluetoothInfo>? paired,
    String? message,
    PrinterNotice? notice,
    bool clearSaved = false,
    bool clearMessage = false,
  }) {
    return PrinterSnapshot(
      name: clearSaved ? null : (name ?? this.name),
      mac: clearSaved ? null : (mac ?? this.mac),
      connected: connected ?? this.connected,
      bluetoothOn: bluetoothOn ?? this.bluetoothOn,
      permissionGranted: permissionGranted ?? this.permissionGranted,
      pluginReady: pluginReady ?? this.pluginReady,
      paired: paired ?? this.paired,
      message: clearMessage ? null : (message ?? this.message),
      notice: clearMessage ? PrinterNotice.info : (notice ?? this.notice),
    );
  }
}

class PrinterController extends StateNotifier<PrinterSnapshot> {
  PrinterController() : super(const PrinterSnapshot()) {
    refresh();
  }

  Future<T?> _safe<T>(Future<T> Function() action) async {
    try {
      return await action();
    } catch (_) {
      return null;
    }
  }

  Future<void> refresh({bool autoReconnect = true}) async {
    final prefs = await SharedPreferences.getInstance();
    final mac = prefs.getString('printerMac');
    final name = prefs.getString('printerName');
    final permissionGranted = await _safe(() => PrintBluetoothThermal.isPermissionBluetoothGranted);
    if (permissionGranted == null) {
      state = state.copyWith(
        mac: mac,
        name: name,
        pluginReady: false,
        permissionGranted: false,
        bluetoothOn: false,
        connected: false,
      );
      return;
    }
    final bluetoothOn = await _safe(() => PrintBluetoothThermal.bluetoothEnabled) ?? false;
    var connected = await _safe(() => PrintBluetoothThermal.connectionStatus) ?? false;
    var paired = <BluetoothInfo>[];
    if (permissionGranted) {
      paired = await _safe(() => PrintBluetoothThermal.pairedBluetooths) ?? const [];
    }
    if (autoReconnect &&
        mac != null &&
        mac.isNotEmpty &&
        permissionGranted &&
        bluetoothOn &&
        !connected) {
      connected = await _safe(() => PrintBluetoothThermal.connect(macPrinterAddress: mac)) ?? false;
    }
    state = state.copyWith(
      mac: mac,
      name: name,
      pluginReady: true,
      permissionGranted: permissionGranted,
      bluetoothOn: bluetoothOn,
      connected: connected,
      paired: paired,
    );
  }

  Future<bool> ensurePermission() async {
    final granted = await _safe(() async {
      await [
        Permission.bluetooth,
        Permission.bluetoothConnect,
        Permission.bluetoothScan,
      ].request();
      return PrintBluetoothThermal.isPermissionBluetoothGranted;
    });
    if (granted == null) {
      state = state.copyWith(
        pluginReady: false,
        permissionGranted: false,
        message: 'Bluetooth printing is available on Android tablets.',
        notice: PrinterNotice.warn,
      );
      return false;
    }
    state = state.copyWith(permissionGranted: granted, pluginReady: true);
    return granted;
  }

  Future<void> loadPaired() async {
    if (!await ensurePermission()) {
      if (state.pluginReady) {
        state = state.copyWith(
          message: 'Allow Bluetooth so the register can find printers.',
          notice: PrinterNotice.warn,
        );
      }
      return;
    }
    final on = await _safe(() => PrintBluetoothThermal.bluetoothEnabled);
    if (on == null) {
      state = state.copyWith(
        pluginReady: false,
        message: 'Bluetooth printing is available on Android tablets.',
        notice: PrinterNotice.warn,
      );
      return;
    }
    if (!on) {
      state = state.copyWith(
        bluetoothOn: false,
        message: 'Turn on Bluetooth, then tap Refresh.',
        notice: PrinterNotice.warn,
      );
      return;
    }
    final paired = await _safe(() => PrintBluetoothThermal.pairedBluetooths);
    if (paired == null) {
      state = state.copyWith(
        message: 'Could not read paired devices. Try Refresh.',
        notice: PrinterNotice.bad,
      );
      return;
    }
    state = state.copyWith(
      bluetoothOn: true,
      paired: paired,
      message: paired.isEmpty
          ? 'No paired printers yet. Pair the printer in Android Bluetooth settings, then tap Refresh.'
          : null,
      notice: paired.isEmpty ? PrinterNotice.info : PrinterNotice.info,
      clearMessage: paired.isNotEmpty,
    );
  }

  Future<bool> connect(BluetoothInfo device) async {
    if (!await ensurePermission()) {
      if (state.pluginReady) {
        state = state.copyWith(message: 'Bluetooth permission is required.', notice: PrinterNotice.warn);
      }
      return false;
    }
    final ok = await _safe(() => PrintBluetoothThermal.connect(macPrinterAddress: device.macAdress));
    if (ok != true) {
      state = state.copyWith(
        connected: false,
        message: 'Could not connect to ${device.name}. Make sure it is on and in range.',
        notice: PrinterNotice.bad,
      );
      return false;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('printerMac', device.macAdress);
    await prefs.setString('printerName', device.name);
    state = state.copyWith(
      name: device.name,
      mac: device.macAdress,
      connected: true,
      message: 'Connected to ${device.name}.',
      notice: PrinterNotice.good,
    );
    return true;
  }

  Future<bool> reconnect() async {
    final mac = state.mac;
    if (mac == null || mac.isEmpty) return false;
    final already = await _safe(() => PrintBluetoothThermal.connectionStatus);
    if (already == true) {
      state = state.copyWith(connected: true, clearMessage: true);
      return true;
    }
    final ok = await _safe(() => PrintBluetoothThermal.connect(macPrinterAddress: mac));
    final success = ok == true;
    state = state.copyWith(
      connected: success,
      message: success
          ? 'Reconnected to ${state.name ?? 'printer'}.'
          : 'Printer is saved but not in range. Turn it on and tap Reconnect.',
      notice: success ? PrinterNotice.good : PrinterNotice.warn,
    );
    return success;
  }

  Future<void> forget() async {
    await _safe(() => PrintBluetoothThermal.disconnect);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('printerMac');
    await prefs.remove('printerName');
    state = state.copyWith(
      clearSaved: true,
      connected: false,
      message: 'Printer forgotten.',
      notice: PrinterNotice.info,
    );
  }

  Future<bool> printTicket(String text, {int copies = 1}) async {
    if (!state.hasSaved) {
      state = state.copyWith(
        message: 'Save a printer in More → Printers first.',
        notice: PrinterNotice.warn,
      );
      return false;
    }
    if (!await reconnect()) {
      return false;
    }
    final ok = await _safe(() => PrintBluetoothThermal.writeBytes(escPosTicket(text, copies: copies)));
    final success = ok == true;
    state = state.copyWith(
      message: success
          ? 'Sent to ${state.name}.'
          : 'Connected, but the printer did not accept the ticket. Try Reconnect.',
      notice: success ? PrinterNotice.good : PrinterNotice.bad,
    );
    return success;
  }

  Future<bool> printTest() {
    return printTicket(printerTestTicket(name: state.name ?? 'Thermal printer', mac: state.mac ?? ''));
  }

  Future<bool> verify() async {
    if (!await ensurePermission()) {
      if (state.pluginReady) {
        state = state.copyWith(
          message: 'Allow Bluetooth, then tap Verify again.',
          notice: PrinterNotice.warn,
        );
      }
      return false;
    }
    final on = await _safe(() => PrintBluetoothThermal.bluetoothEnabled);
    if (on != true) {
      state = state.copyWith(
        bluetoothOn: false,
        message: 'Turn on Bluetooth, then tap Verify.',
        notice: PrinterNotice.warn,
      );
      return false;
    }
    if (!state.hasSaved) {
      state = state.copyWith(
        bluetoothOn: true,
        message: 'Save a paired printer first, then tap Verify.',
        notice: PrinterNotice.warn,
      );
      return false;
    }
    if (!await reconnect()) {
      return false;
    }
    final ok = await printTest();
    if (ok) {
      state = state.copyWith(
        connected: true,
        bluetoothOn: true,
        message: 'Printer verified. ${state.name ?? 'Thermal printer'} is ready for receipts.',
        notice: PrinterNotice.good,
      );
    }
    return ok;
  }

  Future<void> openSystemSettings() async {
    await openAppSettings();
  }
}

final printerProvider = StateNotifierProvider<PrinterController, PrinterSnapshot>((ref) {
  return PrinterController();
});
