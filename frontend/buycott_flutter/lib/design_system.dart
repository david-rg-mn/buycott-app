import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class BuycottDesignSystem {
  const BuycottDesignSystem._();

  static ThemeData darkTheme() {
    const tokens = BuycottThemeTokens.defaults;
    final textTheme =
        BuycottTypography.buildTextTheme(BuycottColors.textPrimary);

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: BuycottColors.colorScheme,
      scaffoldBackgroundColor: BuycottColors.bgPrimary,
      canvasColor: BuycottColors.bgPrimary,
      textTheme: textTheme,
      shadowColor: BuycottColors.shadowBase,
      extensions: const <ThemeExtension<dynamic>>[tokens],
      chipTheme: ChipThemeData(
        backgroundColor: BuycottColors.bgSurface,
        disabledColor:
            BuycottColors.bgSurface.withValues(alpha: tokens.disabledOpacity),
        selectedColor: BuycottColors.accentDim
            .withValues(alpha: tokens.activeOverlayOpacity),
        side: const BorderSide(color: BuycottColors.border),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMd),
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: Dimensions.x1,
          vertical: Dimensions.x1,
        ),
        labelStyle:
            textTheme.bodySmall?.copyWith(color: BuycottColors.textPrimary),
      ),
      cardTheme: CardThemeData(
        margin: EdgeInsets.zero,
        color: BuycottColors.bgSurface,
        elevation: 1,
        shadowColor: BuycottColors.shadowBase,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMd),
          side: const BorderSide(color: BuycottColors.border),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size.fromHeight(Dimensions.controlHeight),
          ),
          padding: const WidgetStatePropertyAll(
            EdgeInsets.symmetric(horizontal: Dimensions.x2),
          ),
          textStyle: WidgetStatePropertyAll(
            textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
          ),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(tokens.radiusMd),
            ),
          ),
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) {
              return BuycottColors.accentPrimary
                  .withValues(alpha: tokens.disabledOpacity);
            }
            return BuycottColors.accentPrimary;
          }),
          foregroundColor:
              const WidgetStatePropertyAll(BuycottColors.textInverse),
          overlayColor: WidgetStateProperty.resolveWith(
            (states) => _overlayColor(states, tokens),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: BuycottColors.bgSurface,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: Dimensions.x2,
          vertical: Dimensions.x1,
        ),
        hintStyle:
            textTheme.bodyMedium?.copyWith(color: BuycottColors.textSecondary),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMd),
          borderSide: const BorderSide(color: BuycottColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMd),
          borderSide: const BorderSide(color: BuycottColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMd),
          borderSide:
              const BorderSide(color: BuycottColors.accentPrimary, width: 2),
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: BuycottColors.bgSurface,
        modalBackgroundColor: BuycottColors.bgSurface,
        modalBarrierColor: BuycottColors.scrim,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(tokens.radiusLg),
          ),
        ),
        dragHandleColor: BuycottColors.border,
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: BuycottColors.bgSurface,
        foregroundColor: BuycottColors.textPrimary,
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: BuycottColors.bgSurface,
          borderRadius: BorderRadius.circular(tokens.radiusMd),
          border: Border.all(color: BuycottColors.border),
        ),
        textStyle: textTheme.bodySmall,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: BuycottColors.bgSurface,
        contentTextStyle: textTheme.bodyMedium,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(tokens.radiusMd),
          side: const BorderSide(color: BuycottColors.border),
        ),
      ),
      dividerTheme: const DividerThemeData(color: BuycottColors.border),
    );
  }

  static Color? _overlayColor(
      Set<WidgetState> states, BuycottThemeTokens tokens) {
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
  }
}

class BuycottColors {
  const BuycottColors._();

  static const Color bgPrimary = Color(0xFF142633);
  static const Color bgSurface = Color(0xFF1E2F3A);
  static const Color border = Color(0xFF2B3A44);
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFF94A1AD);
  static const Color textInverse = Color(0xFF000000);

  static const Color accentPrimary = Color(0xFF00E4E4);
  static const Color accentHover = Color(0xFF33EDEE);
  static const Color accentDim = Color(0xFF146E6E);

  static const Color signalLow = Color(0xFF00CCFF);
  static const Color signalMid = Color(0xFF00E4E4);
  static const Color signalHigh = Color(0xFF00ECBD);
  static const Color signalPeak = Color(0xFF95FF00);

  static const Color semanticSuccess = Color(0xFF97FF7D);
  static const Color semanticError = Color(0xFFFF3B30);
  static const Color semanticWarning = Color(0xFFFFC107);

  static const Color shadowBase = Color(0x80000000);
  static const Color scrim = Color(0xB3000000);

  static const ColorScheme colorScheme = ColorScheme.dark(
    primary: accentPrimary,
    onPrimary: textInverse,
    secondary: signalHigh,
    onSecondary: textInverse,
    tertiary: signalLow,
    onTertiary: textInverse,
    surface: bgSurface,
    onSurface: textPrimary,
    error: semanticError,
    onError: textPrimary,
    outline: border,
    shadow: shadowBase,
    scrim: scrim,
  );
}

class BuycottTypographyScale {
  const BuycottTypographyScale._();

  static const double caption = 12;
  static const double bodySmall = 14;
  static const double body = 16;
  static const double h3 = 20;
  static const double h2 = 24;
  static const double h1 = 32;
}

class BuycottTypography {
  const BuycottTypography._();

  static final Set<double> allowedSizes = <double>{12, 14, 16, 20, 24, 32};
  static final Set<FontWeight> allowedWeights = <FontWeight>{
    FontWeight.w400,
    FontWeight.w600,
    FontWeight.w700,
  };

  static TextTheme buildTextTheme(Color textColor) {
    final base = GoogleFonts.interTextTheme();
    return base.copyWith(
      displayLarge: _style(
        size: BuycottTypographyScale.h1,
        weight: FontWeight.w600,
        height: 1.15,
        color: textColor,
      ),
      headlineLarge: _style(
        size: BuycottTypographyScale.h2,
        weight: FontWeight.w600,
        height: 1.18,
        color: textColor,
      ),
      headlineMedium: _style(
        size: BuycottTypographyScale.h3,
        weight: FontWeight.w600,
        height: 1.2,
        color: textColor,
      ),
      bodyLarge: _style(
        size: BuycottTypographyScale.body,
        weight: FontWeight.w400,
        height: 1.25,
        color: textColor,
      ),
      bodyMedium: _style(
        size: BuycottTypographyScale.bodySmall,
        weight: FontWeight.w400,
        height: 1.25,
        color: textColor,
      ),
      bodySmall: _style(
        size: BuycottTypographyScale.caption,
        weight: FontWeight.w400,
        height: 1.25,
        color: textColor,
      ),
      labelLarge: _style(
        size: BuycottTypographyScale.body,
        weight: FontWeight.w600,
        height: 1.2,
        color: textColor,
      ),
      labelMedium: _style(
        size: BuycottTypographyScale.bodySmall,
        weight: FontWeight.w600,
        height: 1.2,
        color: textColor,
      ),
      labelSmall: _style(
        size: BuycottTypographyScale.caption,
        weight: FontWeight.w600,
        height: 1.2,
        color: textColor,
      ),
    );
  }

  static TextStyle numeric(TextStyle base,
      {FontWeight weight = FontWeight.w700}) {
    return base.copyWith(
      fontWeight: weight,
      fontFeatures: const <FontFeature>[FontFeature.tabularFigures()],
    );
  }

  static TextStyle _style({
    required double size,
    required FontWeight weight,
    required double height,
    required Color color,
  }) {
    return GoogleFonts.inter(
      fontSize: size,
      fontWeight: weight,
      height: height,
      color: color,
      fontFeatures: const <FontFeature>[FontFeature.tabularFigures()],
    );
  }
}

class Dimensions {
  const Dimensions._();

  static const double x1 = 8;
  static const double x2 = 16;
  static const double x3 = 24;
  static const double x4 = 32;
  static const double x5 = 40;
  static const double x6 = 48;
  static const double x7 = 56;
  static const double x8 = 64;

  static const double controlHeight = 48;

  static const EdgeInsets pagePadding = EdgeInsets.all(x2);
  static const EdgeInsets cardPadding = EdgeInsets.all(x2);
  static const EdgeInsets sheetPadding = EdgeInsets.all(x2);
}

@immutable
class BuycottThemeTokens extends ThemeExtension<BuycottThemeTokens> {
  const BuycottThemeTokens({
    required this.radiusSm,
    required this.radiusMd,
    required this.radiusLg,
    required this.radiusFull,
    required this.hoverOverlayOpacity,
    required this.activeOverlayOpacity,
    required this.disabledOpacity,
    required this.elevationCard,
    required this.elevationSheet,
    required this.elevationDialog,
    required this.signalLow,
    required this.signalMid,
    required this.signalHigh,
    required this.signalPeak,
  });

  static const BuycottThemeTokens defaults = BuycottThemeTokens(
    radiusSm: 4,
    radiusMd: 8,
    radiusLg: 16,
    radiusFull: 999,
    hoverOverlayOpacity: 0.08,
    activeOverlayOpacity: 0.16,
    disabledOpacity: 0.5,
    elevationCard: <BoxShadow>[
      BoxShadow(
        color: Color(0x80000000),
        offset: Offset(0, 2),
        blurRadius: 4,
      ),
    ],
    elevationSheet: <BoxShadow>[
      BoxShadow(
        color: Color(0x99000000),
        offset: Offset(0, 4),
        blurRadius: 8,
      ),
    ],
    elevationDialog: <BoxShadow>[
      BoxShadow(
        color: Color(0xB3000000),
        offset: Offset(0, 8),
        blurRadius: 16,
      ),
    ],
    signalLow: BuycottColors.signalLow,
    signalMid: BuycottColors.signalMid,
    signalHigh: BuycottColors.signalHigh,
    signalPeak: BuycottColors.signalPeak,
  );

  final double radiusSm;
  final double radiusMd;
  final double radiusLg;
  final double radiusFull;
  final double hoverOverlayOpacity;
  final double activeOverlayOpacity;
  final double disabledOpacity;
  final List<BoxShadow> elevationCard;
  final List<BoxShadow> elevationSheet;
  final List<BoxShadow> elevationDialog;
  final Color signalLow;
  final Color signalMid;
  final Color signalHigh;
  final Color signalPeak;

  Color colorForConfidence(int confidenceScore) {
    final clamped = confidenceScore.clamp(0, 100);
    if (clamped >= 95) {
      return signalPeak;
    }
    if (clamped >= 85) {
      return signalHigh;
    }
    if (clamped >= 70) {
      return signalMid;
    }
    return signalLow;
  }

  @override
  BuycottThemeTokens copyWith({
    double? radiusSm,
    double? radiusMd,
    double? radiusLg,
    double? radiusFull,
    double? hoverOverlayOpacity,
    double? activeOverlayOpacity,
    double? disabledOpacity,
    List<BoxShadow>? elevationCard,
    List<BoxShadow>? elevationSheet,
    List<BoxShadow>? elevationDialog,
    Color? signalLow,
    Color? signalMid,
    Color? signalHigh,
    Color? signalPeak,
  }) {
    return BuycottThemeTokens(
      radiusSm: radiusSm ?? this.radiusSm,
      radiusMd: radiusMd ?? this.radiusMd,
      radiusLg: radiusLg ?? this.radiusLg,
      radiusFull: radiusFull ?? this.radiusFull,
      hoverOverlayOpacity: hoverOverlayOpacity ?? this.hoverOverlayOpacity,
      activeOverlayOpacity: activeOverlayOpacity ?? this.activeOverlayOpacity,
      disabledOpacity: disabledOpacity ?? this.disabledOpacity,
      elevationCard: elevationCard ?? this.elevationCard,
      elevationSheet: elevationSheet ?? this.elevationSheet,
      elevationDialog: elevationDialog ?? this.elevationDialog,
      signalLow: signalLow ?? this.signalLow,
      signalMid: signalMid ?? this.signalMid,
      signalHigh: signalHigh ?? this.signalHigh,
      signalPeak: signalPeak ?? this.signalPeak,
    );
  }

  @override
  BuycottThemeTokens lerp(ThemeExtension<BuycottThemeTokens>? other, double t) {
    if (other is! BuycottThemeTokens) {
      return this;
    }

    return BuycottThemeTokens(
      radiusSm: lerpDouble(radiusSm, other.radiusSm, t) ?? radiusSm,
      radiusMd: lerpDouble(radiusMd, other.radiusMd, t) ?? radiusMd,
      radiusLg: lerpDouble(radiusLg, other.radiusLg, t) ?? radiusLg,
      radiusFull: lerpDouble(radiusFull, other.radiusFull, t) ?? radiusFull,
      hoverOverlayOpacity:
          lerpDouble(hoverOverlayOpacity, other.hoverOverlayOpacity, t) ??
              hoverOverlayOpacity,
      activeOverlayOpacity:
          lerpDouble(activeOverlayOpacity, other.activeOverlayOpacity, t) ??
              activeOverlayOpacity,
      disabledOpacity: lerpDouble(disabledOpacity, other.disabledOpacity, t) ??
          disabledOpacity,
      elevationCard: t < 0.5 ? elevationCard : other.elevationCard,
      elevationSheet: t < 0.5 ? elevationSheet : other.elevationSheet,
      elevationDialog: t < 0.5 ? elevationDialog : other.elevationDialog,
      signalLow: Color.lerp(signalLow, other.signalLow, t) ?? signalLow,
      signalMid: Color.lerp(signalMid, other.signalMid, t) ?? signalMid,
      signalHigh: Color.lerp(signalHigh, other.signalHigh, t) ?? signalHigh,
      signalPeak: Color.lerp(signalPeak, other.signalPeak, t) ?? signalPeak,
    );
  }
}

extension BuycottThemeContext on BuildContext {
  BuycottThemeTokens get buycottTokens {
    return Theme.of(this).extension<BuycottThemeTokens>() ??
        BuycottThemeTokens.defaults;
  }
}
