import 'package:flutter/material.dart';

import '../models/search_models.dart';
import '../services/buycott_api.dart';

class BusinessDetailSheet extends StatelessWidget {
  const BusinessDetailSheet({
    super.key,
    required this.result,
    required this.query,
    required this.api,
  });

  final SearchResultModel result;
  final String query;
  final BuycottApi api;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_DetailPayload>(
      future: _loadDetail(),
      builder: (context, snapshot) {
        final payload = snapshot.data;

        return Container(
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 28),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: ListView(
            children: [
              Center(
                child: Container(
                  height: 4,
                  width: 54,
                  decoration: BoxDecoration(
                    color: const Color(0xFFCDD5E1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Text(
                result.name,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _pill('${result.minutesAway} min away'),
                  _pill('Evidence ${result.evidenceStrength}'),
                  _pill('${result.distanceKm.toStringAsFixed(1)} km'),
                  if (result.independentBadge) _pill('Independent'),
                  if (result.specialistBadge) _pill('Specialist'),
                ],
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  _actionButton(Icons.directions, 'Directions'),
                  const SizedBox(width: 8),
                  _actionButton(Icons.call, 'Call'),
                  const SizedBox(width: 8),
                  _actionButton(Icons.public, 'Website'),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                'Likely Carries',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 8),
              if (payload == null)
                const LinearProgressIndicator(minHeight: 2)
              else
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: payload.capabilities
                      .take(8)
                      .map((cap) => _pill(
                          '${cap.term} ${(cap.confidence * 100).round()}%'))
                      .toList(),
                ),
              const SizedBox(height: 20),
              Text(
                'Evidence Explanation',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 8),
              if (payload == null)
                const SizedBox.shrink()
              else
                ...payload.evidence.points
                    .map((point) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.subdirectory_arrow_right),
                          title: Text(point.label),
                          subtitle: Text(point.detail),
                        )),
              const SizedBox(height: 12),
              Text(
                'Sources',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 8),
              if (payload == null)
                const SizedBox.shrink()
              else
                ...payload.sources
                    .map((src) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.link, size: 18),
                          title: Text(src.sourceType),
                          subtitle: Text(src.sourceUrl),
                        )),
            ],
          ),
        );
      },
    );
  }

  Future<_DetailPayload> _loadDetail() async {
    final payload = await Future.wait([
      api.capabilities(result.businessId),
      api.evidenceExplanation(businessId: result.businessId, query: query),
      api.sourceTransparency(result.businessId),
    ]);

    return _DetailPayload(
      capabilities: payload[0] as List<CapabilityModel>,
      evidence: payload[1] as EvidenceExplanationModel,
      sources: payload[2] as List<SourceModel>,
    );
  }

  Widget _actionButton(IconData icon, String label) {
    return Expanded(
      child: FilledButton.tonalIcon(
        onPressed: () {},
        icon: Icon(icon, size: 18),
        label: Text(label),
      ),
    );
  }

  Widget _pill(String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFE9F0FF),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        value,
        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
      ),
    );
  }
}

class _DetailPayload {
  _DetailPayload({
    required this.capabilities,
    required this.evidence,
    required this.sources,
  });

  final List<CapabilityModel> capabilities;
  final EvidenceExplanationModel evidence;
  final List<SourceModel> sources;
}
