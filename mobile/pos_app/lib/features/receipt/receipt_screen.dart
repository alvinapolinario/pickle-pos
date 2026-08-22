import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../core/printing/printer_service.dart';
import '../../ui/widgets.dart';
import '../sales/void_dialog.dart';

class ReceiptScreen extends ConsumerStatefulWidget {
  const ReceiptScreen({super.key, required this.saleId});

  final int saleId;

  @override
  ConsumerState<ReceiptScreen> createState() => _ReceiptScreenState();
}

class _ReceiptScreenState extends ConsumerState<ReceiptScreen> {
  Map<String, dynamic>? _receipt;
  String? _error;
  bool _printing = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _print(String text) async {
    if (text.trim().isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Nothing to print on this ticket.')),
        );
      }
      return;
    }
    await ref.read(printerProvider.notifier).refresh();
    if (!mounted) return;
    if (!ref.read(printerProvider).hasSaved) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Choose a Bluetooth printer first.')),
      );
      context.push('/printers');
      return;
    }
    setState(() => _printing = true);
    final ok = await ref.read(printerProvider.notifier).printTicket(
          text,
          qrData: '${_receipt?['qr_payload'] ?? _receipt?['receipt_number'] ?? ''}',
        );
    if (!mounted) return;
    setState(() => _printing = false);
    final message = ref.read(printerProvider).message ?? (ok ? 'Sent to printer.' : 'Print failed.');
    if (!ok) {
      await Clipboard.setData(ClipboardData(text: text));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$message Copied the ticket so you can paste it.')),
      );
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _load() async {
    try {
      final receipt = await ref.read(apiProvider).receipt(widget.saleId);
      if (!mounted) return;
      setState(() => _receipt = receipt);
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not load receipt.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final receipt = _receipt;
    final lines = (receipt?['lines'] as List<dynamic>? ?? const []).cast<dynamic>();

    return Scaffold(
      appBar: AppBar(title: const Text('Receipt')),
      body: receipt == null
          ? Center(child: _error == null ? const CircularProgressIndicator() : Text(_error!, style: const TextStyle(color: red)))
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                const SizedBox(height: 8),
                Center(
                  child: Container(
                    width: 72,
                    height: 72,
                    decoration: const BoxDecoration(color: accentSoft, shape: BoxShape.circle),
                    child: const Icon(Icons.check_rounded, color: accent, size: 40),
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  '${receipt['branch_name'] ?? ''}'.trim().isEmpty ? 'Sale completed!' : '${receipt['branch_name']}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 24, color: ink),
                ),
                if ('${receipt['branch_address'] ?? ''}'.trim().isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    '${receipt['branch_address']}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: muted, fontWeight: FontWeight.w600),
                  ),
                ],
                const SizedBox(height: 4),
                Text(
                  '${receipt['receipt_number']} · ${receipt['sold_at']}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: muted, fontWeight: FontWeight.w600),
                ),
                if ('${receipt['customer'] ?? ''}'.trim().isNotEmpty && '${receipt['customer']}' != 'Walk-in') ...[
                  const SizedBox(height: 4),
                  Text(
                    '${receipt['customer']}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: accent, fontWeight: FontWeight.w700),
                  ),
                ],
                const SizedBox(height: 18),
                PosCard(
                  child: Column(
                    children: [
                      for (final line in lines)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  '${line['quantity']}× ${line['name']}',
                                  style: const TextStyle(fontWeight: FontWeight.w700),
                                ),
                              ),
                              MoneyText(line['line_net'], size: 15),
                            ],
                          ),
                        ),
                      const Divider(),
                      if (receipt['vat_registered'] != false) ...[
                        _row('VAT', receipt['tax_amount']),
                        const SizedBox(height: 6),
                      ],
                      _row('Total', receipt['net_amount'], emphasize: true),
                      const SizedBox(height: 6),
                      _row('Change', receipt['change_amount'], color: accent),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _printing ? null : () => _print(receipt['text']?.toString() ?? ''),
                        icon: _printing
                            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.print_outlined),
                        label: Text(ref.watch(printerProvider).hasSaved ? 'Print' : 'Set printer'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () async {
                          await Clipboard.setData(ClipboardData(text: '${receipt['text']}'));
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Receipt copied.')),
                            );
                          }
                        },
                        icon: const Icon(Icons.ios_share),
                        label: const Text('Share'),
                      ),
                    ),
                  ],
                ),
                if ('${receipt['status']}' == 'completed') ...[
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: _printing
                        ? null
                        : () async {
                            final voided = await confirmVoidSale(context, ref, saleId: widget.saleId);
                            if (voided) await _load();
                          },
                    icon: const Icon(Icons.block, color: red),
                    label: const Text('Void receipt'),
                    style: OutlinedButton.styleFrom(foregroundColor: red),
                  ),
                ],
                if ('${receipt['status']}' == 'void') ...[
                  const SizedBox(height: 10),
                  const SoftBanner(message: 'This receipt has been voided.', tone: StatusTone.bad, margin: EdgeInsets.zero),
                ],
                const SizedBox(height: 10),
                FilledButton(
                  onPressed: () => context.go('/pos'),
                  child: const Text('New sale'),
                ),
              ],
            ),
    );
  }

  Widget _row(String label, dynamic value, {bool emphasize = false, Color? color}) {
    return Row(
      children: [
        Text(label, style: TextStyle(color: muted, fontWeight: emphasize ? FontWeight.w800 : FontWeight.w600)),
        const Spacer(),
        MoneyText(value, size: emphasize ? 20 : 15, color: color ?? ink),
      ],
    );
  }
}
