import 'package:shared_preferences/shared_preferences.dart';

/// 清單型 API 回應的裝置端快取（原始 JSON 字串），
/// 供首頁／我的股票做 stale-while-revalidate：開啟時先顯示快取，背景再更新。
class ListCacheService {
  static const defaultStocksKey = 'cache_default_stocks';

  static String watchlistKey(int userId) => 'cache_watchlist_$userId';

  static Future<String?> loadRaw(String key) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(key);
  }

  static Future<void> saveRaw(String key, String json) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, json);
  }
}
