/// The signed-in identity as the UI sees it.
///
/// Contract §3: a principal carries a token; `student_id` is derived from the
/// token by the backend port, never asserted by UI code — so this model
/// deliberately has no `studentId` field.
library;

class Principal {
  const Principal({required this.token, required this.displayName});

  final String token;
  final String displayName;

  @override
  bool operator ==(Object other) =>
      other is Principal && other.token == token && other.displayName == displayName;

  @override
  int get hashCode => Object.hash(token, displayName);

  @override
  String toString() => 'Principal($displayName)';
}
