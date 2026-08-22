import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/auth/session.dart';
import '../../core/network/api_client.dart';
import '../../ui/widgets.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _user = TextEditingController();
  final _pass = TextEditingController();
  String? _error;
  bool _busy = false;
  bool _hidePass = true;

  @override
  void dispose() {
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _openSettings() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
        child: _LoginApiSettings(onSaved: () {
          if (mounted) setState(() {});
        }),
      ),
    );
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = ref.read(apiProvider);
      final login = await api.login(_user.text.trim(), _pass.text);
      var deviceId = ref.read(sessionProvider).deviceId;
      await ref.read(sessionProvider.notifier).signedIn(
            accessToken: login['access_token'] as String,
            refreshToken: login['refresh_token'] as String,
            username: _user.text.trim(),
            deviceId: deviceId,
          );
      try {
        final device = await api.registerDevice();
        deviceId = device['id'] as int;
        await ref.read(sessionProvider.notifier).signedIn(
              accessToken: login['access_token'] as String,
              refreshToken: login['refresh_token'] as String,
              username: _user.text.trim(),
              deviceId: deviceId,
            );
      } catch (_) {
        // Device may already exist on another branch; POS still works without it.
      }
      final shift = await api.currentShift();
      await ref.read(sessionProvider.notifier).setShift(shift?['id'] as int?);
      if (mounted) context.go(shift == null ? '/shift' : '/home');
    } catch (error) {
      setState(() => _error = 'Could not sign in. Check user, password, and API URL.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final apiUrl = ref.watch(sessionProvider).baseUrl;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        body: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [navy, navy2, Color(0xFF0F3D24)],
            ),
          ),
          child: SafeArea(
            child: Stack(
              children: [
                Align(
                  alignment: Alignment.topRight,
                  child: IconButton(
                    tooltip: 'API settings',
                    onPressed: _openSettings,
                    icon: const Icon(Icons.settings_outlined, color: Colors.white),
                  ),
                ),
                Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(24),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 420),
                      child: Column(
                        children: [
                          const BrandMark(size: 56),
                          const SizedBox(height: 16),
                          const Text(
                            'PICKLEBALL POS',
                            style: TextStyle(
                              color: Colors.white,
                              letterSpacing: 2.4,
                              fontWeight: FontWeight.w800,
                              fontSize: 18,
                            ),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Canteen + court register',
                            style: TextStyle(color: Color(0xFFB7D4BE), fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 28),
                          PosCard(
                            padding: const EdgeInsets.fromLTRB(22, 22, 22, 20),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                const Text('Sign in', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: ink)),
                                const SizedBox(height: 4),
                                const Text('Use your staff account.', style: TextStyle(color: muted)),
                                const SizedBox(height: 20),
                                TextField(
                                  controller: _user,
                                  textInputAction: TextInputAction.next,
                                  autofillHints: const [AutofillHints.username],
                                  decoration: const InputDecoration(
                                    labelText: 'Username',
                                    prefixIcon: Icon(Icons.person_outline),
                                  ),
                                ),
                                const SizedBox(height: 12),
                                TextField(
                                  controller: _pass,
                                  obscureText: _hidePass,
                                  textInputAction: TextInputAction.done,
                                  onSubmitted: (_) => _busy ? null : _submit(),
                                  autofillHints: const [AutofillHints.password],
                                  decoration: InputDecoration(
                                    labelText: 'Password',
                                    prefixIcon: const Icon(Icons.lock_outline),
                                    suffixIcon: IconButton(
                                      onPressed: () => setState(() => _hidePass = !_hidePass),
                                      icon: Icon(_hidePass ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                                    ),
                                  ),
                                ),
                                if (_error != null) ...[
                                  const SizedBox(height: 12),
                                  Text(_error!, style: const TextStyle(color: red, fontWeight: FontWeight.w600, height: 1.35)),
                                ],
                                const SizedBox(height: 20),
                                FilledButton(
                                  onPressed: _busy ? null : _submit,
                                  child: Text(_busy ? 'Signing in…' : 'Sign in'),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 16),
                          TextButton.icon(
                            onPressed: _openSettings,
                            icon: const Icon(Icons.link, color: Color(0xFFB7D4BE), size: 18),
                            label: Text(
                              apiUrl,
                              style: const TextStyle(color: Color(0xFFB7D4BE), fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _LoginApiSettings extends ConsumerStatefulWidget {
  const _LoginApiSettings({required this.onSaved});

  final VoidCallback onSaved;

  @override
  ConsumerState<_LoginApiSettings> createState() => _LoginApiSettingsState();
}

class _LoginApiSettingsState extends ConsumerState<_LoginApiSettings> {
  late final TextEditingController _url;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    _url = TextEditingController(text: ref.read(sessionProvider).baseUrl);
  }

  @override
  void dispose() {
    _url.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final url = _url.text.trim();
    if (url.isEmpty) return;
    await ref.read(sessionProvider.notifier).updateBaseUrl(url);
    setState(() => _saved = true);
    widget.onSaved();
  }

  void _usePreset(String url) {
    _url.text = url;
    setState(() => _saved = false);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(color: line, borderRadius: BorderRadius.circular(99)),
            ),
          ),
          const SizedBox(height: 16),
          const Text('API settings', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 20, color: ink)),
          const SizedBox(height: 4),
          const Text(
            'Point this tablet at the FastAPI server. Use your computer LAN IP on a physical device.',
            style: TextStyle(color: muted, height: 1.35),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _url,
            keyboardType: TextInputType.url,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _save(),
            decoration: const InputDecoration(
              labelText: 'API URL',
              prefixIcon: Icon(Icons.link),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ActionChip(
                label: const Text('Android emulator'),
                onPressed: () => _usePreset('http://10.0.2.2:7101'),
              ),
              ActionChip(
                label: const Text('iOS simulator'),
                onPressed: () => _usePreset('http://127.0.0.1:7101'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'On a tablet use http://<this-computer-ip>:7101, for example http://10.250.106.91:7101',
            style: TextStyle(color: muted, fontSize: 12, height: 1.35),
          ),
          if (_saved) ...[
            const SizedBox(height: 12),
            const SoftBanner(
              message: 'API URL saved.',
              tone: StatusTone.good,
              margin: EdgeInsets.zero,
            ),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _save,
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }
}
