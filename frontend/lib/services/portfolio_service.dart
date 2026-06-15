import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/portfolio.dart';

/// 持股清單的裝置端儲存（沿用專案「資料存使用者端」原則，與 UUID 同機制）。
class PortfolioService {
  static const _key = 'portfolio_holdings';

  static Future<List<Holding>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    try {
      final List data = jsonDecode(raw) as List;
      return data
          .map((e) => Holding.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return [];
    }
  }

  static Future<void> save(List<Holding> holdings) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _key,
      jsonEncode(holdings.map((h) => h.toJson()).toList()),
    );
  }
}
