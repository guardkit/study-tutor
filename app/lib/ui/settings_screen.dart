import 'package:flutter/material.dart';

import '../ports/identity_provider.dart';
import '../ports/session_api.dart';
import '../ports/voice_api.dart';
import 'error_handling.dart';
import 'theme_controller.dart';

/// Settings / Profile surface (scope §7). Two sections:
///
/// - **Appearance** — a System / Light / Dark selector wired to the app-wide
///   [ThemeController]; the choice is in-memory only for v1 (no storage
///   dependency), so it follows the platform again on a cold start.
/// - **Profile** — the signed-in principal's display name and a clear Sign out
///   action that reuses the shared sign-out flow ([routeToSignIn] after
///   `identity.signOut()`), the same treatment the Home overflow used.
///
/// Ports are injected via the constructor (screens never import fakes); Home
/// resolves them from the ambient [AppScope] when it pushes this screen.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({
    super.key,
    required this.identity,
    required this.sessionApi,
    required this.voiceApi,
    required this.themeController,
  });

  final IdentityProvider identity;
  final SessionApi sessionApi;
  final VoiceApi voiceApi;
  final ThemeController themeController;

  Future<void> _signOut(BuildContext context) async {
    await identity.signOut();
    if (!context.mounted) return;
    routeToSignIn(context, identity, sessionApi, voiceApi);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final displayName = identity.currentPrincipal?.displayName;

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionHeader(theme, 'Appearance'),
          const SizedBox(height: 8),
          _AppearanceSelector(controller: themeController),
          const SizedBox(height: 32),
          _sectionHeader(theme, 'Profile'),
          const SizedBox(height: 8),
          _ProfileRow(displayName: displayName),
          const SizedBox(height: 16),
          Semantics(
            button: true,
            label: 'Sign out',
            child: OutlinedButton.icon(
              onPressed: () => _signOut(context),
              icon: const Icon(Icons.logout),
              label: const Text('Sign out'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionHeader(ThemeData theme, String label) {
    return Semantics(
      header: true,
      child: Text(
        label,
        style: theme.textTheme.titleMedium
            ?.copyWith(color: theme.colorScheme.primary),
      ),
    );
  }
}

/// The System / Light / Dark selector, rebuilding off the [ThemeController] so
/// the active choice always reflects the app-wide mode.
class _AppearanceSelector extends StatelessWidget {
  const _AppearanceSelector({required this.controller});

  final ThemeController controller;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        return Semantics(
          label: 'Theme mode',
          child: SegmentedButton<ThemeMode>(
            segments: const [
              ButtonSegment<ThemeMode>(
                value: ThemeMode.system,
                icon: Icon(Icons.brightness_auto),
                label: Text('System'),
              ),
              ButtonSegment<ThemeMode>(
                value: ThemeMode.light,
                icon: Icon(Icons.light_mode),
                label: Text('Light'),
              ),
              ButtonSegment<ThemeMode>(
                value: ThemeMode.dark,
                icon: Icon(Icons.dark_mode),
                label: Text('Dark'),
              ),
            ],
            selected: {controller.mode},
            onSelectionChanged: (selection) =>
                controller.setMode(selection.first),
          ),
        );
      },
    );
  }
}

/// The signed-in principal's display name (or a signed-out fallback).
class _ProfileRow extends StatelessWidget {
  const _ProfileRow({required this.displayName});

  final String? displayName;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final name = displayName ?? 'Not signed in';
    return Semantics(
      label: 'Signed in as $name',
      child: ExcludeSemantics(
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: theme.colorScheme.primaryContainer,
              child: Icon(
                Icons.person,
                color: theme.colorScheme.onPrimaryContainer,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Signed in as',
                      style: theme.textTheme.labelLarge
                          ?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                  Text(name, style: theme.textTheme.titleMedium),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
