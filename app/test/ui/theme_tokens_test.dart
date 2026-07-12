// S-A1 design system: token-resolution for both modes. Seed roles come from
// `fromSeed` (proves the seed is wired), the tertiary role is steered to the
// ⏸A-pinned gold, and the BandColors extension carries the eight pinned hex
// values — all FINAL per the 2026-07-12 attended review.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/ui/theme/app_theme.dart';
import 'package:study_tutor_app/ui/theme/band_colors.dart';

void main() {
  group('seed roles (fromSeed, both modes)', () {
    test('light non-tertiary roles are exactly fromSeed(seed)', () {
      final scheme = AppTheme.light().colorScheme;
      final seeded = ColorScheme.fromSeed(seedColor: AppTheme.seedColor);
      expect(scheme.brightness, Brightness.light);
      expect(scheme.primary, seeded.primary);
      expect(scheme.secondary, seeded.secondary);
      expect(scheme.surface, seeded.surface);
    });

    test('dark non-tertiary roles are exactly fromSeed(seed, dark)', () {
      final scheme = AppTheme.dark().colorScheme;
      final seeded = ColorScheme.fromSeed(
          seedColor: AppTheme.seedColor, brightness: Brightness.dark);
      expect(scheme.brightness, Brightness.dark);
      expect(scheme.primary, seeded.primary);
      expect(scheme.secondary, seeded.secondary);
      expect(scheme.surface, seeded.surface);
    });

    test('seed constant is the pinned deep-ink indigo', () {
      expect(AppTheme.seedColor, const Color(0xFF324376));
    });
  });

  group('gold tertiary (⏸A-pinned, steered off fromSeed)', () {
    test('light tertiary roles', () {
      final s = AppTheme.light().colorScheme;
      expect(s.tertiary, const Color(0xFF7D5800));
      expect(s.onTertiary, const Color(0xFFFFFFFF));
      expect(s.tertiaryContainer, const Color(0xFFFFDEA9));
      expect(s.onTertiaryContainer, const Color(0xFF271900));
    });

    test('dark tertiary roles', () {
      final s = AppTheme.dark().colorScheme;
      expect(s.tertiary, const Color(0xFFF3BE5D));
      expect(s.onTertiary, const Color(0xFF422C00));
      expect(s.tertiaryContainer, const Color(0xFF5F4100));
      expect(s.onTertiaryContainer, const Color(0xFFFFDEA9));
    });

    test('the steer actually changed the seeded tertiary', () {
      final seededLight =
          ColorScheme.fromSeed(seedColor: AppTheme.seedColor).tertiary;
      expect(AppTheme.light().colorScheme.tertiary, isNot(seededLight));
    });
  });

  group('BandColors extension (all eight pinned values)', () {
    test('light band values', () {
      final b = AppTheme.light().extension<BandColors>()!;
      expect(b.struggling, const Color(0xFFC4453C));
      expect(b.developing, const Color(0xFFB98A2E));
      expect(b.secure, const Color(0xFF3E6FA3));
      expect(b.mastered, const Color(0xFF3F8F5F));
    });

    test('dark band values', () {
      final b = AppTheme.dark().extension<BandColors>()!;
      expect(b.struggling, const Color(0xFFE58A82));
      expect(b.developing, const Color(0xFFE3B95C));
      expect(b.secure, const Color(0xFF8FB8E0));
      expect(b.mastered, const Color(0xFF7FC79B));
    });
  });

  group('typography', () {
    test('display styles use the bundled display face', () {
      final t = AppTheme.light().textTheme;
      expect(t.displayLarge?.fontFamily, 'BricolageGrotesque');
      expect(t.displayLarge?.fontSize, 28);
      expect(t.displayMedium?.fontSize, 24);
    });

    test('celebration XP numeral is the pinned 36-size display style', () {
      expect(AppTheme.celebrationXpNumeral.fontSize, 36);
      expect(AppTheme.celebrationXpNumeral.fontFamily, 'BricolageGrotesque');
      expect(AppTheme.celebrationXpNumeral.fontWeight, FontWeight.w700);
    });
  });
}
