import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/stock.dart';

class ApiService {
  // 開發時指向本機；打包前改為正式主機 URL
  static const String _base = 'http://localhost:8000';

  static Future<List<Stock>> fetchDefaultStocks() async {
    final res = await http.get(Uri.parse('$_base/stocks/'));
    if (res.statusCode != 200) throw Exception('載入失敗 (${res.statusCode})');
    final List data = jsonDecode(utf8.decode(res.bodyBytes)) as List;
    return data.map((e) => Stock.fromJson(e as Map<String, dynamic>)).toList();
  }

  static Future<Stock?> fetchStock(String stockId) async {
    final res = await http.get(Uri.parse('$_base/stocks/$stockId'));
    if (res.statusCode == 404) return null;
    if (res.statusCode != 200) throw Exception('載入失敗 (${res.statusCode})');
    return Stock.fromJson(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  /// 即時查詢任意台股（代號不含或含 .TW 皆可）
  static Future<Stock?> lookupStock(String stockId) async {
    final sid = stockId.toUpperCase().replaceAll('.TW', '');
    final res = await http.get(Uri.parse('$_base/stocks/lookup/$sid'));
    if (res.statusCode == 404) return null;
    if (res.statusCode != 200) throw Exception('查詢失敗 (${res.statusCode})');
    return Stock.fromJson(jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>);
  }

  static Future<List<Stock>> fetchWatchlist(int userId) async {
    final res = await http.get(Uri.parse('$_base/users/$userId/watchlist'));
    if (res.statusCode != 200) throw Exception('載入失敗 (${res.statusCode})');
    final List data = jsonDecode(utf8.decode(res.bodyBytes)) as List;
    return data.map((e) => Stock.fromJson(e as Map<String, dynamic>)).toList();
  }

  static Future<String?> addToWatchlist(int userId, String stockId) async {
    final res = await http.post(
      Uri.parse('$_base/users/$userId/watchlist'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'stock_id': stockId}),
    );
    if (res.statusCode == 201) return null;
    final body = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    return body['detail'] as String? ?? '加入失敗';
  }

  static Future<void> removeFromWatchlist(int userId, String stockId) async {
    final res = await http.delete(
      Uri.parse('$_base/users/$userId/watchlist/$stockId'),
    );
    if (res.statusCode != 200) throw Exception('移除失敗');
  }

  /// 即時從網路更新用戶自選股資料，回傳最新清單
  static Future<List<Stock>> refreshAndFetchWatchlist(int userId) async {
    final res = await http.post(
      Uri.parse('$_base/users/$userId/watchlist/refresh'),
    );
    if (res.statusCode != 200) throw Exception('更新失敗 (${res.statusCode})');
    final body = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    final List stocks = body['stocks'] as List;
    return stocks.map((e) => Stock.fromJson(e as Map<String, dynamic>)).toList();
  }
}
