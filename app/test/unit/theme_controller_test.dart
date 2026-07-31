// ThemeController — app-wide theme-mode state (Settings surface, scope §7).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/ui/theme_controller.dart';

void main() {
  test('defaults to ThemeMode.system', () {
    expect(ThemeController().mode, ThemeMode.system);
    expect(ThemeController.defaultMode, ThemeMode.system);
  });

  test('honours an injected initial mode', () {
    expect(ThemeController(initialMode: ThemeMode.dark).mode, ThemeMode.dark);
  });

  test('setMode changes the mode and notifies listeners', () {
    final controller = ThemeController();
    var notifications = 0;
    controller.addListener(() => notifications++);

    controller.setMode(ThemeMode.dark);
    expect(controller.mode, ThemeMode.dark);
    expect(notifications, 1);

    controller.setMode(ThemeMode.light);
    expect(controller.mode, ThemeMode.light);
    expect(notifications, 2);
  });

  test('setMode to the current mode is a no-op (no notification)', () {
    final controller = ThemeController(initialMode: ThemeMode.light);
    var notifications = 0;
    controller.addListener(() => notifications++);

    controller.setMode(ThemeMode.light);
    expect(controller.mode, ThemeMode.light);
    expect(notifications, 0);
  });
}
