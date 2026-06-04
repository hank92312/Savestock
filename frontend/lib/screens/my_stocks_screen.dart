import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/user_service.dart';

class MyStocksScreen extends StatefulWidget {
  const MyStocksScreen({super.key});

  @override
  State<MyStocksScreen> createState() => _MyStocksScreenState();
}

class _MyStocksScreenState extends State<MyStocksScreen> {
  int? _userId;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initUser();
  }

  Future<void> _initUser() async {
    try {
      final id = await UserService.getOrCreateUserId();
      setState(() {
        _userId = id;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = '初始化失敗，請確認網路連線';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('我的股票'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_rounded),
            tooltip: '加入自選股',
            onPressed: _userId == null ? null : () {
              // 加入股票頁（下一階段實作）
            },
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _ErrorView(message: _error!)
              : _EmptyWatchlist(userId: _userId!),
    );
  }
}

class _EmptyWatchlist extends StatelessWidget {
  final int userId;
  const _EmptyWatchlist({required this.userId});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.bookmark_add_outlined,
                size: 64, color: Colors.grey.shade300),
            const SizedBox(height: 20),
            const Text(
              '還沒有自選股票',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '點右上角「＋」，把你感興趣的股票\n加入個人追蹤清單',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: AppTheme.textSecondary,
                height: 1.6,
              ),
            ),
            const SizedBox(height: 32),
            FilledButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.add_rounded),
              label: const Text('加入第一檔股票'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  const _ErrorView({required this.message});

  @override
  Widget build(BuildContext context) => Center(
        child: Text(message,
            style: const TextStyle(color: AppTheme.textSecondary)),
      );
}
