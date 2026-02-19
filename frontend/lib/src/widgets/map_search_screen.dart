import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';

import '../models/search_models.dart';
import '../services/buycott_api.dart';
import '../state/search_state.dart';
import 'business_detail_sheet.dart';
import 'gradient_pin.dart';

class MapSearchScreen extends StatefulWidget {
  const MapSearchScreen({super.key, required this.api});

  final BuycottApi api;

  @override
  State<MapSearchScreen> createState() => _MapSearchScreenState();
}

class _MapSearchScreenState extends State<MapSearchScreen> {
  final _queryController = TextEditingController();
  late final LatLng _initialCenter;

  @override
  void initState() {
    super.initState();
    final state = context.read<SearchState>();
    _initialCenter = LatLng(state.userLat, state.userLng);
  }

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          _MapCanvas(
            initialCenter: _initialCenter,
            onMarkerTap: (result) => _openDetailSheet(
              context,
              result,
              context.read<SearchState>().query,
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _searchCard(),
                  const SizedBox(height: 10),
                  _filterRow(),
                  const SizedBox(height: 10),
                  _expansionRow(),
                  _relatedRow(),
                ],
              ),
            ),
          ),
          const _LoadingIndicator(),
        ],
      ),
    );
  }

  Widget _searchCard() {
    final state = context.read<SearchState>();
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(20),
      elevation: 5,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _queryController,
              onChanged: state.setQuery,
              onSubmitted: (_) => state.search(),
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Where can I get this nearby?',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.arrow_forward),
                  onPressed: () => state.search(),
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
            Selector<SearchState, List<String>>(
              selector: (_, searchState) => searchState.suggestions,
              shouldRebuild: (previous, next) => !listEquals(previous, next),
              builder: (context, suggestions, _) {
                if (suggestions.isEmpty) {
                  return const SizedBox.shrink();
                }
                final searchState = context.read<SearchState>();
                return Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: suggestions
                        .map(
                          (suggestion) => ActionChip(
                            label: Text(suggestion),
                            onPressed: () {
                              _queryController.text = suggestion;
                              searchState.applySuggestion(suggestion);
                            },
                          ),
                        )
                        .toList(growable: false),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _filterRow() {
    final state = context.read<SearchState>();
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          Selector<SearchState, bool>(
            selector: (_, searchState) => searchState.includeChains,
            builder: (context, includeChains, _) {
              return Row(
                children: [
                  FilterChip(
                    selected: !includeChains,
                    label: const Text('Local only'),
                    onSelected: (selected) =>
                        state.toggleIncludeChains(!selected),
                  ),
                  const SizedBox(width: 8),
                  FilterChip(
                    selected: includeChains,
                    label: const Text('Show chains'),
                    onSelected: state.toggleIncludeChains,
                  ),
                ],
              );
            },
          ),
          const SizedBox(width: 8),
          Selector<SearchState, bool>(
            selector: (_, searchState) => searchState.openNow,
            builder: (context, openNow, _) {
              return FilterChip(
                selected: openNow,
                label: const Text('Open now'),
                onSelected: state.toggleOpenNow,
              );
            },
          ),
          const SizedBox(width: 8),
          Selector<SearchState, bool>(
            selector: (_, searchState) => searchState.walkingDistance,
            builder: (context, walkingDistance, _) {
              return FilterChip(
                selected: walkingDistance,
                label: const Text('Walking distance'),
                onSelected: state.toggleWalkingDistance,
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _expansionRow() {
    return Selector<SearchState, List<String>>(
      selector: (_, state) => state.expandedTerms,
      shouldRebuild: (previous, next) => !listEquals(previous, next),
      builder: (context, terms, _) {
        if (terms.isEmpty) {
          return const SizedBox.shrink();
        }
        return Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0xEE0B1530),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            'Ontology expansion: ${terms.join(' -> ')}',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w500,
            ),
          ),
        );
      },
    );
  }

  Widget _relatedRow() {
    return Selector<SearchState, List<String>>(
      selector: (_, state) => state.relatedItems,
      shouldRebuild: (previous, next) => !listEquals(previous, next),
      builder: (context, relatedItems, _) {
        if (relatedItems.isEmpty) {
          return const SizedBox.shrink();
        }
        final state = context.read<SearchState>();
        return Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xEEFFFFFF),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: relatedItems
                  .map(
                    (item) => ActionChip(
                      label: Text(item),
                      onPressed: () {
                        _queryController.text = item;
                        state.applySuggestion(item);
                      },
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        );
      },
    );
  }

  Future<void> _openDetailSheet(
    BuildContext context,
    SearchResultModel result,
    String query,
  ) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => SizedBox(
        height: MediaQuery.of(context).size.height * 0.78,
        child: BusinessDetailSheet(
          result: result,
          query: query,
          api: widget.api,
        ),
      ),
    );
  }
}

class _MapCanvas extends StatelessWidget {
  const _MapCanvas({
    required this.initialCenter,
    required this.onMarkerTap,
  });

  final LatLng initialCenter;
  final ValueChanged<SearchResultModel> onMarkerTap;

  @override
  Widget build(BuildContext context) {
    return FlutterMap(
      options: MapOptions(
        initialCenter: initialCenter,
        initialZoom: 12.8,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'buycott_frontend',
        ),
        _MapMarkerLayer(onMarkerTap: onMarkerTap),
      ],
    );
  }
}

class _MapMarkerLayer extends StatelessWidget {
  const _MapMarkerLayer({required this.onMarkerTap});

  final ValueChanged<SearchResultModel> onMarkerTap;

  @override
  Widget build(BuildContext context) {
    return Selector<SearchState, List<SearchResultModel>>(
      selector: (_, state) => state.markerResults,
      builder: (context, markerResults, _) {
        final markers = markerResults
            .map(
              (result) => Marker(
                point: LatLng(result.lat, result.lng),
                width: 68,
                height: 84,
                child: GestureDetector(
                  onTap: () => onMarkerTap(result),
                  child: GradientSquarePin(
                    minutesAway: result.minutesAway,
                    evidenceStrength: result.evidenceStrength,
                    highlighted: result.independentBadge,
                  ),
                ),
              ),
            )
            .toList(growable: false);
        return MarkerLayer(markers: markers);
      },
    );
  }
}

class _LoadingIndicator extends StatelessWidget {
  const _LoadingIndicator();

  @override
  Widget build(BuildContext context) {
    return Selector<SearchState, bool>(
      selector: (_, state) => state.loading,
      builder: (context, loading, _) {
        if (!loading) {
          return const SizedBox.shrink();
        }
        return const Positioned(
          top: 0,
          left: 0,
          right: 0,
          child: LinearProgressIndicator(minHeight: 3),
        );
      },
    );
  }
}
