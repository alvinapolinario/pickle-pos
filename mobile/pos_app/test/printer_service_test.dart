import 'package:flutter_test/flutter_test.dart';
import 'package:pos_app/core/printing/esc_pos.dart';
import 'package:pos_app/core/printing/printer_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('snapshot detail describes connection state', () {
    expect(const PrinterSnapshot().detail, 'No printer saved');
    expect(const PrinterSnapshot(pluginReady: false).detail, 'Android tablet required');
    expect(
      const PrinterSnapshot(name: 'Xprinter', mac: 'AA:BB', connected: true).detail,
      'Connected · Xprinter',
    );
    expect(
      const PrinterSnapshot(name: 'Xprinter', mac: 'AA:BB').detail,
      'Saved · Xprinter',
    );
  });

  test('printTicket fails when no printer is saved', () async {
    SharedPreferences.setMockInitialValues({});
    final controller = PrinterController();
    await Future<void>.delayed(Duration.zero);
    expect(await controller.printTicket('hello'), isFalse);
    expect(controller.state.notice, PrinterNotice.warn);
  });

  test('forget clears saved printer prefs', () async {
    SharedPreferences.setMockInitialValues({
      'printerMac': 'AA:BB:CC:DD:EE:FF',
      'printerName': 'Xprinter',
    });
    final controller = PrinterController();
    await controller.refresh(autoReconnect: false);
    expect(controller.state.hasSaved, isTrue);
    expect(controller.state.name, 'Xprinter');
    await controller.forget();
    expect(controller.state.hasSaved, isFalse);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('printerMac'), isNull);
  });

  test('verify fails safely when the Bluetooth plugin is unavailable', () async {
    SharedPreferences.setMockInitialValues({});
    final controller = PrinterController();
    await Future<void>.delayed(Duration.zero);
    expect(await controller.verify(), isFalse);
    expect(controller.state.message, isNotNull);
  });

  test('test ticket is valid ESC/POS', () {
    final bytes = escPosTicket(printerTestTicket(name: 'Xprinter', mac: 'AA:BB'));
    expect(bytes.take(2), escPosInit);
    expect(containsBytes(bytes, escPosPartialCut), isTrue);
  });
}
