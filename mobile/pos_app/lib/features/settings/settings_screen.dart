import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../ui/widgets.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  late final TextEditingController _url;
  late final TextEditingController _device;
  String? _message;
  StatusTone _tone = StatusTone.info;
  int _pending = 0;
  bool _vatRegistered = true;
  bool _vatLoading = true;

  @override
  void initState() {
    super.initState();
    final session = ref.read(sessionProvider);
    _url = TextEditingController(text: session.baseUrl);
    _device = TextEditingController(text: session.deviceCode);
    ref.read(apiProvider).pendingCount().then((count) {
      if (mounted) setState(() => _pending = count);
    });
    ref.read(apiProvider).branchSettings().then((settings) {
      if (mounted) {
        setState(() {
          _vatRegistered = settings['vat_registered'] == true;
          _vatLoading = false;
        });
      }
    }).catchError((_) {
      if (mounted) setState(() => _vatLoading = false);
    });
  }

  @override
  void dispose() {
    _url.dispose();
    _device.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          PosCard(
            child: Row(
              children: [
                CircleAvatar(
                  radius: 26,
                  backgroundColor: accentSoft,
                  child: Text(
                    (session.username ?? 'C')[0].toUpperCase(),
                    style: const TextStyle(color: accent, fontWeight: FontWeight.w800, fontSize: 20),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        session.username ?? 'Cashier',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18, color: ink),
                      ),
                      const SizedBox(height: 2),
                      const StatusPill(label: 'Online', tone: StatusTone.good),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          PosCard(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                MenuRow(
                  icon: Icons.schedule_outlined,
                  label: 'Shift',
                  detail: session.shiftId == null ? 'Closed' : 'Shift #${session.shiftId}',
                  onTap: () => context.go('/shift'),
                ),
                const Divider(),
                MenuRow(
                  icon: Icons.print_outlined,
                  label: 'Printers',
                  detail: 'Copy receipt into a printer app',
                  onTap: () => ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Use Print on a receipt to copy thermal text. Bluetooth pairing waits for a physical printer.')),
                  ),
                ),
                const Divider(),
                MenuRow(
                  icon: Icons.sync,
                  label: 'Sync status',
                  detail: _pending == 0 ? 'Queue is clear' : '$_pending pending',
                  onTap: () async {
                    try {
                      final leftover = await ref.read(apiProvider).syncPending();
                      setState(() {
                        _pending = leftover.length;
                        _message = leftover.isEmpty ? 'Queue synced.' : '${leftover.length} still pending.';
                        _tone = leftover.isEmpty ? StatusTone.good : StatusTone.warn;
                      });
                    } catch (_) {
                      setState(() {
                        _message = 'Sync failed.';
                        _tone = StatusTone.bad;
                      });
                    }
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Tax'),
          const SizedBox(height: 8),
          PosCard(
            padding: EdgeInsets.zero,
            child: SwitchListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              title: const Text('VAT registered', style: TextStyle(fontWeight: FontWeight.w800, color: ink)),
              subtitle: Text(
                _vatRegistered
                    ? 'Receipts extract 12% VAT from selling prices.'
                    : 'This branch is not VAT-registered. Tax is not shown or collected.',
                style: const TextStyle(color: muted),
              ),
              value: _vatRegistered,
              activeThumbColor: accent,
              onChanged: _vatLoading
                  ? null
                  : (value) async {
                      setState(() => _vatRegistered = value);
                      try {
                        await ref.read(apiProvider).updateBranchSettings(vatRegistered: value);
                        setState(() {
                          _message = value ? 'VAT is on for this branch.' : 'VAT is off for this branch.';
                          _tone = StatusTone.good;
                        });
                      } catch (_) {
                        setState(() {
                          _vatRegistered = !value;
                          _message = 'Could not save VAT setting.';
                          _tone = StatusTone.bad;
                        });
                      }
                    },
            ),
          ),
          const SizedBox(height: 16),
          const SectionLabel('Device'),
          const SizedBox(height: 8),
          PosCard(
            child: Column(
              children: [
                TextField(
                  controller: _url,
                  decoration: const InputDecoration(labelText: 'API URL'),
                  onSubmitted: (value) => ref.read(sessionProvider.notifier).updateBaseUrl(value.trim()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _device,
                  decoration: const InputDecoration(labelText: 'Device code'),
                  onSubmitted: (value) => ref.read(sessionProvider.notifier).updateDeviceCode(value.trim()),
                ),
                const SizedBox(height: 14),
                FilledButton(
                  onPressed: () async {
                    await ref.read(sessionProvider.notifier).updateBaseUrl(_url.text.trim());
                    await ref.read(sessionProvider.notifier).updateDeviceCode(_device.text.trim());
                    setState(() {
                      _message = 'Saved.';
                      _tone = StatusTone.good;
                    });
                  },
                  child: const Text('Save'),
                ),
              ],
            ),
          ),
          if (_message != null)
            SoftBanner(message: _message!, tone: _tone, margin: const EdgeInsets.only(top: 12)),
          const SizedBox(height: 20),
          OutlinedButton(
            onPressed: () => ref.read(sessionProvider.notifier).signOut(),
            style: OutlinedButton.styleFrom(foregroundColor: red, side: const BorderSide(color: redSoft)),
            child: const Text('Logout'),
          ),
          const SizedBox(height: 16),
          const Text(
            'Android emulator uses http://10.0.2.2:7101. A physical device should use your computer LAN IP.',
            style: TextStyle(color: muted, height: 1.45),
          ),
        ],
      ),
    );
  }
}
