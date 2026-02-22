import 'package:buycott_flutter/design_system.dart';
import 'package:buycott_flutter/widgets/buycott_card.dart';
import 'package:buycott_flutter/widgets/evidence_square.dart';
import 'package:buycott_flutter/widgets/primary_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';

void main() {
  testWidgets('design system visual baseline', (WidgetTester tester) async {
    GoogleFonts.config.allowRuntimeFetching = false;
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(400, 800);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        theme: BuycottDesignSystem.darkTheme(),
        home: const Scaffold(
          backgroundColor: BuycottColors.bgPrimary,
          body: Padding(
            padding: EdgeInsets.all(Dimensions.x2),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                BuycottCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Buycott Card Title'),
                      SizedBox(height: Dimensions.x1),
                      Text('Dark-mode tokenized card content'),
                    ],
                  ),
                ),
                SizedBox(height: Dimensions.x2),
                PrimaryButton(label: 'Find Nearby', expand: true),
                SizedBox(height: Dimensions.x2),
                Align(
                  alignment: Alignment.centerLeft,
                  child:
                      EvidenceSquare(minutes: 8, evidence: 92, highlight: true),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    await expectLater(
      find.byType(Scaffold),
      matchesGoldenFile('goldens/design_system_baseline.png'),
    );
  });
}
