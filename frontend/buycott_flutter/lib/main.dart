import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import 'models/api_models.dart';
import 'services/api_service.dart';
import 'widgets/evidence_square.dart';

void main() {
  runApp(const BuycottApp());
}

class BuycottApp extends StatelessWidget {
  const BuycottApp({super.key});

  @override
  Widget build(BuildContext context) {
    final textTheme = GoogleFonts.ibmPlexSansTextTheme();

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Buycott',
      theme: ThemeData(
        useMaterial3: true,
        textTheme: textTheme,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0E7490),
          brightness: Brightness.light,
        ),
      ),
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

  Timer? _debounce;
  bool _loading = false;
  bool _localOnly = true;
  bool _openNow = false;
  bool _walkingDistance = false;
  String? _error;

  SearchPayload? _searchPayload;
  List<SearchResult> _results = const [];
  List<String> _suggestions = const [];

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
        setState(() => _suggestions = const []);
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
        setState(() => _suggestions = const []);
      }
    });
  }

  Future<void> _performSearch({String? queryOverride}) async {
    final query = (queryOverride ?? _queryController.text).trim();
    if (query.isEmpty) {
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _suggestions = const [];
    });

    try {
      final payload = await _api.search(
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
        _results = payload.results;
        _loading = false;
      });

      if (_results.isNotEmpty) {
        final first = _results.first;
        _mapController.move(LatLng(first.lat, first.lng), 13.7);
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

    if (_searchPayload != null || _queryController.text.trim().isNotEmpty) {
      await _performSearch();
    }
  }

  Future<void> _openBusinessSheet(SearchResult result) async {
    final capsFuture = _api.capabilities(result.id);

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          result.name,
                          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
                        ),
                      ),
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
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ...result.badges.map(
                        (badge) => Chip(
                          label: Text(badge),
                          side: BorderSide.none,
                          backgroundColor: badge == 'Independent'
                              ? const Color(0xFFE7F5E8)
                              : const Color(0xFFF7F2E6),
                        ),
                      ),
                      Chip(
                        label: Text(result.openNow ? 'Open now' : 'Closed now'),
                        side: BorderSide.none,
                        backgroundColor: result.openNow
                            ? const Color(0xFFD9FEE3)
                            : const Color(0xFFFFE2E2),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text('${result.distanceKm.toStringAsFixed(1)} km away'),
                  const SizedBox(height: 4),
                  Text('Driving ${result.drivingMinutes}m • Walking ${result.walkingMinutes}m'),
                  const SizedBox(height: 4),
                  Text(_freshnessLabel(result.lastUpdated)),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    children: [
                      FilledButton.tonalIcon(
                        onPressed: () => _launchDirections(result),
                        icon: const Icon(Icons.directions),
                        label: const Text('Directions'),
                      ),
                      if (result.phone != null)
                        FilledButton.tonalIcon(
                          onPressed: () => _launchUrl('tel:${result.phone}'),
                          icon: const Icon(Icons.call),
                          label: const Text('Call'),
                        ),
                      if (result.website != null)
                        FilledButton.tonalIcon(
                          onPressed: () => _launchUrl(result.website!),
                          icon: const Icon(Icons.language),
                          label: const Text('Website'),
                        ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    'Likely carries',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  FutureBuilder<CapabilityPayload>(
                    future: capsFuture,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 10),
                          child: LinearProgressIndicator(minHeight: 3),
                        );
                      }
                      if (snapshot.hasError) {
                        return const Text('Capability data unavailable');
                      }
                      final capabilities = snapshot.data?.capabilities ?? [];
                      if (capabilities.isEmpty) {
                        return const Text('No inferred capabilities yet.');
                      }

                      return Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: capabilities
                            .map(
                              (capability) => Chip(
                                label: Text(
                                  capability.ontologyTerm,
                                  style: const TextStyle(fontSize: 12),
                                ),
                                side: BorderSide.none,
                                backgroundColor: const Color(0xFFE6F3FF),
                              ),
                            )
                            .toList(),
                      );
                    },
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    'Match terms',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: result.matchedTerms
                        .map(
                          (term) => Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: const Color(0xFFECFDF5),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(term),
                          ),
                        )
                        .toList(),
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
        return FutureBuilder<EvidenceExplanation>(
          future: _api.evidenceExplanation(businessId: result.id, query: query),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const SizedBox(
                height: 220,
                child: Center(child: CircularProgressIndicator()),
              );
            }
            if (snapshot.hasError || !snapshot.hasData) {
              return const SizedBox(
                height: 180,
                child: Center(child: Text('Evidence explanation unavailable')),
              );
            }

            final evidence = snapshot.data!;
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Expanded(
                            child: Text(
                              'Evidence explanation',
                              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                            ),
                          ),
                          EvidenceSquare(
                            minutes: result.minutesAway,
                            evidence: evidence.evidenceScore,
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Semantic matches',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 8),
                      ...evidence.semanticMatches.map((line) => Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Text('• $line'),
                          )),
                      const SizedBox(height: 14),
                      const Text(
                        'Capability links',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 8),
                      ...evidence.capabilityMatches.map(
                        (match) => Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Text(
                            '• ${match.ontologyTerm} (${(match.confidenceScore * 100).round()}%)',
                          ),
                        ),
                      ),
                      const SizedBox(height: 14),
                      const Text(
                        'Data sources',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 8),
                      ...evidence.evidenceSources.map(
                        (source) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Text('• ${source.sourceType}: ${source.snippet ?? source.sourceUrl ?? 'n/a'}'),
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

  @override
  Widget build(BuildContext context) {
    final markers = _results
        .map(
          (result) => Marker(
            width: 90,
            height: 94,
            point: LatLng(result.lat, result.lng),
            child: GestureDetector(
              onTap: () => _openBusinessSheet(result),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  EvidenceSquare(
                    minutes: result.minutesAway,
                    evidence: result.evidenceScore,
                    highlight: !result.isChain,
                  ),
                  const Icon(Icons.location_pin, size: 26, color: Color(0xFF1E293B)),
                ],
              ),
            ),
          ),
        )
        .toList();

    return Scaffold(
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: const MapOptions(
              initialCenter: _userLocation,
              initialZoom: 13.4,
              minZoom: 4,
              maxZoom: 18,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.buycott.app',
              ),
              MarkerLayer(markers: markers),
              MarkerLayer(
                markers: [
                  Marker(
                    point: _userLocation,
                    width: 24,
                    height: 24,
                    child: Container(
                      decoration: BoxDecoration(
                        color: const Color(0xFFB91C1C),
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 2),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          SafeArea(
            child: Align(
              alignment: Alignment.topCenter,
              child: Container(
                margin: const EdgeInsets.all(12),
                padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.96),
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x24000000),
                      blurRadius: 12,
                      offset: Offset(0, 3),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            focusNode: _queryFocusNode,
                            controller: _queryController,
                            onSubmitted: (_) => _performSearch(),
                            decoration: const InputDecoration(
                              isDense: true,
                              hintText: 'Where can I get this nearby?',
                              border: OutlineInputBorder(),
                              prefixIcon: Icon(Icons.search),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        FilledButton(
                          onPressed: _loading ? null : _performSearch,
                          child: _loading
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text('Go'),
                        ),
                      ],
                    ),
                    if (_suggestions.isNotEmpty && _queryFocusNode.hasFocus) ...[
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 110,
                        child: ListView.builder(
                          itemCount: _suggestions.length,
                          itemBuilder: (context, index) {
                            final suggestion = _suggestions[index];
                            return ListTile(
                              dense: true,
                              title: Text(suggestion),
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
                    const SizedBox(height: 8),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          FilterChip(
                            label: const Text('Local only'),
                            selected: _localOnly,
                            onSelected: (value) => _onFilterChange(localOnly: value),
                          ),
                          const SizedBox(width: 8),
                          FilterChip(
                            label: const Text('Open now'),
                            selected: _openNow,
                            onSelected: (value) => _onFilterChange(openNow: value),
                          ),
                          const SizedBox(width: 8),
                          FilterChip(
                            label: const Text('Walking distance'),
                            selected: _walkingDistance,
                            onSelected: (value) => _onFilterChange(walkingDistance: value),
                          ),
                        ],
                      ),
                    ),
                    if (_searchPayload != null) ...[
                      const SizedBox(height: 6),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          '${_results.length} places matched',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                    if ((_searchPayload?.expansionChain ?? []).isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Ontology chain: ${_searchPayload!.expansionChain.join(' -> ')}',
                          style: const TextStyle(fontSize: 12, color: Color(0xFF334155)),
                        ),
                      ),
                    ],
                    if ((_searchPayload?.relatedItems ?? []).isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: _searchPayload!.relatedItems
                              .map(
                                (item) => ActionChip(
                                  label: Text(item),
                                  onPressed: () {
                                    _queryController.text = item;
                                    _performSearch(queryOverride: item);
                                  },
                                ),
                              )
                              .toList(),
                        ),
                      ),
                    ],
                    if (_error != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        _error!,
                        style: const TextStyle(color: Color(0xFFB91C1C)),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
