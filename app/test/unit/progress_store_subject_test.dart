// Lane 1 step 2 (app leg): the progress read follows the selected subject.
// ProgressStore.updateSubject re-points the store and refetches, dropping the
// old subject's snapshot first (§6.1's never-hidden card degrades to its
// loading/zero state rather than showing one subject's mastery under
// another's selection).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/gamification.dart';
import 'package:study_tutor_app/fakes/fake_student_model_api.dart';
import 'package:study_tutor_app/ports/student_model_api.dart';
import 'package:study_tutor_app/ui/progress_store.dart';

/// Records every subject fetched. English answers with the seeded record,
/// anything else with the zero-state — the live backend's honest empty answer
/// for a subject with nothing banked (binding §2.2, live-proven 2026-08-02).
class _RecordingStudentModelApi implements StudentModelApi {
  final fetched = <String>[];

  @override
  Future<StudentModel> fetch({required String subject}) async {
    fetched.add(subject);
    return subject == 'english'
        ? FakeStudentModelApi.defaultModel
        : FakeStudentModelApi.zeroState;
  }
}

void main() {
  test('load fetches under the constructed subject', () async {
    final api = _RecordingStudentModelApi();
    final store = ProgressStore(api: api, subject: 'english');

    await store.load();

    expect(store.subject, 'english');
    expect(api.fetched, ['english']);
    expect(store.model, FakeStudentModelApi.defaultModel);
  });

  test('updateSubject drops the stale snapshot and refetches', () async {
    final api = _RecordingStudentModelApi();
    final store = ProgressStore(api: api, subject: 'english');
    await store.load();

    store.updateSubject('french');
    expect(store.model, isNull,
        reason: "the cached record is the old subject's — never shown under "
            'the new selection');

    await pumpEventQueue();
    expect(store.subject, 'french');
    expect(api.fetched, ['english', 'french']);
    expect(store.model, FakeStudentModelApi.zeroState,
        reason: 'a subject with nothing banked honestly shows the zero-state');
  });

  test('updateSubject with the current subject is a no-op', () async {
    final api = _RecordingStudentModelApi();
    final store = ProgressStore(api: api, subject: 'english');
    await store.load();

    store.updateSubject('english');
    await pumpEventQueue();

    expect(api.fetched, ['english'], reason: 'no redundant refetch');
    expect(store.model, FakeStudentModelApi.defaultModel);
  });
}
