import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/stock.dart';

class PricePoint {
  final DateTime date;
  final double close;
  final bool alertFlag;

  const PricePoint({required this.date, required this.close, required this.alertFlag});

  factory PricePoint.fromJson(Map<String, dynamic> j) => PricePoint(
        date: DateTime.parse(j['date'] as String),
        close: (j['close_price'] as num).toDouble(),
        alertFlag: j['alert_flag'] as bool? ?? false,
      );
}

class DividendPoint {
  final DateTime date;
  final double amount;

  const DividendPoint({required this.date, required this.amount});

  factory DividendPoint.fromJson(Map<String, dynamic> j) => DividendPoint(
        date: DateTime.parse(j['date'] as String),
        amount: (j['amount'] as num).toDouble(),
      );
}

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

  /// 即時從網路更新所有預設股（較慢，供「更新」按鈕/下拉刷新使用）
  static Future<List<Stock>> refreshDefaultStocks() async {
    final res = await http.post(Uri.parse('$_base/stocks/refresh'));
    if (res.statusCode != 200) throw Exception('更新失敗 (${res.statusCode})');
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
  /// 查無資料時丟出含 API detail 訊息的 Exception，供 UI 直接顯示。
  static Future<Stock> lookupStock(String stockId) async {
    // 剝掉後綴交給 server 從快取解析正確的 .TW / .TWO
    final sid = stockId.toUpperCase().replaceAll(RegExp(r'\.(TW|TWO)$'), '');
    final res = await http.get(Uri.parse('$_base/stocks/lookup/$sid'));
    if (res.statusCode != 200) {
      final body = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
      final detail = body['detail'] as String? ?? '查詢失敗，請確認代號是否正確';
      throw Exception(detail);
    }
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
    // 達自選股上限：改為友善說明並引導升級，取代後端原始錯誤字串
    if (res.statusCode == 403) {
      return '${body['detail'] ?? '已達自選股上限'}\n升級方案即可追蹤更多標的。';
    }
    return body['detail'] as String? ?? '加入失敗';
  }

  static Future<void> removeFromWatchlist(int userId, String stockId) async {
    final res = await http.delete(
      Uri.parse('$_base/users/$userId/watchlist/$stockId'),
    );
    if (res.statusCode != 200) throw Exception('移除失敗');
  }

  /// 取得個股近 N 日收盤價歷史（預設 30 日）
  static Future<List<PricePoint>> fetchPrices(String stockId, {int days = 30}) async {
    final res = await http.get(
      Uri.parse('$_base/stocks/$stockId/prices?days=$days'),
    );
    if (res.statusCode != 200) throw Exception('載入失敗 (${res.statusCode})');
    final List data = jsonDecode(utf8.decode(res.bodyBytes)) as List;
    return data
        .map((e) => PricePoint.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// 取得個股近 N 個月現金股利發放紀錄（供股利折線圖，預設 24 個月）
  static Future<List<DividendPoint>> fetchDividends(String stockId,
      {int months = 24}) async {
    final res = await http.get(
      Uri.parse('$_base/stocks/$stockId/dividends?months=$months'),
    );
    if (res.statusCode != 200) throw Exception('載入失敗 (${res.statusCode})');
    final List data = jsonDecode(utf8.decode(res.bodyBytes)) as List;
    return data
        .map((e) => DividendPoint.fromJson(e as Map<String, dynamic>))
        .toList();
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
