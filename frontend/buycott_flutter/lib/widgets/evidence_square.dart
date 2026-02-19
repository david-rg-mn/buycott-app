import 'package:flutter/material.dart';

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
    return Container(
      width: 64,
      height: 64,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0F766E), Color(0xFF0E7490), Color(0xFF0284C7)],
        ),
        border: Border.all(
          color: highlight ? const Color(0xFFF59E0B) : Colors.white,
          width: 2,
        ),
        boxShadow: [
          BoxShadow(
            color: highlight ? const Color(0x66F59E0B) : const Color(0x33000000),
            blurRadius: 10,
            spreadRadius: highlight ? 2 : 0,
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${minutes}m',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w800,
            ),
          ),
          Text(
            '$evidence',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
