import 'package:flutter/material.dart';

import 'band_colors.dart';

/// "Warm academic" (R2) design system — spec §1, all values ⏸A-pinned
/// (2026-07-12, FINAL). Both light and dark schemes are built from a single
/// indigo seed with the tertiary role steered to warm gold; the display face
/// (Bricolage Grotesque) is applied to headings only, body/UI stay platform
/// default (Roboto/SF).
abstract final class AppTheme {
  /// Deep-ink-indigo seed for `ColorScheme.fromSeed` (both brightnesses).
  static const Color seedColor = Color(0xFF324376);

  /// The bundled display face (declared in pubspec, weights 400/500/600/700).
  static const String displayFontFamily = 'BricolageGrotesque';

  /// Named style for the celebration XP numeral (spec §1: size 36 — the one
  /// approved exception above display-28). Used by the session-end sheet in
  /// S-A3; colour is resolved by the caller from the scheme.
  static const TextStyle celebrationXpNumeral = TextStyle(
    fontFamily: displayFontFamily,
    fontSize: 36,
    fontWeight: FontWeight.w700,
    height: 1.05,
  );

  static ThemeData light() => _theme(Brightness.light);

  static ThemeData dark() => _theme(Brightness.dark);

  static ThemeData _theme(Brightness brightness) {
    final scheme = _scheme(brightness);
    final bands =
        brightness == Brightness.light ? BandColors.light : BandColors.dark;
    final base = ThemeData(colorScheme: scheme, useMaterial3: true);
    return base.copyWith(
      textTheme: _textTheme(base.textTheme),
      extensions: <ThemeExtension<dynamic>>[bands],
    );
  }

  /// `fromSeed` for the given brightness with the tertiary role steered to the
  /// warm-gold `#B98A2E` tonal palette (⏸A-pinned tones). Every other role is
  /// left exactly as `fromSeed` renders it (⏸A: approved as rendered).
  static ColorScheme _scheme(Brightness brightness) {
    final seeded =
        ColorScheme.fromSeed(seedColor: seedColor, brightness: brightness);
    if (brightness == Brightness.light) {
      return seeded.copyWith(
        tertiary: const Color(0xFF7D5800),
        onTertiary: const Color(0xFFFFFFFF),
        tertiaryContainer: const Color(0xFFFFDEA9),
        onTertiaryContainer: const Color(0xFF271900),
      );
    }
    return seeded.copyWith(
      tertiary: const Color(0xFFF3BE5D),
      onTertiary: const Color(0xFF422C00),
      tertiaryContainer: const Color(0xFF5F4100),
      onTertiaryContainer: const Color(0xFFFFDEA9),
    );
  }

  /// Type scale (spec §1): display 28/24 in the display face (w600), title 18,
  /// body 15, label 12. Headline styles also take the display face so screen
  /// titles (e.g. SignIn app name) render warm; body/label keep the platform
  /// family for legible UI text.
  static TextTheme _textTheme(TextTheme base) {
    TextStyle display(TextStyle? s, double size) => (s ?? const TextStyle())
        .copyWith(
      fontFamily: displayFontFamily,
      fontSize: size,
      fontWeight: FontWeight.w600,
      height: 1.15,
    );
    return base.copyWith(
      displayLarge: display(base.displayLarge, 28),
      displayMedium: display(base.displayMedium, 24),
      displaySmall: display(base.displaySmall, 24),
      headlineLarge: display(base.headlineLarge, 28),
      headlineMedium: display(base.headlineMedium, 24),
      headlineSmall: display(base.headlineSmall, 24),
      titleLarge: base.titleLarge?.copyWith(fontSize: 18),
      titleMedium: base.titleMedium?.copyWith(fontSize: 16),
      bodyLarge: base.bodyLarge?.copyWith(fontSize: 15),
      bodyMedium: base.bodyMedium?.copyWith(fontSize: 15),
      labelLarge: base.labelLarge?.copyWith(fontSize: 12),
      labelMedium: base.labelMedium?.copyWith(fontSize: 12),
      labelSmall: base.labelSmall?.copyWith(fontSize: 12),
    );
  }
}
