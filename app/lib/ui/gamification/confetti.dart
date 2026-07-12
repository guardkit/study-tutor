import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/motion.dart';

/// A one-shot confetti burst (spec §1 motion): a ≤1.2 s particle burst used
/// ONLY on achievement unlock / level-up — never routine actions. Self-drawn
/// with a [CustomPainter] (no package). The burst plays once and stops; it
/// never repeats, so it settles under `pumpAndSettle`.
class ConfettiBurst extends StatefulWidget {
  const ConfettiBurst({super.key, this.particleCount = 24, this.child});

  final int particleCount;
  final Widget? child;

  @override
  State<ConfettiBurst> createState() => _ConfettiBurstState();
}

class _ConfettiParticle {
  _ConfettiParticle(math.Random rng, int paletteSize)
      : angle = rng.nextDouble() * 2 * math.pi,
        speed = 0.5 + rng.nextDouble() * 0.5,
        colorIndex = rng.nextInt(paletteSize),
        size = 4 + rng.nextDouble() * 4,
        spin = (rng.nextDouble() - 0.5) * 6;

  final double angle;
  final double speed;

  /// Index into the theme palette, resolved at paint time — the concrete
  /// colours aren't known at construction (no theme yet) and never hardcoded.
  final int colorIndex;
  final double size;
  final double spin;
}

class _ConfettiBurstState extends State<ConfettiBurst>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: AppMotion.confettiBurst,
  );
  late final List<_ConfettiParticle> _particles;

  /// The theme palette has three roles (tertiary/primary/secondary), assembled
  /// in [build]; particles pick an index against this count at construction.
  static const int _paletteSize = 3;

  @override
  void initState() {
    super.initState();
    final rng = math.Random(7); // deterministic layout for stable tests
    _particles = List.generate(
      widget.particleCount,
      (_) => _ConfettiParticle(rng, _paletteSize),
    );
    _controller.forward();
  }

  // Filled in with the theme palette on first build (always assigned in
  // [build] before [_ConfettiPainter] can read it, so no seed colour is needed
  // — keeps lib/ui free of hardcoded `Colors.*`).
  late List<Color> _palette;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    _palette = [scheme.tertiary, scheme.primary, scheme.secondary];
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return CustomPaint(
          painter: _ConfettiPainter(_particles, _controller.value, _palette),
          child: child,
        );
      },
      child: widget.child,
    );
  }
}

class _ConfettiPainter extends CustomPainter {
  _ConfettiPainter(this.particles, this.t, this.palette);

  final List<_ConfettiParticle> particles;
  final double t;
  final List<Color> palette;

  @override
  void paint(Canvas canvas, Size size) {
    if (t == 0) return;
    final origin = Offset(size.width / 2, size.height * 0.35);
    final reach = size.shortestSide * 0.9;
    final opacity = (1 - t).clamp(0.0, 1.0);
    for (final p in particles) {
      final distance = p.speed * reach * t;
      final gravity = 40 * t * t;
      final dx = math.cos(p.angle) * distance;
      final dy = math.sin(p.angle) * distance + gravity;
      final center = origin + Offset(dx, dy);
      final color = palette[p.colorIndex % palette.length];
      final paint = Paint()
        ..color = color.withValues(alpha: opacity)
        ..style = PaintingStyle.fill;
      canvas.save();
      canvas.translate(center.dx, center.dy);
      canvas.rotate(p.spin * t);
      canvas.drawRect(
        Rect.fromCenter(center: Offset.zero, width: p.size, height: p.size),
        paint,
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ConfettiPainter old) =>
      old.t != t || old.palette != palette;
}
