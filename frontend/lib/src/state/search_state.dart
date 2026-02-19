import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/search_models.dart';
import '../services/buycott_api.dart';

class SearchState extends ChangeNotifier {
  SearchState({required BuycottApi api}) : _api = api;

  static const _suggestionDebounce = Duration(milliseconds: 250);

  final BuycottApi _api;
  Timer? _debounce;
  int _suggestionRequestId = 0;
  int _searchRequestId = 0;
  String? _lastSearchSignature;
  String? _activeSearchSignature;

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
  List<SearchResultModel> markerResults = [];

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> setQuery(String value) async {
    query = value;
    final normalizedQuery = value.trim();
    final requestId = _resetSuggestionDebounce();

    if (normalizedQuery.length < 2) {
      if (suggestions.isEmpty) {
        return;
      }
      suggestions = const [];
      notifyListeners();
      return;
    }

    _debounce = Timer(_suggestionDebounce, () async {
      try {
        final nextSuggestions = await _api.suggestions(normalizedQuery);
        if (!_isActiveSuggestionRequest(requestId, normalizedQuery)) {
          return;
        }
        if (listEquals(nextSuggestions, suggestions)) {
          return;
        }
        suggestions = List<String>.unmodifiable(nextSuggestions);
        notifyListeners();
      } catch (_) {
        if (!_isActiveSuggestionRequest(requestId, normalizedQuery)) {
          return;
        }
        if (suggestions.isEmpty) {
          return;
        }
        suggestions = const [];
        notifyListeners();
      }
    });
  }

  Future<void> search({bool force = false}) async {
    final normalizedQuery = query.trim();
    if (normalizedQuery.length < 2) {
      if (suggestions.isNotEmpty) {
        suggestions = const [];
        notifyListeners();
      }
      return;
    }

    final signature = _buildSearchSignature(normalizedQuery);
    if (!force) {
      if (_lastSearchSignature == signature) {
        return;
      }
      if (loading && _activeSearchSignature == signature) {
        return;
      }
    }

    _resetSuggestionDebounce();
    final requestId = ++_searchRequestId;
    _activeSearchSignature = signature;
    loading = true;
    if (suggestions.isNotEmpty) {
      suggestions = const [];
    }
    notifyListeners();

    try {
      final payload = await Future.wait<Object>([
        _api.search(
          query: normalizedQuery,
          lat: userLat,
          lng: userLng,
          includeChains: includeChains,
          openNow: openNow,
          walkingDistance: walkingDistance,
          walkingThresholdMinutes: walkingThresholdMinutes,
        ),
        _api.relatedItems(normalizedQuery),
      ]);

      if (requestId != _searchRequestId) {
        return;
      }

      final response = payload[0] as SearchResponseModel;
      final related = payload[1] as List<String>;
      final nextResults =
          List<SearchResultModel>.unmodifiable(response.results);

      results = nextResults;
      markerResults = nextResults;
      expandedTerms = List<String>.unmodifiable(response.expandedTerms);
      relatedItems = List<String>.unmodifiable(related);
      _lastSearchSignature = signature;
    } finally {
      if (requestId == _searchRequestId) {
        loading = false;
        _activeSearchSignature = null;
        notifyListeners();
      }
    }
  }

  Future<void> toggleIncludeChains(bool value) async {
    if (includeChains == value) {
      return;
    }
    includeChains = value;
    if (query.trim().length >= 2) {
      await search();
      return;
    }
    notifyListeners();
  }

  Future<void> toggleOpenNow(bool value) async {
    if (openNow == value) {
      return;
    }
    openNow = value;
    if (query.trim().length >= 2) {
      await search();
      return;
    }
    notifyListeners();
  }

  Future<void> toggleWalkingDistance(bool value) async {
    if (walkingDistance == value) {
      return;
    }
    walkingDistance = value;
    if (query.trim().length >= 2) {
      await search();
      return;
    }
    notifyListeners();
  }

  Future<void> applySuggestion(String value) async {
    query = value;
    _resetSuggestionDebounce();
    if (suggestions.isNotEmpty) {
      suggestions = const [];
    }
    await search();
  }

  int _resetSuggestionDebounce() {
    _debounce?.cancel();
    _debounce = null;
    return ++_suggestionRequestId;
  }

  bool _isActiveSuggestionRequest(int requestId, String expectedQuery) {
    return requestId == _suggestionRequestId && query.trim() == expectedQuery;
  }

  String _buildSearchSignature(String normalizedQuery) {
    return '$normalizedQuery|$includeChains|$openNow|$walkingDistance|'
        '$walkingThresholdMinutes|$userLat|$userLng';
  }
}
