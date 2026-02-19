import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color fog = Color(0xFFF5F3EA);
  static const Color ink = Color(0xFF1E2430);
  static const Color civicBlue = Color(0xFF1162F3);
  static const Color civicMint = Color(0xFF00BFA6);
  static const Color civicOrange = Color(0xFFFF8A2A);

  static ThemeData build() {
    final base = ThemeData.light(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: fog,
      colorScheme: base.colorScheme.copyWith(
        primary: civicBlue,
        secondary: civicMint,
        surface: Colors.white,
      ),
      textTheme: GoogleFonts.spaceGroteskTextTheme(base.textTheme).copyWith(
        bodySmall: GoogleFonts.ibmPlexMono(textStyle: base.textTheme.bodySmall),
      ),
    );
  }
}
