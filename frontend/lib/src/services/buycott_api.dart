import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/search_models.dart';

class BuycottApi {
  BuycottApi({required this.baseUrl, http.Client? client})
      : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  Future<SearchResponseModel> search({
    required String query,
    required double lat,
    required double lng,
    required bool includeChains,
    required bool openNow,
    required bool walkingDistance,
    int walkingThresholdMinutes = 15,
  }) async {
    final uri = Uri.parse('$baseUrl/search').replace(queryParameters: {
      'query': query,
      'lat': '$lat',
      'lng': '$lng',
      'include_chains': '$includeChains',
      'open_now': '$openNow',
      'walking_distance': '$walkingDistance',
      'walking_threshold_minutes': '$walkingThresholdMinutes',
      'limit': '40',
    });

    final response = await _client.get(uri);
    _expectOk(response);
    return SearchResponseModel.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<List<String>> suggestions(String prefix) async {
    final uri = Uri.parse('$baseUrl/search_suggestions').replace(queryParameters: {
      'query_prefix': prefix,
    });
    final response = await _client.get(uri);
    _expectOk(response);

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return List<String>.from(body['suggestions'] as List<dynamic>);
  }

  Future<List<String>> relatedItems(String query) async {
    final uri = Uri.parse('$baseUrl/related_items').replace(queryParameters: {
      'query': query,
    });
    final response = await _client.get(uri);
    _expectOk(response);

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return List<String>.from(body['related_items'] as List<dynamic>);
  }

  Future<EvidenceExplanationModel> evidenceExplanation({
    required String businessId,
    required String query,
  }) async {
    final uri = Uri.parse('$baseUrl/evidence_explanation').replace(queryParameters: {
      'business_id': businessId,
      'query': query,
    });
    final response = await _client.get(uri);
    _expectOk(response);
    return EvidenceExplanationModel.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<List<CapabilityModel>> capabilities(String businessId) async {
    final uri = Uri.parse('$baseUrl/business_capabilities').replace(queryParameters: {
      'business_id': businessId,
    });
    final response = await _client.get(uri);
    _expectOk(response);

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return (body['likely_carries'] as List<dynamic>)
        .map((row) => CapabilityModel.fromJson(row as Map<String, dynamic>))
        .toList();
  }

  Future<List<SourceModel>> sourceTransparency(String businessId) async {
    final uri = Uri.parse('$baseUrl/source_transparency').replace(queryParameters: {
      'business_id': businessId,
    });
    final response = await _client.get(uri);
    _expectOk(response);

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return (body['sources'] as List<dynamic>)
        .map((row) => SourceModel.fromJson(row as Map<String, dynamic>))
        .toList();
  }

  void _expectOk(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('API error ${response.statusCode}: ${response.body}');
    }
  }
}
