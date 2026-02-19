import 'package:flutter/material.dart';

class GradientSquarePin extends StatelessWidget {
  const GradientSquarePin({
    super.key,
    required this.minutesAway,
    required this.evidenceStrength,
    this.highlighted = false,
  });

  final int minutesAway;
  final int evidenceStrength;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF0BB2C2), Color(0xFF2757ED), Color(0xFFFF8A2A)],
            ),
            border: Border.all(
              color: highlighted ? const Color(0xFFFFD46B) : Colors.white,
              width: highlighted ? 2.5 : 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: highlighted
                    ? const Color(0x66FFD46B)
                    : const Color(0x332757ED),
                blurRadius: highlighted ? 18 : 10,
                spreadRadius: highlighted ? 4 : 2,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '${minutesAway}m',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  fontSize: 14,
                  height: 0.95,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                '$evidenceStrength',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  height: 0.95,
                ),
              ),
            ],
          ),
        ),
        const Icon(Icons.location_on, color: Color(0xFF2757ED), size: 18),
      ],
    );
  }
}
