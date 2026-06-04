import 'dart:math';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class UserService {
  static const _keyUserId = 'user_id';
  static const _keyUuid = 'user_uuid';
  static const String _base = 'http://localhost:8000';

  static Future<int> getOrCreateUserId() async {
    final prefs = await SharedPreferences.getInstance();

    final savedId = prefs.getInt(_keyUserId);
    if (savedId != null) return savedId;

    final uuid = prefs.getString(_keyUuid) ?? _generateUuid();
    await prefs.setString(_keyUuid, uuid);

    final res = await http.post(
      Uri.parse('$_base/users/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'uuid': uuid}),
    );
    if (res.statusCode != 201) throw Exception('建立用戶失敗');
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final userId = data['user_id'] as int;
    await prefs.setInt(_keyUserId, userId);
    return userId;
  }

  static String _generateUuid() {
    final rng = Random.secure();
    String hex(int n) => rng.nextInt(n).toRadixString(16).padLeft(4, '0');
    return '${hex(65536)}${hex(65536)}-${hex(65536)}-4${hex(4096).substring(1)}'
        '-${(8 + rng.nextInt(4)).toRadixString(16)}${hex(4096).substring(1)}'
        '-${hex(65536)}${hex(65536)}${hex(65536)}';
  }
}
