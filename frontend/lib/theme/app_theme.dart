import 'package:flutter/material.dart';

class AppTheme {
  static const Color primary = Color(0xFF1A73E8);
  static const Color alertRed = Color(0xFFE53935);
  static const Color gainGreen = Color(0xFF2E7D32);
  static const Color surface = Color(0xFFF3F5F9);
  static const Color cardBg = Colors.white;
  static const Color textPrimary = Color(0xFF1C1C1E);
  static const Color textSecondary = Color(0xFF6C757D);
  static const Color divider = Color(0xFFE9ECEF);

  /// 卡片統一圓角
  static const double cardRadius = 16;

  /// 卡片柔和陰影（取代生硬邊框，所有自繪卡片容器共用）
  static const List<BoxShadow> cardShadow = [
    BoxShadow(
      color: Color(0x14202C44), // ~8% 深藍灰
      blurRadius: 14,
      offset: Offset(0, 4),
    ),
  ];

  /// 自繪卡片容器的統一 decoration
  static BoxDecoration cardDecoration({double radius = cardRadius}) =>
      BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(radius),
        boxShadow: cardShadow,
      );

  static ThemeData get theme => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: primary,
          surface: surface,
        ),
        scaffoldBackgroundColor: surface,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: textPrimary,
          elevation: 0,
          scrolledUnderElevation: 1,
          centerTitle: false,
          titleTextStyle: TextStyle(
            color: textPrimary,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
        cardTheme: CardThemeData(
          color: cardBg,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(cardRadius),
          ),
          margin: EdgeInsets.zero,
        ),
      );
}
