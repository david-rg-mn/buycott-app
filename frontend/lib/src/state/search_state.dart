import 'package:flutter/foundation.dart';

import '../models/search_models.dart';
import '../services/buycott_api.dart';

class SearchState extends ChangeNotifier {
  SearchState({required BuycottApi api}) : _api = api;

  final BuycottApi _api;

  String query = '';
  bool includeChains = false;
  bool openNow = false;
  bool walkingDistance = false;
  int walkingThresholdMinutes = 15;
  bool loading = false;

  double userLat = 44.9778;
  double userLng = -93.2650;

  List<String> suggestions = [];
  List<String> relatedItems = [];
  List<String> expandedTerms = [];
  List<SearchResultModel> results = [];

  Future<void> setQuery(String value) async {
    query = value;
    notifyListeners();

    if (value.trim().length < 2) {
      suggestions = [];
      notifyListeners();
      return;
    }

    suggestions = await _api.suggestions(value.trim());
    notifyListeners();
  }

  Future<void> search() async {
    if (query.trim().length < 2) {
      return;
    }

    loading = true;
    notifyListeners();

    try {
      final response = await _api.search(
        query: query,
        lat: userLat,
        lng: userLng,
        includeChains: includeChains,
        openNow: openNow,
        walkingDistance: walkingDistance,
        walkingThresholdMinutes: walkingThresholdMinutes,
      );

      results = response.results;
      expandedTerms = response.expandedTerms;
      relatedItems = await _api.relatedItems(query);
      suggestions = [];
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> toggleIncludeChains(bool value) async {
    includeChains = value;
    notifyListeners();
    if (query.isNotEmpty) {
      await search();
    }
  }

  Future<void> toggleOpenNow(bool value) async {
    openNow = value;
    notifyListeners();
    if (query.isNotEmpty) {
      await search();
    }
  }

  Future<void> toggleWalkingDistance(bool value) async {
    walkingDistance = value;
    notifyListeners();
    if (query.isNotEmpty) {
      await search();
    }
  }

  Future<void> applySuggestion(String value) async {
    query = value;
    suggestions = [];
    notifyListeners();
    await search();
  }
}
