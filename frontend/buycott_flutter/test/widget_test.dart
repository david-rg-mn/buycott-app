import 'package:flutter_test/flutter_test.dart';

import 'package:buycott_flutter/main.dart';

void main() {
  testWidgets('buycott search input renders', (WidgetTester tester) async {
    await tester.pumpWidget(const BuycottApp());
    expect(find.text('Where can I get this nearby?'), findsOneWidget);
  });
}
