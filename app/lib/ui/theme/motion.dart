import 'package:flutter/animation.dart';

/// Motion constants (spec §1, ⏸A-approved values). Later stages import these
/// so every animated affordance shares one timing vocabulary rather than
/// scattering magic durations.
abstract final class AppMotion {
  /// Standard screen/element transitions: 200–300 ms `easeOutCubic`. 250 ms
  /// sits in the middle of the pinned band.
  static const Duration standard = Duration(milliseconds: 250);

  /// The curve for [standard] transitions.
  static const Curve standardCurve = Curves.easeOutCubic;

  /// XP count-up animation on the celebration sheet / progress header.
  static const Duration xpCountUp = Duration(milliseconds: 800);

  /// Confetti burst — ONLY on achievement unlock / level-up (never routine
  /// actions). Capped at ≤1.2 s.
  static const Duration confettiBurst = Duration(milliseconds: 1200);

  /// Stagger between successively revealed items (e.g. unlock cards).
  static const Duration stagger = Duration(milliseconds: 250);

  /// One cycle of the Home streak-flame idle pulse — runs only while today's
  /// streak is alive.
  static const Duration flamePulse = Duration(milliseconds: 1600);
}
