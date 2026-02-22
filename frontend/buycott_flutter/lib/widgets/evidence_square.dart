import 'package:flutter/material.dart';

import '../design_system.dart';

class EvidenceSquare extends StatelessWidget {
  const EvidenceSquare({
    super.key,
    required this.minutes,
    required this.evidence,
    this.highlight = false,
  });

  final int minutes;
  final int evidence;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final tokens = context.buycottTokens;
    final textTheme = Theme.of(context).textTheme;

    final accentColor = highlight
        ? BuycottColors.accentPrimary
        : tokens.colorForConfidence(evidence);

    return Container(
      width: Dimensions.x8,
      height: Dimensions.x8,
      decoration: BoxDecoration(
        color: BuycottColors.bgSurface,
        borderRadius: BorderRadius.circular(tokens.radiusMd),
        border: Border.all(color: BuycottColors.border),
        boxShadow: tokens.elevationCard,
      ),
      child: Column(
        children: <Widget>[
          Container(
            height: Dimensions.x1,
            decoration: BoxDecoration(
              color: accentColor,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(tokens.radiusMd),
                topRight: Radius.circular(tokens.radiusMd),
              ),
            ),
          ),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Text(
                  '${minutes}m',
                  style: BuycottTypography.numeric(
                    textTheme.bodyLarge!,
                    weight: FontWeight.w700,
                  ),
                ),
                Text(
                  '$evidence',
                  style: BuycottTypography.numeric(
                    textTheme.bodySmall!,
                    weight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
