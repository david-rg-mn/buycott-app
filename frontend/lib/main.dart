import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'src/services/buycott_api.dart';
import 'src/state/search_state.dart';
import 'src/theme/app_theme.dart';
import 'src/widgets/map_search_screen.dart';

void main() {
  const baseUrl = String.fromEnvironment(
    'BUYCOTT_API_URL',
    defaultValue: 'http://localhost:8000',
  );
  final api = BuycottApi(baseUrl: baseUrl);

  runApp(BuycottApp(api: api));
}

class BuycottApp extends StatelessWidget {
  const BuycottApp({super.key, required this.api});

  final BuycottApi api;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => SearchState(api: api),
      child: MaterialApp(
        title: 'Buycott',
        theme: AppTheme.build(),
        home: MapSearchScreen(api: api),
      ),
    );
  }
}
