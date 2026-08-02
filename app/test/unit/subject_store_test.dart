// Lane 1 step 2 (app leg): SubjectStore owns the selected subject with
// defaultSubject as the fallback; the offer list is a client-side constant
// (no server endpoint — that would be a contract addition).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:study_tutor_app/ui/subject_store.dart';

void main() {
  test('the offered list is the client-side constant — English only today',
      () {
    expect(availableSubjects, ['english']);
  });

  test('selection initialises to the fallback (defaultSubject)', () {
    final store = SubjectStore(fallback: defaultSubject);
    expect(store.selectedSubject, defaultSubject);
    expect(store.subjects, ['english']);
  });

  test('select updates the selection and notifies', () {
    final store = SubjectStore(
        fallback: defaultSubject, subjects: const ['english', 'french']);
    var notified = 0;
    store.addListener(() => notified++);

    store.select('french');

    expect(store.selectedSubject, 'french');
    expect(notified, 1);
  });

  test('reselecting the current subject does not notify', () {
    final store = SubjectStore(fallback: defaultSubject);
    var notified = 0;
    store.addListener(() => notified++);

    store.select(defaultSubject);

    expect(store.selectedSubject, defaultSubject);
    expect(notified, 0);
  });

  test('a subject outside the offer is rejected', () {
    final store = SubjectStore(fallback: defaultSubject);
    expect(() => store.select('maths'), throwsAssertionError);
    expect(store.selectedSubject, defaultSubject);
  });

  test('a fallback outside the offer is rejected at construction', () {
    expect(() => SubjectStore(fallback: 'maths'), throwsAssertionError);
  });

  test('the offer list is unmodifiable — extend availableSubjects instead',
      () {
    final store = SubjectStore(fallback: defaultSubject);
    expect(() => store.subjects.add('latin'), throwsUnsupportedError);
  });
}
