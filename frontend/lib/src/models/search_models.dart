class SearchResultModel {
  SearchResultModel({
    required this.businessId,
    required this.name,
    required this.lat,
    required this.lng,
    required this.minutesAway,
    required this.walkingMinutes,
    required this.drivingMinutes,
    required this.distanceKm,
    required this.evidenceStrength,
    required this.independentBadge,
    required this.specialistBadge,
    required this.capabilityPreview,
    required this.sourceTypes,
    required this.lastUpdated,
    required this.isChain,
    required this.chainName,
  });

  final String businessId;
  final String name;
  final double lat;
  final double lng;
  final int minutesAway;
  final int walkingMinutes;
  final int drivingMinutes;
  final double distanceKm;
  final int evidenceStrength;
  final bool independentBadge;
  final bool specialistBadge;
  final List<String> capabilityPreview;
  final List<String> sourceTypes;
  final DateTime lastUpdated;
  final bool isChain;
  final String? chainName;

  factory SearchResultModel.fromJson(Map<String, dynamic> json) {
    return SearchResultModel(
      businessId: json['business_id'] as String,
      name: json['name'] as String,
      lat: (json['lat'] as num).toDouble(),
      lng: (json['lng'] as num).toDouble(),
      minutesAway: json['minutes_away'] as int,
      walkingMinutes: json['walking_minutes'] as int,
      drivingMinutes: json['driving_minutes'] as int,
      distanceKm: (json['distance_km'] as num).toDouble(),
      evidenceStrength: json['evidence_strength'] as int,
      independentBadge: json['independent_badge'] as bool,
      specialistBadge: json['specialist_badge'] as bool,
      capabilityPreview: List<String>.from(json['capability_preview'] as List<dynamic>),
      sourceTypes: List<String>.from(json['source_types'] as List<dynamic>),
      lastUpdated: DateTime.parse(json['last_updated'] as String),
      isChain: json['is_chain'] as bool,
      chainName: json['chain_name'] as String?,
    );
  }
}

class SearchResponseModel {
  SearchResponseModel({
    required this.query,
    required this.expandedTerms,
    required this.results,
  });

  final String query;
  final List<String> expandedTerms;
  final List<SearchResultModel> results;

  factory SearchResponseModel.fromJson(Map<String, dynamic> json) {
    return SearchResponseModel(
      query: json['query'] as String,
      expandedTerms: List<String>.from(json['expanded_terms'] as List<dynamic>),
      results: (json['results'] as List<dynamic>)
          .map((e) => SearchResultModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class EvidencePointModel {
  EvidencePointModel({required this.label, required this.detail});

  final String label;
  final String detail;

  factory EvidencePointModel.fromJson(Map<String, dynamic> json) {
    return EvidencePointModel(
      label: json['label'] as String,
      detail: json['detail'] as String,
    );
  }
}

class EvidenceExplanationModel {
  EvidenceExplanationModel({
    required this.evidenceStrength,
    required this.points,
    required this.ontologyMatchChain,
  });

  final int evidenceStrength;
  final List<EvidencePointModel> points;
  final List<String> ontologyMatchChain;

  factory EvidenceExplanationModel.fromJson(Map<String, dynamic> json) {
    return EvidenceExplanationModel(
      evidenceStrength: json['evidence_strength'] as int,
      points: (json['points'] as List<dynamic>)
          .map((e) => EvidencePointModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      ontologyMatchChain: List<String>.from(json['ontology_match_chain'] as List<dynamic>),
    );
  }
}

class CapabilityModel {
  CapabilityModel({required this.term, required this.confidence});

  final String term;
  final double confidence;

  factory CapabilityModel.fromJson(Map<String, dynamic> json) {
    return CapabilityModel(
      term: json['ontology_term'] as String,
      confidence: (json['confidence_score'] as num).toDouble(),
    );
  }
}

class SourceModel {
  SourceModel({required this.sourceType, required this.sourceUrl});

  final String sourceType;
  final String sourceUrl;

  factory SourceModel.fromJson(Map<String, dynamic> json) {
    return SourceModel(
      sourceType: json['source_type'] as String,
      sourceUrl: json['source_url'] as String,
    );
  }
}
