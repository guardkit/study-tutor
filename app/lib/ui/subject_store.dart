import 'package:flutter/foundation.dart';

/// The subjects the app offers — a CLIENT-SIDE constant by design (Lane 1
/// step 2): no server endpoint lists subjects, and inventing one would be a
/// contract addition (a later, additive decision once per-subject content
/// packs exist). Adding an entry here surfaces it in the Home picker with no
/// further plumbing — the backend already keys sessions, retrieval, mastery
/// banking, and progress reads on whatever subject the app sends.
const availableSubjects = ['english'];

/// Owns the selected tutoring subject for the app run (Lane 1 step 2's app
/// seam). A [ChangeNotifier] like `ProgressStore`/`ThemeController` — no
/// provider/riverpod/bloc. Session-scoped by design (Rich's call 2026-08-02):
/// every launch starts on the fallback (`defaultSubject`); nothing persists.
class SubjectStore extends ChangeNotifier {
  SubjectStore({required String fallback, List<String>? subjects})
      : assert((subjects ?? availableSubjects).contains(fallback),
            'the fallback must be one of the offered subjects'),
        subjects = List.unmodifiable(subjects ?? availableSubjects),
        _selected = fallback;

  /// The offered subjects, in display order. Injectable so tests can drive
  /// the picker with more than one entry before a second subject really lands.
  final List<String> subjects;

  String _selected;

  /// The subject every `startSession` and progress read consumes.
  String get selectedSubject => _selected;

  /// Select [subject] from the offer. Reselecting the current subject is a
  /// no-op; values outside [subjects] are rejected — the list is the closed
  /// client-side offer, not a free-text field.
  void select(String subject) {
    assert(subjects.contains(subject), 'unknown subject: $subject');
    if (!subjects.contains(subject) || subject == _selected) return;
    _selected = subject;
    notifyListeners();
  }
}
