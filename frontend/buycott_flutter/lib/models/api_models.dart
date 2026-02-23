double? _toDouble(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

int? _toInt(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.round();
  }
  return int.tryParse(value.toString());
}

class SearchResult {
  SearchResult({
    required this.id,
    required this.name,
    required this.lat,
    required this.lng,
    required this.distanceKm,
    required this.minutesAway,
    required this.drivingMinutes,
    required this.walkingMinutes,
    required this.evidenceScore,
    required this.isChain,
    required this.openNow,
    required this.badges,
    required this.matchedTerms,
    required this.types,
    required this.lastUpdated,
    this.chainName,
    this.formattedAddress,
    this.phone,
    this.website,
    this.hours,
    this.requestId,
  });

  final int id;
  final String name;
  final double lat;
  final double lng;
  final double distanceKm;
  final int minutesAway;
  final int drivingMinutes;
  final int walkingMinutes;
  final int evidenceScore;
  final bool isChain;
  final bool openNow;
  final List<String> badges;
  final List<String> matchedTerms;
  final List<String> types;
  final DateTime lastUpdated;
  final String? chainName;
  final String? formattedAddress;
  final String? phone;
  final String? website;
  final Map<String, dynamic>? hours;
  final String? requestId;

  factory SearchResult.fromJson(Map<String, dynamic> json, {String? requestId}) {
    return SearchResult(
      id: json['id'] as int,
      name: json['name'] as String,
      lat: (json['lat'] as num).toDouble(),
      lng: (json['lng'] as num).toDouble(),
      distanceKm: (json['distance_km'] as num).toDouble(),
      minutesAway: json['minutes_away'] as int,
      drivingMinutes: json['driving_minutes'] as int,
      walkingMinutes: json['walking_minutes'] as int,
      evidenceScore: json['evidence_score'] as int,
      isChain: json['is_chain'] as bool,
      openNow: json['open_now'] as bool,
      badges: (json['badges'] as List<dynamic>? ?? []).cast<String>(),
      matchedTerms: (json['matched_terms'] as List<dynamic>? ?? []).cast<String>(),
      types: (json['types'] as List<dynamic>? ?? []).map((item) => item.toString()).toList(),
      lastUpdated: DateTime.parse(json['last_updated'] as String),
      chainName: json['chain_name'] as String?,
      formattedAddress: json['formatted_address'] as String?,
      phone: json['phone'] as String?,
      website: json['website'] as String?,
      hours: json['hours'] is Map
          ? Map<String, dynamic>.from(json['hours'] as Map<dynamic, dynamic>)
          : null,
      requestId: json['request_id'] as String? ?? requestId,
    );
  }
}

class SearchPerformanceMetrics {
  SearchPerformanceMetrics({
    this.requestId,
    this.embeddingTimeMs,
    this.expansionTimeMs,
    this.dbTimeMs,
    this.rankingTimeMs,
    this.totalTimeMs,
    this.resultCount,
    this.topSimilarityScore,
  });

  final String? requestId;
  final double? embeddingTimeMs;
  final double? expansionTimeMs;
  final double? dbTimeMs;
  final double? rankingTimeMs;
  final double? totalTimeMs;
  final int? resultCount;
  final double? topSimilarityScore;

  factory SearchPerformanceMetrics.fromJson(Map<String, dynamic> json) {
    return SearchPerformanceMetrics(
      requestId: json['request_id'] as String?,
      embeddingTimeMs: _toDouble(json['embedding_time_ms']),
      expansionTimeMs: _toDouble(json['expansion_time_ms']),
      dbTimeMs: _toDouble(json['db_time_ms']),
      rankingTimeMs: _toDouble(json['ranking_time_ms']),
      totalTimeMs: _toDouble(json['total_time_ms']),
      resultCount: _toInt(json['result_count']),
      topSimilarityScore: _toDouble(json['top_similarity_score']),
    );
  }
}

class SearchPayload {
  SearchPayload({
    required this.query,
    required this.expansionChain,
    required this.relatedItems,
    required this.localOnly,
    required this.results,
    this.requestId,
    this.performance,
  });

  final String query;
  final List<String> expansionChain;
  final List<String> relatedItems;
  final bool localOnly;
  final List<SearchResult> results;
  final String? requestId;
  final SearchPerformanceMetrics? performance;

  factory SearchPayload.fromJson(
    Map<String, dynamic> json, {
    SearchPerformanceMetrics? performance,
  }) {
    final requestId = json['request_id'] as String? ?? performance?.requestId;
    return SearchPayload(
      query: json['query'] as String,
      expansionChain: (json['expansion_chain'] as List<dynamic>? ?? []).cast<String>(),
      relatedItems: (json['related_items'] as List<dynamic>? ?? []).cast<String>(),
      localOnly: json['local_only'] as bool? ?? true,
      results: (json['results'] as List<dynamic>? ?? [])
          .map(
            (item) => SearchResult.fromJson(
              item as Map<String, dynamic>,
              requestId: requestId,
            ),
          )
          .toList(),
      requestId: requestId,
      performance: performance,
    );
  }
}

class Capability {
  Capability({
    required this.ontologyTerm,
    required this.confidenceScore,
    this.sourceReference,
  });

  final String ontologyTerm;
  final double confidenceScore;
  final String? sourceReference;

  factory Capability.fromJson(Map<String, dynamic> json) {
    return Capability(
      ontologyTerm: json['ontology_term'] as String,
      confidenceScore: (json['confidence_score'] as num).toDouble(),
      sourceReference: json['source_reference'] as String?,
    );
  }
}

class CapabilityPayload {
  CapabilityPayload({
    required this.businessId,
    required this.capabilities,
    required this.menuItems,
  });

  final int businessId;
  final List<Capability> capabilities;
  final List<String> menuItems;

  factory CapabilityPayload.fromJson(Map<String, dynamic> json) {
    return CapabilityPayload(
      businessId: json['business_id'] as int,
      capabilities: (json['capabilities'] as List<dynamic>? ?? [])
          .map((item) => Capability.fromJson(item as Map<String, dynamic>))
          .toList(),
      menuItems: (json['menu_items'] as List<dynamic>? ?? [])
          .map((item) => item.toString().trim())
          .where((item) => item.isNotEmpty)
          .toList(),
    );
  }
}

class EvidenceSource {
  EvidenceSource({
    required this.sourceType,
    this.sourceUrl,
    this.snippet,
    this.lastFetched,
  });

  final String sourceType;
  final String? sourceUrl;
  final String? snippet;
  final DateTime? lastFetched;

  factory EvidenceSource.fromJson(Map<String, dynamic> json) {
    return EvidenceSource(
      sourceType: json['source_type'] as String,
      sourceUrl: json['source_url'] as String?,
      snippet: json['snippet'] as String?,
      lastFetched: (json['last_fetched'] as String?) != null
          ? DateTime.parse(json['last_fetched'] as String)
          : null,
    );
  }
}

class EvidenceExplanation {
  EvidenceExplanation({
    required this.businessId,
    required this.query,
    required this.evidenceScore,
    required this.semanticMatches,
    required this.capabilityMatches,
    required this.evidenceSources,
    required this.lastUpdated,
  });

  final int businessId;
  final String query;
  final int evidenceScore;
  final List<String> semanticMatches;
  final List<Capability> capabilityMatches;
  final List<EvidenceSource> evidenceSources;
  final DateTime lastUpdated;

  factory EvidenceExplanation.fromJson(Map<String, dynamic> json) {
    return EvidenceExplanation(
      businessId: json['business_id'] as int,
      query: json['query'] as String,
      evidenceScore: json['evidence_score'] as int,
      semanticMatches: (json['semantic_matches'] as List<dynamic>? ?? []).cast<String>(),
      capabilityMatches: (json['capability_matches'] as List<dynamic>? ?? [])
          .map((item) => Capability.fromJson(item as Map<String, dynamic>))
          .toList(),
      evidenceSources: (json['evidence_sources'] as List<dynamic>? ?? [])
          .map((item) => EvidenceSource.fromJson(item as Map<String, dynamic>))
          .toList(),
      lastUpdated: DateTime.parse(json['last_updated'] as String),
    );
  }
}
