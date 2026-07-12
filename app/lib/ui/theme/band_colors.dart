import 'package:flutter/material.dart';

/// Semantic mastery-band colours (design.md §6.1; spec §1) exposed as a
/// [ThemeExtension] so band-coloured UI (mastery grid, progress cells) reads
/// its palette from the theme rather than hardcoding it. Light/dark pairs are
/// the ⏸A-pinned values (2026-07-12, FINAL).
///
/// Read via `Theme.of(context).extension<BandColors>()!` or the [of] helper.
@immutable
class BandColors extends ThemeExtension<BandColors> {
  const BandColors({
    required this.struggling,
    required this.developing,
    required this.secure,
    required this.mastered,
  });

  final Color struggling;
  final Color developing;
  final Color secure;
  final Color mastered;

  /// Light-mode band palette (⏸A pinned).
  static const light = BandColors(
    struggling: Color(0xFFC4453C),
    developing: Color(0xFFB98A2E),
    secure: Color(0xFF3E6FA3),
    mastered: Color(0xFF3F8F5F),
  );

  /// Dark-mode band palette (⏸A pinned).
  static const dark = BandColors(
    struggling: Color(0xFFE58A82),
    developing: Color(0xFFE3B95C),
    secure: Color(0xFF8FB8E0),
    mastered: Color(0xFF7FC79B),
  );

  /// The [BandColors] registered on the ambient theme.
  static BandColors of(BuildContext context) =>
      Theme.of(context).extension<BandColors>()!;

  @override
  BandColors copyWith({
    Color? struggling,
    Color? developing,
    Color? secure,
    Color? mastered,
  }) =>
      BandColors(
        struggling: struggling ?? this.struggling,
        developing: developing ?? this.developing,
        secure: secure ?? this.secure,
        mastered: mastered ?? this.mastered,
      );

  @override
  BandColors lerp(ThemeExtension<BandColors>? other, double t) {
    if (other is! BandColors) return this;
    return BandColors(
      struggling: Color.lerp(struggling, other.struggling, t)!,
      developing: Color.lerp(developing, other.developing, t)!,
      secure: Color.lerp(secure, other.secure, t)!,
      mastered: Color.lerp(mastered, other.mastered, t)!,
    );
  }
}
