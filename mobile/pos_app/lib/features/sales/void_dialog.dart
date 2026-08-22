import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/network/api_client.dart';

class ManagerPasscode {
  const ManagerPasscode(this.passcode, {this.reason = ''});

  final String passcode;
  final String reason;
}

Future<ManagerPasscode?> askManagerPasscode(
  BuildContext context, {
  required String title,
  required String subtitle,
  required String actionLabel,
  bool askReason = true,
}) {
  return showModalBottomSheet<ManagerPasscode>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => _ManagerPasscodeSheet(
      title: title,
      subtitle: subtitle,
      actionLabel: actionLabel,
      askReason: askReason,
    ),
  );
}

Future<bool> confirmVoidSale(
  BuildContext context,
  WidgetRef ref, {
  required int saleId,
}) async {
  final result = await askManagerPasscode(
    context,
    title: 'Void receipt',
    subtitle: 'Enter the passcode from System Settings. Stock will be returned.',
    actionLabel: 'Void sale',
  );
  if (result == null || !context.mounted) return false;
  try {
    await ref.read(apiProvider).voidSale(saleId, passcode: result.passcode, reason: result.reason);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Receipt voided.')));
    }
    return true;
  } catch (error) {
    if (!context.mounted) return false;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_passcodeMessage(error, fallback: 'Could not void this receipt.'))));
    return false;
  }
}

String _passcodeMessage(Object error, {required String fallback}) {
  if (error is DioException) {
    final detail = error.response?.data;
    if (detail is Map && detail['detail'] != null) return '${detail['detail']}';
  }
  return fallback;
}

class _ManagerPasscodeSheet extends StatefulWidget {
  const _ManagerPasscodeSheet({
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    this.askReason = true,
  });

  final String title;
  final String subtitle;
  final String actionLabel;
  final bool askReason;

  @override
  State<_ManagerPasscodeSheet> createState() => _ManagerPasscodeSheetState();
}

class _ManagerPasscodeSheetState extends State<_ManagerPasscodeSheet> {
  final _passcode = TextEditingController();
  final _reason = TextEditingController();

  @override
  void dispose() {
    _passcode.dispose();
    _reason.dispose();
    super.dispose();
  }

  void _submit() {
    Navigator.pop(context, ManagerPasscode(_passcode.text.trim(), reason: _reason.text.trim()));
  }

  @override
  Widget build(BuildContext context) {
    final ready = _passcode.text.trim().length >= 4;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(20, 8, 20, 16 + MediaQuery.viewInsetsOf(context).bottom),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(widget.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 20, color: ink)),
            const SizedBox(height: 4),
            Text(widget.subtitle, style: const TextStyle(color: muted, fontWeight: FontWeight.w600)),
            const SizedBox(height: 16),
            TextField(
              controller: _passcode,
              obscureText: true,
              autofocus: true,
              keyboardType: TextInputType.visiblePassword,
              decoration: const InputDecoration(labelText: 'Passcode'),
              onChanged: (_) => setState(() {}),
              onSubmitted: (_) {
                if (ready) _submit();
              },
            ),
            if (widget.askReason) ...[
              const SizedBox(height: 10),
              TextField(
                controller: _reason,
                decoration: const InputDecoration(labelText: 'Reason (optional)'),
              ),
            ],
            const SizedBox(height: 16),
            FilledButton(
              onPressed: ready ? _submit : null,
              style: FilledButton.styleFrom(backgroundColor: red),
              child: Text(widget.actionLabel),
            ),
          ],
        ),
      ),
    );
  }
}
