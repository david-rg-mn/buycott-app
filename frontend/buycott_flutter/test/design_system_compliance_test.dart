import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  final libFiles = Directory('lib')
      .listSync(recursive: true)
      .whereType<File>()
      .where((file) => file.path.endsWith('.dart'))
      .toList()
    ..sort((a, b) => a.path.compareTo(b.path));

  String relativePath(File file) {
    return file.path.replaceFirst('${Directory.current.path}/', '');
  }

  int lineNumberForOffset(String content, int offset) {
    return '\n'.allMatches(content.substring(0, offset)).length + 1;
  }

  group('design system compliance', () {
    test('no hard-coded hex or raw colors outside design_system.dart', () {
      final violations = <String>[];
      final hexPattern = RegExp(r'#[0-9A-Fa-f]{3,8}');
      final colorCtorPattern = RegExp(r'\bColor\s*\(');
      final colorsClassPattern = RegExp(r'\bColors\.[A-Za-z0-9_]+');

      for (final file in libFiles) {
        final path = relativePath(file);
        final content = file.readAsStringSync();

        if (path.endsWith('design_system.dart')) {
          continue;
        }

        for (final match in hexPattern.allMatches(content)) {
          violations.add(
              '$path:${lineNumberForOffset(content, match.start)} contains # hex');
        }

        for (final match in colorCtorPattern.allMatches(content)) {
          violations.add(
            '$path:${lineNumberForOffset(content, match.start)} contains raw Color(...)',
          );
        }

        for (final match in colorsClassPattern.allMatches(content)) {
          violations.add(
            '$path:${lineNumberForOffset(content, match.start)} contains raw Colors.*',
          );
        }
      }

      expect(
        violations,
        isEmpty,
        reason: violations.isEmpty ? null : violations.join('\n'),
      );
    });

    test('font sizes and font weights follow approved scale', () {
      final violations = <String>[];
      final allowedSizes = <double>{12, 14, 16, 20, 24, 32};
      final allowedWeights = <String>{
        'FontWeight.w400',
        'FontWeight.w600',
        'FontWeight.w700',
      };

      final fontSizePattern = RegExp(r'fontSize\s*:\s*([0-9]+(?:\.[0-9]+)?)');
      final fontWeightPattern =
          RegExp(r'fontWeight\s*:\s*(FontWeight\.[A-Za-z0-9_]+)');

      for (final file in libFiles) {
        final path = relativePath(file);
        final content = file.readAsStringSync();

        for (final match in fontSizePattern.allMatches(content)) {
          final rawValue = match.group(1);
          if (rawValue == null) {
            continue;
          }
          final fontSize = double.tryParse(rawValue);
          if (fontSize == null || !allowedSizes.contains(fontSize)) {
            violations.add(
              '$path:${lineNumberForOffset(content, match.start)} uses disallowed fontSize $rawValue',
            );
          }
        }

        for (final match in fontWeightPattern.allMatches(content)) {
          final rawWeight = match.group(1);
          if (rawWeight == null) {
            continue;
          }
          if (!allowedWeights.contains(rawWeight)) {
            violations.add(
              '$path:${lineNumberForOffset(content, match.start)} uses disallowed fontWeight $rawWeight',
            );
          }
        }
      }

      expect(
        violations,
        isEmpty,
        reason: violations.isEmpty ? null : violations.join('\n'),
      );
    });

    test('all EdgeInsets literal values follow the 8dp grid', () {
      final violations = <String>[];
      final edgeInsetsPattern = RegExp(r'EdgeInsets\.[A-Za-z]+\(([^\)]*)\)');
      final numberPattern = RegExp(r'(?<![A-Za-z0-9_\.])(\d+(?:\.\d+)?)');

      for (final file in libFiles) {
        final path = relativePath(file);
        final content = file.readAsStringSync();

        for (final edgeInsetsMatch in edgeInsetsPattern.allMatches(content)) {
          final args = edgeInsetsMatch.group(1) ?? '';
          for (final numberMatch in numberPattern.allMatches(args)) {
            final rawValue = numberMatch.group(1);
            if (rawValue == null) {
              continue;
            }
            final value = double.tryParse(rawValue);
            if (value == null || value == 0) {
              continue;
            }
            if (value % 8 != 0) {
              violations.add(
                '$path:${lineNumberForOffset(content, edgeInsetsMatch.start)} has non-8dp EdgeInsets value $rawValue',
              );
            }
          }
        }
      }

      expect(
        violations,
        isEmpty,
        reason: violations.isEmpty ? null : violations.join('\n'),
      );
    });

    test('raw ElevatedButton.styleFrom is blocked', () {
      final violations = <String>[];
      final styleFromPattern = RegExp(r'ElevatedButton\.styleFrom');

      for (final file in libFiles) {
        final path = relativePath(file);
        final content = file.readAsStringSync();

        for (final match in styleFromPattern.allMatches(content)) {
          violations.add(
            '$path:${lineNumberForOffset(content, match.start)} uses ElevatedButton.styleFrom',
          );
        }
      }

      expect(
        violations,
        isEmpty,
        reason: violations.isEmpty ? null : violations.join('\n'),
      );
    });
  });
}
