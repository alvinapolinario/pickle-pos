import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/printing/printer_service.dart';
import '../../ui/widgets.dart';

class PrintersScreen extends ConsumerStatefulWidget {
  const PrintersScreen({super.key});

  @override
  ConsumerState<PrintersScreen> createState() => _PrintersScreenState();
}

class _PrintersScreenState extends ConsumerState<PrintersScreen> {
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      await ref.read(printerProvider.notifier).refresh();
      await ref.read(printerProvider.notifier).loadPaired();
    });
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  StatusTone _tone(PrinterNotice notice) {
    return switch (notice) {
      PrinterNotice.good => StatusTone.good,
      PrinterNotice.warn => StatusTone.warn,
      PrinterNotice.bad => StatusTone.bad,
      PrinterNotice.info => StatusTone.info,
    };
  }

  @override
  Widget build(BuildContext context) {
    final printer = ref.watch(printerProvider);
    final controller = ref.read(printerProvider.notifier);
    return Scaffold(
      appBar: AppBar(title: const Text('Printers')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          PosCard(
            child: Row(
              children: [
                CircleAvatar(
                  backgroundColor: printer.connected ? accentSoft : const Color(0xFFF1F4F8),
                  child: Icon(
                    Icons.print_outlined,
                    color: printer.connected ? accent : muted,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        printer.hasSaved ? (printer.name ?? 'Thermal printer') : 'No printer saved',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: ink),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        printer.connected
                            ? 'Ready · ${printer.mac}'
                            : printer.hasSaved
                                ? 'Saved · turn the printer on, then tap Reconnect'
                                : 'Pair a 58mm or 80mm ESC/POS printer, then pick it below.',
                        style: const TextStyle(color: muted),
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          StatusPill(
                            label: printer.connected ? 'Connected' : 'Not connected',
                            tone: printer.connected ? StatusTone.good : StatusTone.neutral,
                          ),
                          StatusPill(
                            label: printer.bluetoothOn ? 'Bluetooth on' : 'Bluetooth off',
                            tone: printer.bluetoothOn ? StatusTone.good : StatusTone.warn,
                          ),
                          if (printer.hasSaved)
                            const StatusPill(label: 'Saved', tone: StatusTone.info),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (!printer.pluginReady)
            SoftBanner(
              message: 'Bluetooth printing runs on an Android tablet. Share still copies the ticket.',
              tone: StatusTone.info,
              margin: const EdgeInsets.only(top: 12),
            )
          else if (printer.message != null)
            SoftBanner(
              message: printer.message!,
              tone: _tone(printer.notice),
              margin: const EdgeInsets.only(top: 12),
              actionLabel: printer.permissionGranted ? null : 'Settings',
              onAction: printer.permissionGranted ? null : () => controller.openSystemSettings(),
            ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _busy ? null : () => _run(controller.loadPaired),
                  child: const Text('Refresh'),
                ),
              ),
              if (printer.hasSaved) ...[
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton(
                    onPressed: _busy ? null : () => _run(() async { await controller.reconnect(); }),
                    child: const Text('Reconnect'),
                  ),
                ),
              ],
            ],
          ),
          if (printer.hasSaved) ...[
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: _busy ? null : () => _run(() async { await controller.verify(); }),
              icon: const Icon(Icons.verified_outlined),
              label: const Text('Verify printer'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _busy ? null : () => _run(() async { await controller.printTest(); }),
              icon: const Icon(Icons.receipt_long_outlined),
              label: const Text('Test print'),
            ),
            TextButton(
              onPressed: _busy ? null : () => _run(controller.forget),
              child: const Text('Forget printer'),
            ),
          ],
          const SizedBox(height: 8),
          const SectionLabel('How to connect'),
          const SizedBox(height: 8),
          const PosCard(
            child: Column(
              children: [
                _Step(number: '1', text: 'Turn on the thermal printer and put it in pairing mode.'),
                SizedBox(height: 10),
                _Step(number: '2', text: 'On this tablet, open Android Bluetooth settings and pair it once.'),
                SizedBox(height: 10),
                _Step(number: '3', text: 'Return here, tap Refresh, then tap the printer to save it.'),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Paired devices'),
          const SizedBox(height: 8),
          PosCard(
            padding: EdgeInsets.zero,
            child: printer.paired.isEmpty
                ? const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'Nothing paired yet. After you pair the printer in Android Bluetooth settings, tap Refresh.',
                      style: TextStyle(color: muted, height: 1.45),
                    ),
                  )
                : Column(
                    children: [
                      for (var i = 0; i < printer.paired.length; i++) ...[
                        if (i > 0) const Divider(height: 1),
                        ListTile(
                          leading: Icon(
                            printer.mac == printer.paired[i].macAdress ? Icons.check_circle : Icons.print_outlined,
                            color: printer.mac == printer.paired[i].macAdress ? accent : muted,
                          ),
                          title: Text(printer.paired[i].name, style: const TextStyle(fontWeight: FontWeight.w700)),
                          subtitle: Text(printer.paired[i].macAdress, style: const TextStyle(color: muted)),
                          trailing: printer.mac == printer.paired[i].macAdress
                              ? const StatusPill(label: 'Saved', tone: StatusTone.good)
                              : TextButton(
                                  onPressed: _busy
                                      ? null
                                      : () => _run(() => controller.connect(printer.paired[i])),
                                  child: const Text('Use'),
                                ),
                          onTap: _busy ? null : () => _run(() => controller.connect(printer.paired[i])),
                        ),
                      ],
                    ],
                  ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Works with common ESC/POS Bluetooth printers (Xprinter, Epson TM, Rongta, and similar). Once saved, receipts print from the ticket screen.',
            style: TextStyle(color: muted, height: 1.45),
          ),
        ],
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.number, required this.text});

  final String number;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 24,
          height: 24,
          alignment: Alignment.center,
          decoration: const BoxDecoration(color: accentSoft, shape: BoxShape.circle),
          child: Text(number, style: const TextStyle(color: accent, fontWeight: FontWeight.w800, fontSize: 12)),
        ),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: const TextStyle(color: ink, height: 1.4))),
      ],
    );
  }
}
