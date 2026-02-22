import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import 'design_system.dart';
import 'models/api_models.dart';
import 'services/api_service.dart';
import 'widgets/buycott_card.dart';
import 'widgets/evidence_square.dart';
import 'widgets/primary_button.dart';

void main() {
  runApp(const BuycottApp());
}

class BuycottApp extends StatelessWidget {
  const BuycottApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Buycott',
      theme: BuycottDesignSystem.darkTheme(),
      home: const BuycottMapPage(),
    );
  }
}

class BuycottMapPage extends StatefulWidget {
  const BuycottMapPage({super.key});

  @override
  State<BuycottMapPage> createState() => _BuycottMapPageState();
}

class _BuycottMapPageState extends State<BuycottMapPage> {
  final BuycottApiService _api = BuycottApiService();
  final TextEditingController _queryController = TextEditingController();
  final FocusNode _queryFocusNode = FocusNode();
  final MapController _mapController = MapController();

  static const LatLng _userLocation = LatLng(44.9778, -93.2650);
  static const int _maxVisibleMapMarkers = 24;
  static const double _mapHighlightOpacity = 0.15;

  Timer? _debounce;
  bool _loading = false;
  bool _localOnly = true;
  bool _openNow = false;
  bool _walkingDistance = false;
  bool _showAllBusinesses = false;
  String? _error;

  SearchPayload? _searchPayload;
  SearchPerformanceMetrics? _searchPerformance;
  List<SearchResult> _results = const <SearchResult>[];
  List<String> _suggestions = const <String>[];

  SearchResult? _highestProbabilityMatch(List<SearchResult> results) {
    if (results.isEmpty) {
      return null;
    }
    return results.reduce((best, candidate) {
      if (candidate.evidenceScore != best.evidenceScore) {
        return candidate.evidenceScore > best.evidenceScore ? candidate : best;
      }
      if (candidate.minutesAway != best.minutesAway) {
        return candidate.minutesAway < best.minutesAway ? candidate : best;
      }
      if (candidate.distanceKm != best.distanceKm) {
        return candidate.distanceKm < best.distanceKm ? candidate : best;
      }
      return candidate.name.compareTo(best.name) < 0 ? candidate : best;
    });
  }

  @override
  void initState() {
    super.initState();
    _queryController.addListener(_onQueryChanged);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _queryController.removeListener(_onQueryChanged);
    _queryController.dispose();
    _queryFocusNode.dispose();
    super.dispose();
  }

  void _onQueryChanged() {
    _debounce?.cancel();
    final text = _queryController.text.trim();
    if (text.length < 2) {
      if (_suggestions.isNotEmpty) {
        setState(() => _suggestions = const <String>[]);
      }
      return;
    }

    _debounce = Timer(const Duration(milliseconds: 250), () async {
      try {
        final suggestions = await _api.suggestions(text);
        if (!mounted) {
          return;
        }
        setState(() => _suggestions = suggestions);
      } catch (_) {
        if (!mounted) {
          return;
        }
        setState(() => _suggestions = const <String>[]);
      }
    });
  }

  Future<void> _performSearch({String? queryOverride}) async {
    final query = (queryOverride ?? _queryController.text).trim();
    if (!_showAllBusinesses && query.isEmpty) {
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _suggestions = const <String>[];
    });

    try {
      final payload = _showAllBusinesses
          ? await _api.businesses(
              lat: _userLocation.latitude,
              lng: _userLocation.longitude,
              includeChains: !_localOnly,
              openNow: _openNow,
              walkingDistance: _walkingDistance,
            )
          : await _api.search(
              query: query,
              lat: _userLocation.latitude,
              lng: _userLocation.longitude,
              includeChains: !_localOnly,
              openNow: _openNow,
              walkingDistance: _walkingDistance,
            );

      if (!mounted) {
        return;
      }

      setState(() {
        _searchPayload = payload;
        _searchPerformance = payload.performance;
        _results = payload.results;
        _loading = false;
      });

      final bestMatch = _highestProbabilityMatch(payload.results);
      if (bestMatch != null) {
        _mapController.move(LatLng(bestMatch.lat, bestMatch.lng), 14);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _onFilterChange({
    bool? localOnly,
    bool? openNow,
    bool? walkingDistance,
  }) async {
    setState(() {
      if (localOnly != null) {
        _localOnly = localOnly;
      }
      if (openNow != null) {
        _openNow = openNow;
      }
      if (walkingDistance != null) {
        _walkingDistance = walkingDistance;
      }
    });

    if (_showAllBusinesses ||
        _searchPayload != null ||
        _queryController.text.trim().isNotEmpty) {
      await _performSearch();
    }
  }

  Future<void> _openBusinessSheet(SearchResult result) async {
    final capsFuture = _api.capabilities(result.id, limit: 30);

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) {
        final textTheme = Theme.of(context).textTheme;
        final tokens = context.buycottTokens;

        final hasPhone = (result.phone ?? '').trim().isNotEmpty;
        final hasWebsite = (result.website ?? '').trim().isNotEmpty;
        final hasHours = result.hours != null;

        return SafeArea(
          child: Padding(
            padding: Dimensions.sheetPadding,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(
                        child: Text(
                          result.name,
                          style: textTheme.headlineMedium,
                        ),
                      ),
                      const SizedBox(width: Dimensions.x1),
                      GestureDetector(
                        onTap: () => _showEvidencePanel(result),
                        child: EvidenceSquare(
                          minutes: result.minutesAway,
                          evidence: result.evidenceScore,
                          highlight: !result.isChain,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: Dimensions.x2),
                  Wrap(
                    spacing: Dimensions.x1,
                    runSpacing: Dimensions.x1,
                    children: <Widget>[
                      ...result.badges.map((badge) {
                        return Chip(
                          label: Text(badge),
                          backgroundColor: badge == 'Independent'
                              ? BuycottColors.accentDim.withValues(
                                  alpha: tokens.activeOverlayOpacity)
                              : BuycottColors.bgPrimary,
                        );
                      }),
                      Chip(
                        label: Text(result.openNow ? 'Open now' : 'Closed now'),
                        labelStyle: textTheme.bodySmall?.copyWith(
                          color: result.openNow
                              ? BuycottColors.semanticSuccess
                              : BuycottColors.semanticError,
                        ),
                        backgroundColor: BuycottColors.bgPrimary,
                      ),
                    ],
                  ),
                  const SizedBox(height: Dimensions.x2),
                  Text(
                    '${result.distanceKm.toStringAsFixed(1)} km away',
                    style: textTheme.bodyMedium,
                  ),
                  if ((result.formattedAddress ?? '')
                      .trim()
                      .isNotEmpty) ...<Widget>[
                    const SizedBox(height: Dimensions.x1),
                    Text(result.formattedAddress!, style: textTheme.bodyMedium),
                  ],
                  const SizedBox(height: Dimensions.x1),
                  Text(
                    'Time-to-possession: ${result.minutesAway}m',
                    style: textTheme.bodyMedium,
                  ),
                  const SizedBox(height: Dimensions.x1),
                  Text(
                    'Driving ${result.drivingMinutes}m • Walking ${result.walkingMinutes}m',
                    style: textTheme.bodySmall,
                  ),
                  if (result.types.isNotEmpty) ...<Widget>[
                    const SizedBox(height: Dimensions.x2),
                    Container(
                      decoration: BoxDecoration(
                        color: BuycottColors.bgPrimary,
                        borderRadius: BorderRadius.circular(tokens.radiusMd),
                        border: Border.all(color: BuycottColors.border),
                      ),
                      child: Theme(
                        data: Theme.of(context).copyWith(
                          dividerColor: BuycottColors.bgPrimary,
                        ),
                        child: ExpansionTile(
                          tilePadding: const EdgeInsets.symmetric(
                            horizontal: Dimensions.x2,
                          ),
                          childrenPadding: const EdgeInsets.fromLTRB(
                            Dimensions.x2,
                            0,
                            Dimensions.x2,
                            Dimensions.x2,
                          ),
                          iconColor: BuycottColors.accentPrimary,
                          collapsedIconColor: BuycottColors.textSecondary,
                          title: Text(
                            'Keywords',
                            style: textTheme.bodyMedium
                                ?.copyWith(fontWeight: FontWeight.w600),
                          ),
                          subtitle: Text(
                            'Expand to view business types',
                            style: textTheme.bodySmall
                                ?.copyWith(color: BuycottColors.textSecondary),
                          ),
                          children: <Widget>[
                            Align(
                              alignment: Alignment.centerLeft,
                              child: Wrap(
                                spacing: Dimensions.x1,
                                runSpacing: Dimensions.x1,
                                children: result.types.map((type) {
                                  return Chip(
                                    label: Text(type),
                                    backgroundColor: BuycottColors.bgSurface,
                                  );
                                }).toList(),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: Dimensions.x1),
                  Text(_freshnessLabel(result.lastUpdated),
                      style: textTheme.bodySmall),
                  if ((result.requestId ?? _searchPayload?.requestId) !=
                      null) ...<Widget>[
                    const SizedBox(height: Dimensions.x1),
                    Text(
                      'Trace request: ${result.requestId ?? _searchPayload?.requestId}',
                      style: textTheme.bodySmall
                          ?.copyWith(color: BuycottColors.textSecondary),
                    ),
                  ],
                  const SizedBox(height: Dimensions.x2),
                  PrimaryButton(
                    label: 'Directions',
                    icon: Icons.directions,
                    onPressed: () => _launchDirections(result),
                    expand: true,
                  ),
                  const SizedBox(height: Dimensions.x1),
                  Wrap(
                    spacing: Dimensions.x1,
                    runSpacing: Dimensions.x1,
                    children: <Widget>[
                      ActionChip(
                        label: const Text('Call'),
                        onPressed: hasPhone
                            ? () => _launchUrl('tel:${result.phone}')
                            : null,
                        avatar: const Icon(Icons.call, size: Dimensions.x2),
                      ),
                      ActionChip(
                        label: const Text('Website'),
                        onPressed: hasWebsite
                            ? () => _launchUrl(result.website!)
                            : null,
                        avatar: const Icon(Icons.language, size: Dimensions.x2),
                      ),
                      ActionChip(
                        label: const Text('Hours'),
                        onPressed:
                            hasHours ? () => _showHoursSheet(result) : null,
                        avatar: const Icon(Icons.schedule, size: Dimensions.x2),
                      ),
                    ],
                  ),
                  const SizedBox(height: Dimensions.x3),
                  Text('Likely carries',
                      style: textTheme.bodyLarge
                          ?.copyWith(fontWeight: FontWeight.w600)),
                  const SizedBox(height: Dimensions.x1),
                  FutureBuilder<CapabilityPayload>(
                    future: capsFuture,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Padding(
                          padding:
                              EdgeInsets.symmetric(vertical: Dimensions.x1),
                          child:
                              LinearProgressIndicator(minHeight: Dimensions.x1),
                        );
                      }
                      if (snapshot.hasError) {
                        return Text('Capability data unavailable',
                            style: textTheme.bodyMedium);
                      }

                      final capabilities =
                          snapshot.data?.capabilities ?? const <Capability>[];
                      final allOpenClawTerms = capabilities
                          .map((capability) => capability.ontologyTerm.trim())
                          .where((term) => term.isNotEmpty)
                          .toSet()
                          .toList()
                        ..sort();

                      if (capabilities.isEmpty) {
                        return Text('No inferred capabilities yet.',
                            style: textTheme.bodyMedium);
                      }

                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Wrap(
                            spacing: Dimensions.x1,
                            runSpacing: Dimensions.x1,
                            children: capabilities.take(8).map((capability) {
                              return Chip(
                                label: Text(capability.ontologyTerm),
                                backgroundColor: BuycottColors.bgPrimary,
                              );
                            }).toList(),
                          ),
                          const SizedBox(height: Dimensions.x2),
                          Container(
                            decoration: BoxDecoration(
                              color: BuycottColors.bgPrimary,
                              borderRadius:
                                  BorderRadius.circular(tokens.radiusMd),
                              border: Border.all(color: BuycottColors.border),
                            ),
                            child: Theme(
                              data: Theme.of(context).copyWith(
                                dividerColor: BuycottColors.bgPrimary,
                              ),
                              child: ExpansionTile(
                                tilePadding: const EdgeInsets.symmetric(
                                  horizontal: Dimensions.x2,
                                ),
                                childrenPadding: const EdgeInsets.fromLTRB(
                                  Dimensions.x2,
                                  0,
                                  Dimensions.x2,
                                  Dimensions.x2,
                                ),
                                iconColor: BuycottColors.accentPrimary,
                                collapsedIconColor: BuycottColors.textSecondary,
                                title: Text(
                                  'OpenClaw terms',
                                  style: textTheme.bodyMedium
                                      ?.copyWith(fontWeight: FontWeight.w600),
                                ),
                                subtitle: Text(
                                  'Expand to view all ${allOpenClawTerms.length} terms',
                                  style: textTheme.bodySmall?.copyWith(
                                    color: BuycottColors.textSecondary,
                                  ),
                                ),
                                children: <Widget>[
                                  Align(
                                    alignment: Alignment.centerLeft,
                                    child: Wrap(
                                      spacing: Dimensions.x1,
                                      runSpacing: Dimensions.x1,
                                      children: allOpenClawTerms.map((term) {
                                        return Chip(
                                          label: Text(term),
                                          backgroundColor: BuycottColors
                                              .accentDim
                                              .withValues(
                                            alpha: tokens.hoverOverlayOpacity,
                                          ),
                                        );
                                      }).toList(),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: Dimensions.x3),
                  Text('Match terms',
                      style: textTheme.bodyLarge
                          ?.copyWith(fontWeight: FontWeight.w600)),
                  const SizedBox(height: Dimensions.x1),
                  Wrap(
                    spacing: Dimensions.x1,
                    runSpacing: Dimensions.x1,
                    children: result.matchedTerms.map((term) {
                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: Dimensions.x2,
                          vertical: Dimensions.x1,
                        ),
                        decoration: BoxDecoration(
                          color: BuycottColors.accentDim
                              .withValues(alpha: tokens.hoverOverlayOpacity),
                          borderRadius: BorderRadius.circular(tokens.radiusMd),
                        ),
                        child: Text(term, style: textTheme.bodySmall),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _showEvidencePanel(SearchResult result) async {
    final query = _searchPayload?.query ?? _queryController.text.trim();
    if (query.isEmpty) {
      return;
    }

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) {
        final textTheme = Theme.of(context).textTheme;

        return FutureBuilder<EvidenceExplanation>(
          future: _api.evidenceExplanation(businessId: result.id, query: query),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const SizedBox(
                height: 224,
                child: Center(child: CircularProgressIndicator()),
              );
            }
            if (snapshot.hasError || !snapshot.hasData) {
              return SizedBox(
                height: 192,
                child: Center(
                  child: Text('Evidence explanation unavailable',
                      style: textTheme.bodyMedium),
                ),
              );
            }

            final evidence = snapshot.data!;
            return SafeArea(
              child: Padding(
                padding: Dimensions.sheetPadding,
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              'Evidence explanation',
                              style: textTheme.headlineMedium,
                            ),
                          ),
                          const SizedBox(width: Dimensions.x1),
                          EvidenceSquare(
                            minutes: result.minutesAway,
                            evidence: evidence.evidenceScore,
                          ),
                        ],
                      ),
                      const SizedBox(height: Dimensions.x2),
                      Text(
                        'Semantic matches',
                        style: textTheme.bodyLarge
                            ?.copyWith(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: Dimensions.x1),
                      ...evidence.semanticMatches.map(
                        (line) => Padding(
                          padding: const EdgeInsets.only(bottom: Dimensions.x1),
                          child: Text('• $line', style: textTheme.bodyMedium),
                        ),
                      ),
                      const SizedBox(height: Dimensions.x2),
                      Text(
                        'Capability links',
                        style: textTheme.bodyLarge
                            ?.copyWith(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: Dimensions.x1),
                      ...evidence.capabilityMatches.map(
                        (match) => Padding(
                          padding: const EdgeInsets.only(bottom: Dimensions.x1),
                          child: Text(
                            '• ${match.ontologyTerm} (${(match.confidenceScore * 100).round()}%)',
                            style: textTheme.bodyMedium,
                          ),
                        ),
                      ),
                      const SizedBox(height: Dimensions.x2),
                      Text(
                        'Data sources',
                        style: textTheme.bodyLarge
                            ?.copyWith(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: Dimensions.x1),
                      ...evidence.evidenceSources.map(
                        (source) => Padding(
                          padding: const EdgeInsets.only(bottom: Dimensions.x1),
                          child: Text(
                            '• ${source.sourceType}: ${source.snippet ?? source.sourceUrl ?? 'n/a'}',
                            style: textTheme.bodyMedium,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _launchDirections(SearchResult result) async {
    final url =
        'https://www.google.com/maps/dir/?api=1&destination=${result.lat},${result.lng}&travelmode=driving';
    await _launchUrl(url);
  }

  Future<void> _showHoursSheet(SearchResult result) async {
    final hours = result.hours;
    if (hours == null) {
      return;
    }

    final rawWeekdays = hours['weekdayDescriptions'];
    final weekdayLines = (rawWeekdays is List)
        ? rawWeekdays
            .whereType<String>()
            .where((line) => line.trim().isNotEmpty)
            .toList()
        : <String>[];

    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        final textTheme = Theme.of(context).textTheme;

        return SafeArea(
          child: Padding(
            padding: Dimensions.sheetPadding,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Business hours', style: textTheme.headlineMedium),
                const SizedBox(height: Dimensions.x2),
                if (weekdayLines.isEmpty)
                  Text(
                    'Hours available but weekday detail is not provided.',
                    style: textTheme.bodyMedium,
                  )
                else
                  ...weekdayLines.map(
                    (line) => Padding(
                      padding: const EdgeInsets.only(bottom: Dimensions.x1),
                      child: Text(line, style: textTheme.bodyMedium),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _launchUrl(String rawUrl) async {
    final uri = Uri.tryParse(rawUrl);
    if (uri == null) {
      return;
    }
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not open link')),
      );
    }
  }

  String _freshnessLabel(DateTime timestamp) {
    final days = DateTime.now().difference(timestamp.toLocal()).inDays;
    if (days <= 0) {
      return 'Last updated today';
    }
    if (days == 1) {
      return 'Last updated 1 day ago';
    }
    return 'Last updated $days days ago';
  }

  String? _traceSummaryLabel() {
    final requestId = _searchPayload?.requestId;
    final compactRequestId =
        (requestId != null && requestId.length > Dimensions.x1)
            ? requestId.substring(0, Dimensions.x1.toInt())
            : requestId;
    final totalMs = _searchPerformance?.totalTimeMs;

    if (compactRequestId != null && totalMs != null) {
      return 'Trace $compactRequestId • API ${totalMs.toStringAsFixed(1)} ms';
    }
    if (compactRequestId != null) {
      return 'Trace $compactRequestId';
    }
    if (totalMs != null) {
      return 'API ${totalMs.toStringAsFixed(1)} ms';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final tokens = context.buycottTokens;
    final visibleResults = _showAllBusinesses
        ? _results
        : _results.take(_maxVisibleMapMarkers).toList();

    final markers = visibleResults.map((result) {
      return Marker(
        width: Dimensions.x6,
        height: Dimensions.x6,
        point: LatLng(result.lat, result.lng),
        child: Tooltip(
          message:
              'request_id: ${result.requestId ?? _searchPayload?.requestId ?? 'n/a'}',
          child: _MapResultMarker(
            confidenceScore: result.evidenceScore,
            confidenceColor: tokens.colorForConfidence(result.evidenceScore),
            onTap: () => _openBusinessSheet(result),
          ),
        ),
      );
    }).toList();

    return Scaffold(
      body: Stack(
        children: <Widget>[
          FlutterMap(
            mapController: _mapController,
            options: const MapOptions(
              initialCenter: _userLocation,
              initialZoom: 13.5,
              minZoom: 4,
              maxZoom: 18,
            ),
            children: <Widget>[
              TileLayer(
                urlTemplate:
                    'https://basemaps.cartocdn.com/rastertiles/dark_nolabels/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.buycott.app',
              ),
              MarkerLayer(markers: markers),
              MarkerLayer(
                markers: <Marker>[
                  Marker(
                    point: _userLocation,
                    width: Dimensions.x4,
                    height: Dimensions.x4,
                    child: Container(
                      decoration: BoxDecoration(
                        color: BuycottColors.textPrimary,
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: BuycottColors.accentPrimary,
                          width: 2,
                        ),
                        boxShadow: tokens.elevationCard,
                      ),
                      child: Center(
                        child: Container(
                          width: Dimensions.x1,
                          height: Dimensions.x1,
                          decoration: const BoxDecoration(
                            color: BuycottColors.accentPrimary,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          IgnorePointer(
            child: Container(
              color: BuycottColors.textPrimary
                  .withValues(alpha: _mapHighlightOpacity),
            ),
          ),
          SafeArea(
            child: Align(
              alignment: Alignment.topCenter,
              child: Padding(
                padding: const EdgeInsets.all(Dimensions.x2),
                child: BuycottCard(
                  padding: const EdgeInsets.all(Dimensions.x2),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Expanded(
                            child: TextField(
                              focusNode: _queryFocusNode,
                              controller: _queryController,
                              onSubmitted: (_) => _performSearch(),
                              decoration: const InputDecoration(
                                hintText: 'Where can I get this nearby?',
                                prefixIcon: Icon(Icons.search),
                              ),
                            ),
                          ),
                          const SizedBox(width: Dimensions.x1),
                          SizedBox(
                            width: 96,
                            child: PrimaryButton(
                              label: 'Go',
                              onPressed: _loading ? null : _performSearch,
                              isLoading: _loading,
                              expand: true,
                            ),
                          ),
                        ],
                      ),
                      if (_suggestions.isNotEmpty &&
                          _queryFocusNode.hasFocus) ...<Widget>[
                        const SizedBox(height: Dimensions.x1),
                        SizedBox(
                          height: 112,
                          child: ListView.builder(
                            itemCount: _suggestions.length,
                            itemBuilder: (context, index) {
                              final suggestion = _suggestions[index];
                              return ListTile(
                                dense: true,
                                title: Text(suggestion,
                                    style: textTheme.bodyMedium),
                                onTap: () {
                                  _queryController.text = suggestion;
                                  _queryFocusNode.unfocus();
                                  _performSearch(queryOverride: suggestion);
                                },
                              );
                            },
                          ),
                        ),
                      ],
                      const SizedBox(height: Dimensions.x1),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: <Widget>[
                            FilterChip(
                              label: const Text('Local only'),
                              selected: _localOnly,
                              onSelected: (value) =>
                                  _onFilterChange(localOnly: value),
                            ),
                            const SizedBox(width: Dimensions.x1),
                            FilterChip(
                              label: const Text('Open now'),
                              selected: _openNow,
                              onSelected: (value) =>
                                  _onFilterChange(openNow: value),
                            ),
                            const SizedBox(width: Dimensions.x1),
                            FilterChip(
                              label: const Text('Walking distance'),
                              selected: _walkingDistance,
                              onSelected: (value) =>
                                  _onFilterChange(walkingDistance: value),
                            ),
                            const SizedBox(width: Dimensions.x1),
                            FilterChip(
                              label: const Text('Show all businesses'),
                              selected: _showAllBusinesses,
                              onSelected: (value) async {
                                setState(() {
                                  _showAllBusinesses = value;
                                });
                                if (_showAllBusinesses ||
                                    _searchPayload != null ||
                                    _queryController.text.trim().isNotEmpty) {
                                  await _performSearch();
                                }
                              },
                            ),
                          ],
                        ),
                      ),
                      if (_searchPayload != null) ...<Widget>[
                        const SizedBox(height: Dimensions.x1),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            '${_results.length} places matched',
                            style: textTheme.bodyMedium
                                ?.copyWith(fontWeight: FontWeight.w600),
                          ),
                        ),
                        if (!_showAllBusinesses &&
                            _results.length >
                                _maxVisibleMapMarkers) ...<Widget>[
                          const SizedBox(height: Dimensions.x1),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              'Showing nearest $_maxVisibleMapMarkers on map',
                              style: textTheme.bodySmall?.copyWith(
                                  color: BuycottColors.textSecondary),
                            ),
                          ),
                        ],
                        if (_showAllBusinesses) ...<Widget>[
                          const SizedBox(height: Dimensions.x1),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              'Showing all businesses (confidence agnostic)',
                              style: textTheme.bodySmall?.copyWith(
                                  color: BuycottColors.textSecondary),
                            ),
                          ),
                        ],
                        if (_traceSummaryLabel() != null) ...<Widget>[
                          const SizedBox(height: Dimensions.x1),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              _traceSummaryLabel()!,
                              style: textTheme.bodySmall?.copyWith(
                                color: BuycottColors.accentPrimary,
                              ),
                            ),
                          ),
                        ],
                      ],
                      if ((_searchPayload?.expansionChain ?? const <String>[])
                          .isNotEmpty) ...<Widget>[
                        const SizedBox(height: Dimensions.x1),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            'Ontology chain: ${_searchPayload!.expansionChain.join(' -> ')}',
                            style: textTheme.bodySmall
                                ?.copyWith(color: BuycottColors.textSecondary),
                          ),
                        ),
                      ],
                      if ((_searchPayload?.relatedItems ?? const <String>[])
                          .isNotEmpty) ...<Widget>[
                        const SizedBox(height: Dimensions.x1),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Wrap(
                            spacing: Dimensions.x1,
                            runSpacing: Dimensions.x1,
                            children: _searchPayload!.relatedItems.map((item) {
                              return ActionChip(
                                label: Text(item),
                                onPressed: () {
                                  _queryController.text = item;
                                  _performSearch(queryOverride: item);
                                },
                              );
                            }).toList(),
                          ),
                        ),
                      ],
                      if (_error != null) ...<Widget>[
                        const SizedBox(height: Dimensions.x1),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            _error!,
                            style: textTheme.bodySmall
                                ?.copyWith(color: BuycottColors.semanticError),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MapResultMarker extends StatelessWidget {
  const _MapResultMarker({
    required this.confidenceScore,
    required this.confidenceColor,
    required this.onTap,
  });

  final int confidenceScore;
  final Color confidenceColor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final tokens = context.buycottTokens;
    final clampedScore = confidenceScore.clamp(0, 100);
    final glowFactor = clampedScore / 100;
    final glowOpacity = 0.2 + (0.5 * glowFactor);
    final glowBlur = 4 + (12 * glowFactor);
    final glowSpread = 0.5 + (2 * glowFactor);

    return Material(
      color: BuycottColors.bgSurface,
      shape: const CircleBorder(),
      child: InkWell(
        onTap: onTap,
        customBorder: const CircleBorder(),
        child: Container(
          width: Dimensions.x6,
          height: Dimensions.x6,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: confidenceColor, width: 2),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: confidenceColor.withValues(alpha: glowOpacity),
                blurRadius: glowBlur,
                spreadRadius: glowSpread,
              ),
              ...tokens.elevationCard,
            ],
          ),
          alignment: Alignment.center,
          child: Text(
            '$clampedScore',
            style: BuycottTypography.numeric(
              textTheme.bodySmall!,
              weight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}
