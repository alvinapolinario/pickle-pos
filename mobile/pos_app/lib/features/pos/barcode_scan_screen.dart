import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../ui/widgets.dart';
import 'cart_controller.dart';

class BarcodeScanScreen extends ConsumerStatefulWidget {
  const BarcodeScanScreen({super.key});

  @override
  ConsumerState<BarcodeScanScreen> createState() => _BarcodeScanScreenState();
}

class _BarcodeScanScreenState extends ConsumerState<BarcodeScanScreen> {
  final MobileScannerController _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.normal,
    detectionTimeoutMs: 800,
    formats: const [
      BarcodeFormat.ean13,
      BarcodeFormat.ean8,
      BarcodeFormat.upcA,
      BarcodeFormat.upcE,
      BarcodeFormat.code128,
      BarcodeFormat.code39,
      BarcodeFormat.itf14,
      BarcodeFormat.codabar,
      BarcodeFormat.qrCode,
    ],
  );

  String? _lastCode;
  DateTime? _lastAt;
  String? _status;
  StatusTone _tone = StatusTone.info;
  bool _busy = false;

  @override
  void dispose() {
    unawaited(_controller.dispose());
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    final code = capture.barcodes
        .map((barcode) => barcode.rawValue?.trim() ?? '')
        .firstWhere((value) => value.isNotEmpty, orElse: () => '');
    if (code.isEmpty || _busy) return;

    final now = DateTime.now();
    if (_lastCode == code && _lastAt != null && now.difference(_lastAt!) < const Duration(milliseconds: 1400)) {
      return;
    }
    _lastCode = code;
    _lastAt = now;

    if (ref.read(sessionProvider).shiftId == null) {
      setState(() {
        _status = 'Open a shift before scanning.';
        _tone = StatusTone.warn;
      });
      return;
    }

    setState(() {
      _busy = true;
      _status = 'Looking up $code…';
      _tone = StatusTone.info;
    });

    try {
      final product = await ref.read(apiProvider).lookupProduct(code);
      if (!mounted) return;
      if (product == null) {
        HapticFeedback.heavyImpact();
        setState(() {
          _status = 'No product for $code';
          _tone = StatusTone.bad;
        });
        return;
      }
      HapticFeedback.mediumImpact();
      SystemSound.play(SystemSoundType.click);
      ref.read(cartProvider.notifier).add(product);
      setState(() {
        _status = 'Added ${product['name']}';
        _tone = StatusTone.good;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _status = 'Lookup failed. Check the API connection.';
        _tone = StatusTone.bad;
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = ref.watch(cartProvider);
    final items = cart.fold<int>(0, (sum, line) => sum + line.qty);

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: const Text('Scan barcode'),
        actions: [
          IconButton(
            onPressed: () => _controller.toggleTorch(),
            icon: const Icon(Icons.flash_on_outlined),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Stack(
              fit: StackFit.expand,
              children: [
                MobileScanner(
                  controller: _controller,
                  onDetect: _onDetect,
                  errorBuilder: (context, error) {
                    return ColoredBox(
                      color: navy,
                      child: EmptyState(
                        icon: Icons.photo_camera_outlined,
                        title: 'Camera unavailable',
                        detail: error.errorCode == MobileScannerErrorCode.permissionDenied
                            ? 'Allow camera access so the register can scan barcodes.'
                            : 'This device could not start the camera. Use the search field with a USB scanner instead.',
                      ),
                    );
                  },
                ),
                IgnorePointer(
                  child: Center(
                    child: Container(
                      width: 240,
                      height: 160,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: Colors.white, width: 2),
                      ),
                    ),
                  ),
                ),
                const Positioned(
                  left: 24,
                  right: 24,
                  bottom: 20,
                  child: Text(
                    'Point the camera at a barcode. Keep scanning to add more.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
          Container(
            width: double.infinity,
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
            child: SafeArea(
              top: false,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      const Text('Cart', style: TextStyle(fontWeight: FontWeight.w800, color: ink)),
                      const Spacer(),
                      StatusPill(label: '$items item${items == 1 ? '' : 's'}', tone: StatusTone.info),
                    ],
                  ),
                  if (_status != null) SoftBanner(message: _status!, tone: _tone, margin: const EdgeInsets.only(top: 12)),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Done'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
