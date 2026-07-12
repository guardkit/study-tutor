import 'package:flutter/foundation.dart';

import '../domain/errors.dart';
import '../domain/gamification.dart';
import '../ports/student_model_api.dart';

/// Owns the student-model snapshot for the whole app (spec §2): fetch, cache,
/// and refresh-after-session-end. A [ChangeNotifier] — no provider/riverpod/
/// bloc; the Home header card and Progress screen rebuild off it via
/// `ListenableBuilder`.
///
/// The snapshot is cached: a failed refresh keeps the last good [model] rather
/// than blanking the card (spec §6.1: the card is never hidden). "Streak alive
/// today" is app-local UX state — there is no wire field for it, so the store
/// only knows the streak is alive once a session-end block reports
/// `streak_extended` during this app run.
class ProgressStore extends ChangeNotifier {
  ProgressStore({required this._api, required this.subject});

  final StudentModelApi _api;

  /// The subject the record is scoped to (`GET /api/student-model?subject=`).
  final String subject;

  StudentModel? _model;
  bool _loading = false;
  bool _hasLoaded = false;
  bool _streakAliveToday = false;

  /// The cached record, or null before the first successful load.
  StudentModel? get model => _model;

  /// True while a fetch is in flight and no cached record exists yet.
  bool get isLoading => _loading && _model == null;

  /// Whether the first load has been kicked off (so Home only auto-loads once).
  bool get hasLoaded => _hasLoaded;

  /// App-local: has a session extended the streak during this app run? Drives
  /// the Home flame's idle pulse (spec §1) and the badge's alive/at-risk state
  /// (spec §6.1). False on a cold load — we can't know from the wire alone.
  bool get streakAliveToday => _streakAliveToday;

  /// Initial fetch — call once (Home `initState`). Safe to call again; it just
  /// re-fetches.
  Future<void> load() {
    _hasLoaded = true;
    return _fetch();
  }

  /// Re-fetch after a session ends (spec §6.2 dismiss path). When the ended
  /// session's block reported `streak_extended`, the streak is alive today.
  Future<void> refresh({bool streakExtended = false}) {
    if (streakExtended) _streakAliveToday = true;
    return _fetch();
  }

  Future<void> _fetch() async {
    _loading = true;
    if (_model == null) notifyListeners();
    try {
      final model = await _api.fetch(subject: subject);
      _model = model;
    } on Unauthenticated {
      // Leave the cache as-is; the surrounding screen owns the sign-in route.
    } on TransportError {
      // Keep the last good snapshot; the card degrades to it or the zero-state.
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}
