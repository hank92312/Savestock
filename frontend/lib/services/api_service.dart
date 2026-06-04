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
}
