import 'package:flutter/material.dart';

import '../app/theme.dart';
import 'format.dart';

class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 44});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 0.28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF34C759), Color(0xFF1E8A3C)],
        ),
        boxShadow: const [
          BoxShadow(color: Color(0x401E8A3C), blurRadius: 18, offset: Offset(0, 8)),
        ],
      ),
      alignment: Alignment.center,
      child: Text(
        'P',
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w800,
          fontSize: size * 0.46,
          height: 1,
        ),
      ),
    );
  }
}

class ProductThumb extends StatelessWidget {
  const ProductThumb({
    super.key,
    required this.name,
    this.imageUrl,
    this.seed = 0,
    this.size = 56,
    this.radius = 12,
    this.expand = false,
  });

  final String name;
  final String? imageUrl;
  final int seed;
  final double size;
  final double radius;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final color = productAccent(seed);
    final url = imageUrl == null || imageUrl!.isEmpty ? null : imageUrl;
    final iconSize = expand ? 36.0 : size * 0.42;
    final child = url == null
        ? ColoredBox(
            color: color.withValues(alpha: 0.12),
            child: Center(child: Icon(_iconFor(name), color: color, size: iconSize)),
          )
        : Image.network(
            url,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => ColoredBox(
              color: color.withValues(alpha: 0.12),
              child: Center(child: Icon(_iconFor(name), color: color, size: iconSize)),
            ),
          );
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: expand ? child : SizedBox(width: size, height: size, child: child),
    );
  }

  IconData _iconFor(String name) {
    final lower = name.toLowerCase();
    if (lower.contains('drink') || lower.contains('water') || lower.contains('coffee')) {
      return Icons.local_drink_outlined;
    }
    if (lower.contains('chip') || lower.contains('bar') || lower.contains('snack')) {
      return Icons.fastfood_outlined;
    }
    if (lower.contains('ball') || lower.contains('paddle')) return Icons.sports_tennis;
    return Icons.inventory_2_outlined;
  }
}

class PosCard extends StatelessWidget {
  const PosCard({super.key, required this.child, this.padding, this.color});

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color ?? Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: line),
        boxShadow: const [
          BoxShadow(color: Color(0x0A102028), blurRadius: 18, offset: Offset(0, 8)),
        ],
      ),
      child: Padding(
        padding: padding ?? const EdgeInsets.all(16),
        child: child,
      ),
    );
  }
}

class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: const TextStyle(
        color: muted,
        fontSize: 11,
        fontWeight: FontWeight.w800,
        letterSpacing: 0.9,
      ),
    );
  }
}

class MoneyText extends StatelessWidget {
  const MoneyText(this.value, {super.key, this.size = 18, this.color = ink, this.weight = FontWeight.w800});

  final dynamic value;
  final double size;
  final Color color;
  final FontWeight weight;

  @override
  Widget build(BuildContext context) {
    return Text(
      peso(value),
      style: TextStyle(color: color, fontSize: size, fontWeight: weight, letterSpacing: -0.3),
    );
  }
}

class StatusPill extends StatelessWidget {
  const StatusPill({
    super.key,
    required this.label,
    this.tone = StatusTone.neutral,
  });

  final String label;
  final StatusTone tone;

  @override
  Widget build(BuildContext context) {
    final colors = switch (tone) {
      StatusTone.good => (greenSoft, green),
      StatusTone.warn => (orangeSoft, Color(0xFFB45309)),
      StatusTone.bad => (redSoft, red),
      StatusTone.info => (accentSoft, accent),
      StatusTone.neutral => (canvas, muted),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: colors.$1,
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        label,
        style: TextStyle(color: colors.$2, fontSize: 12, fontWeight: FontWeight.w800),
      ),
    );
  }
}

enum StatusTone { good, warn, bad, info, neutral }

class SoftBanner extends StatelessWidget {
  const SoftBanner({
    super.key,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.tone = StatusTone.warn,
    this.margin = const EdgeInsets.fromLTRB(16, 12, 16, 0),
  });

  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final StatusTone tone;
  final EdgeInsetsGeometry margin;

  @override
  Widget build(BuildContext context) {
    final colors = switch (tone) {
      StatusTone.good => (greenSoft, green),
      StatusTone.warn => (orangeSoft, const Color(0xFFB45309)),
      StatusTone.bad => (redSoft, red),
      StatusTone.info => (accentSoft, accent),
      StatusTone.neutral => (canvas, muted),
    };
    return Container(
      width: double.infinity,
      margin: margin,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: colors.$1,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(message, style: TextStyle(color: colors.$2, fontWeight: FontWeight.w700)),
          ),
          if (actionLabel != null)
            TextButton(onPressed: onAction, child: Text(actionLabel!)),
        ],
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.detail,
  });

  final IconData icon;
  final String title;
  final String? detail;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: const BoxDecoration(color: accentSoft, shape: BoxShape.circle),
              child: Icon(icon, color: accent, size: 30),
            ),
            const SizedBox(height: 16),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16, color: ink)),
            if (detail != null) ...[
              const SizedBox(height: 6),
              Text(detail!, textAlign: TextAlign.center, style: const TextStyle(color: muted, height: 1.4)),
            ],
          ],
        ),
      ),
    );
  }
}

class QtyStepper extends StatelessWidget {
  const QtyStepper({
    super.key,
    required this.qty,
    required this.onMinus,
    required this.onPlus,
  });

  final int qty;
  final VoidCallback onMinus;
  final VoidCallback onPlus;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: canvas,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _StepButton(icon: Icons.remove, onTap: onMinus),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Text('$qty', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          ),
          _StepButton(icon: Icons.add, onTap: onPlus),
        ],
      ),
    );
  }
}

class _StepButton extends StatelessWidget {
  const _StepButton({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: SizedBox(width: 36, height: 36, child: Icon(icon, size: 18, color: ink)),
    );
  }
}

class QuickAction extends StatelessWidget {
  const QuickAction({
    super.key,
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: line),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
            child: Column(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, color: color),
                ),
                const SizedBox(height: 10),
                Text(
                  label,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: ink, height: 1.2),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class MenuRow extends StatelessWidget {
  const MenuRow({
    super.key,
    required this.icon,
    required this.label,
    this.detail,
    this.color = ink,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final String? detail;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: onTap,
      leading: Icon(icon, color: color),
      title: Text(label, style: TextStyle(fontWeight: FontWeight.w700, color: color)),
      subtitle: detail == null ? null : Text(detail!, style: const TextStyle(color: muted)),
      trailing: onTap == null ? null : const Icon(Icons.chevron_right, color: muted),
    );
  }
}
