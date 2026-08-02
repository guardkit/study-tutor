/// The app version, kept in sync with `pubspec.yaml` via a test.
///
/// This is the single source of truth for the version string displayed in the
/// UI. The test in `app/test/config/app_version_test.dart` reads
/// `pubspec.yaml` and asserts this constant matches — preventing silent drift.
const String appVersion = '1.0.0+1';
