import 'package:flutter_test/flutter_test.dart';

import 'package:buycott_frontend/main.dart';
import 'package:buycott_frontend/src/services/buycott_api.dart';

void main() {
  testWidgets('Buycott app renders search input', (WidgetTester tester) async {
    await tester.pumpWidget(
      BuycottApp(api: BuycottApi(baseUrl: 'http://localhost:8000')),
    );

    expect(find.text('Where can I get this nearby?'), findsOneWidget);
    expect(find.text('Local only'), findsOneWidget);
  });
}
