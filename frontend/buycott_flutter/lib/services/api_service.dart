import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/api_models.dart';

const String defaultApiBaseUrl = String.fromEnvironment(
  'BUYCOTT_API_URL',
  defaultValue: 'http://localhost:8000',
);

class BuycottApiService {
  BuycottApiService({String? baseUrl}) : _baseUrl = baseUrl ?? defaultApiBaseUrl;

  final String _baseUrl;

  Uri _buildUri(String path, Map<String, String> queryParams) {
    return Uri.parse('$_baseUrl$path').replace(queryParameters: queryParams);
  }

  Future<Map<String, dynamic>> _getJson(Uri uri) async {
    final response = await http.get(uri);
    if (response.statusCode >= 400) {
      throw Exception('API error ${response.statusCode}: ${response.body}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  SearchPerformanceMetrics? _parsePerformanceHeader(http.Response response) {
    final rawHeader = response.headers['x-search-performance'];
    if (rawHeader == null || rawHeader.isEmpty) {
      return null;
    }
    try {
      final decoded = jsonDecode(rawHeader);
      if (decoded is Map<String, dynamic>) {
        return SearchPerformanceMetrics.fromJson(decoded);
      }
      if (decoded is Map) {
        final jsonMap = decoded.map(
          (key, value) => MapEntry(key.toString(), value),
        );
        return SearchPerformanceMetrics.fromJson(jsonMap);
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  Future<SearchPayload> search({
    required String query,
    required double lat,
    required double lng,
    required bool includeChains,
    required bool openNow,
    required bool walkingDistance,
    int walkingThresholdMinutes = 15,
  }) async {
    final uri = _buildUri('/api/search', {
      'query': query,
      'lat': lat.toString(),
      'lng': lng.toString(),
      'include_chains': includeChains.toString(),
      'open_now': openNow.toString(),
      'walking_distance': walkingDistance.toString(),
      'walking_threshold_minutes': walkingThresholdMinutes.toString(),
    });

    final response = await http.get(uri);
    if (response.statusCode >= 400) {
      throw Exception('API error ${response.statusCode}: ${response.body}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final performance = _parsePerformanceHeader(response);
    return SearchPayload.fromJson(json, performance: performance);
  }

  Future<List<String>> suggestions(String partial, {int limit = 8}) async {
    final uri = _buildUri('/api/search_suggestions', {
      'q': partial,
      'limit': limit.toString(),
    });

    final json = await _getJson(uri);
    return (json['suggestions'] as List<dynamic>? ?? []).cast<String>();
  }

  Future<CapabilityPayload> capabilities(int businessId, {int limit = 8}) async {
    final uri = _buildUri('/api/business_capabilities/$businessId', {
      'limit': limit.toString(),
    });

    final json = await _getJson(uri);
    return CapabilityPayload.fromJson(json);
  }

  Future<EvidenceExplanation> evidenceExplanation({
    required int businessId,
    required String query,
  }) async {
    final uri = _buildUri('/api/evidence_explanation', {
      'business_id': businessId.toString(),
      'query': query,
    });

    final json = await _getJson(uri);
    return EvidenceExplanation.fromJson(json);
  }
}
