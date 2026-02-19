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

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<SearchState>(
      builder: (context, state, _) {
        final markers = state.results.map((result) {
          return Marker(
            point: LatLng(result.lat, result.lng),
            width: 68,
            height: 84,
            child: GestureDetector(
              onTap: () => _openDetailSheet(context, result, state.query),
              child: GradientSquarePin(
                minutesAway: result.minutesAway,
                evidenceStrength: result.evidenceStrength,
                highlighted: result.independentBadge,
              ),
            ),
          );
        }).toList();

        return Scaffold(
          body: Stack(
            children: [
              FlutterMap(
                options: MapOptions(
                  initialCenter: LatLng(state.userLat, state.userLng),
                  initialZoom: 12.8,
                ),
                children: [
                  TileLayer(
                    urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'buycott_frontend',
                  ),
                  MarkerLayer(markers: markers),
                ],
              ),
              SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _searchCard(state),
                      const SizedBox(height: 10),
                      _filterRow(state),
                      const SizedBox(height: 10),
                      if (state.expandedTerms.isNotEmpty) _expansionRow(state.expandedTerms),
                      if (state.relatedItems.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        _relatedRow(state),
                      ],
                    ],
                  ),
                ),
              ),
              if (state.loading)
                const Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: LinearProgressIndicator(minHeight: 3),
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _searchCard(SearchState state) {
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
              onChanged: (value) => state.setQuery(value),
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
            if (state.suggestions.isNotEmpty) const SizedBox(height: 8),
            if (state.suggestions.isNotEmpty)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: state.suggestions
                    .map(
                      (suggestion) => ActionChip(
                        label: Text(suggestion),
                        onPressed: () {
                          _queryController.text = suggestion;
                          state.applySuggestion(suggestion);
                        },
                      ),
                    )
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _filterRow(SearchState state) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          FilterChip(
            selected: !state.includeChains,
            label: const Text('Local only'),
            onSelected: (selected) => state.toggleIncludeChains(!selected),
          ),
          const SizedBox(width: 8),
          FilterChip(
            selected: state.includeChains,
            label: const Text('Show chains'),
            onSelected: state.toggleIncludeChains,
          ),
          const SizedBox(width: 8),
          FilterChip(
            selected: state.openNow,
            label: const Text('Open now'),
            onSelected: state.toggleOpenNow,
          ),
          const SizedBox(width: 8),
          FilterChip(
            selected: state.walkingDistance,
            label: const Text('Walking distance'),
            onSelected: state.toggleWalkingDistance,
          ),
        ],
      ),
    );
  }

  Widget _expansionRow(List<String> terms) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xEE0B1530),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        'Ontology expansion: ${terms.join(' -> ')}',
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
      ),
    );
  }

  Widget _relatedRow(SearchState state) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xEEFFFFFF),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: state.relatedItems
            .map(
              (item) => ActionChip(
                label: Text(item),
                onPressed: () {
                  _queryController.text = item;
                  state.applySuggestion(item);
                },
              ),
            )
            .toList(),
      ),
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
