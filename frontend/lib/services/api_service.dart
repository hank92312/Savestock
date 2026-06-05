import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/stock.dart';

class SearchCandidate {
  final String stockId; // 含後綴，如 "2330.TW"、"6147.TWO"
  final String name;

  const SearchCandidate({required this.stockId, required this.name});

  factory SearchCandidate.fromJson(Map<String, dynamic> j) =>
      SearchCandidate(stockId: j['stock_id'] as String, name: j['name'] as String);

  /// 顯示用：去掉後綴的純代號，如 "2330"
  String get code => stockId.replaceAll(RegExp(r'\.(TW|TWO)$'), '');
}

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

  /// 模糊搜尋台股：輸入代號前綴或中文名稱部分字詞，回傳候選清單
  static Future<List<SearchCandidate>> searchStocks(String q) async {
    if (q.trim().isEmpty) return [];
    final uri = Uri.parse('$_base/stocks/search').replace(
      queryParameters: {'q': q.trim(), 'limit': '20'},
    );
    final res = await http.get(uri);
    if (res.statusCode != 200) return [];
    final List data = jsonDecode(utf8.decode(res.bodyBytes)) as List;
    return data
        .map((e) => SearchCandidate.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 即時查詢任意台股（傳入純代號如 "2330"，或含後綴 "2330.TW"、"6147.TWO"）
  static Future<Stock?> lookupStock(String stockId) async {
    // 剝掉後綴交給 server 從快取解析正確的 .TW / .TWO
    final sid = stockId.toUpperCase().replaceAll(RegExp(r'\.(TW|TWO)$'), '');
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
