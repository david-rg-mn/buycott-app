import 'package:flutter/material.dart';

import '../design_system.dart';

class BuycottCard extends StatelessWidget {
  const BuycottCard({
    super.key,
    required this.child,
    this.padding = Dimensions.cardPadding,
    this.onTap,
    this.selected = false,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final tokens = context.buycottTokens;
    final colorScheme = Theme.of(context).colorScheme;

    final borderRadius = BorderRadius.circular(tokens.radiusMd);
    final borderColor = selected ? colorScheme.primary : BuycottColors.border;
    final boxShadows = selected ? tokens.elevationSheet : tokens.elevationCard;

    final Widget content = AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeInOut,
      padding: padding,
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: borderRadius,
        border: Border.all(color: borderColor, width: selected ? 2 : 1),
        boxShadow: boxShadows,
      ),
      child: child,
    );

    if (onTap == null) {
      return content;
    }

    return Material(
      color: colorScheme.surface.withValues(alpha: 0),
      borderRadius: borderRadius,
      child: InkWell(
        onTap: onTap,
        borderRadius: borderRadius,
        overlayColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.pressed)) {
            return BuycottColors.textPrimary
                .withValues(alpha: tokens.activeOverlayOpacity);
          }
          if (states.contains(WidgetState.hovered) ||
              states.contains(WidgetState.focused)) {
            return BuycottColors.textPrimary
                .withValues(alpha: tokens.hoverOverlayOpacity);
          }
          return null;
        }),
        child: content,
      ),
    );
  }
}
