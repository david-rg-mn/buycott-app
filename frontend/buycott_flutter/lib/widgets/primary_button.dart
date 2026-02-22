import 'package:flutter/material.dart';

import '../design_system.dart';

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.isLoading = false,
    this.expand = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isLoading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final onPrimary = Theme.of(context).colorScheme.onPrimary;

    final Widget button = isLoading
        ? FilledButton(
            onPressed: null,
            child: SizedBox(
              width: Dimensions.x2,
              height: Dimensions.x2,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: onPrimary,
              ),
            ),
          )
        : icon != null
            ? FilledButton.icon(
                onPressed: onPressed,
                icon: Icon(icon),
                label: Text(label),
              )
            : FilledButton(
                onPressed: onPressed,
                child: Text(label),
              );

    if (expand) {
      return SizedBox(
        width: double.infinity,
        child: button,
      );
    }

    return button;
  }
}
