import 'package:flutter/material.dart';
import '../models/stock.dart';
import '../services/api_service.dart';
import '../services/user_service.dart';
import '../theme/app_theme.dart';
import '../widgets/stock_card.dart';
import 'add_stock_screen.dart';

class MyStocksScreen extends StatefulWidget {
  const MyStocksScreen({super.key});

  @override
  State<MyStocksScreen> createState() => _MyStocksScreenState();
}

class _MyStocksScreenState extends State<MyStocksScreen> {
  int? _userId;
  List<Stock> _stocks = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final id = await UserService.getOrCreateUserId();
      // 直接從網路抓最新資料並更新 DB，確保顯示即時數據
      final stocks = await ApiService.refreshAndFetchWatchlist(id);
      setState(() {
        _userId = id;
        _stocks = stocks;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = '載入失敗，請確認網路連線';
        _loading = false;
      });
    }
  }

  Future<void> _remove(Stock stock) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('移除自選股'),
        content: Text('確定要從追蹤清單移除「${stock.name}」嗎？'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('取消')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              style: FilledButton.styleFrom(backgroundColor: AppTheme.alertRed),
              child: const Text('移除')),
        ],
      ),
    );
    if (confirm != true || _userId == null) return;

    try {
      await ApiService.removeFromWatchlist(_userId!, stock.stockId);
      setState(() => _stocks.removeWhere((s) => s.stockId == stock.stockId));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('移除失敗，請稍後再試')),
      );
    }
  }

  Future<void> _goToAdd() async {
    final added = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const AddStockScreen()),
    );
    if (added == true) _init(); // 有加入 → 重新載入清單
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isTablet = width >= 600;

    return Scaffold(
      appBar: AppBar(
        title: const Text('我的股票'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: '重新整理',
            onPressed: _init,
          ),
          IconButton(
            icon: const Icon(Icons.add_rounded),
            tooltip: '加入自選股',
            onPressed: _userId == null ? null : _goToAdd,
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _ErrorView(message: _error!, onRetry: _init)
              : _stocks.isEmpty
                  ? _EmptyView(onAdd: _userId == null ? null : _goToAdd)
                  : _StockList(
                      stocks: _stocks,
                      isTablet: isTablet,
                      onRemove: _remove,
                    ),
    );
  }
}

// ── 股票列表（滑動可刪除）──────────────────────────────────

class _StockList extends StatelessWidget {
  final List<Stock> stocks;
  final bool isTablet;
  final Future<void> Function(Stock) onRemove;

  const _StockList(
      {required this.stocks,
      required this.isTablet,
      required this.onRemove});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: stocks.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (_, i) {
        final stock = stocks[i];
        return Dismissible(
          key: ValueKey(stock.stockId),
          direction: DismissDirection.endToStart,
          background: Container(
            alignment: Alignment.centerRight,
            padding: const EdgeInsets.only(right: 20),
            decoration: BoxDecoration(
              color: AppTheme.alertRed.withOpacity(0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.delete_outline_rounded, color: AppTheme.alertRed),
                SizedBox(height: 4),
                Text('移除',
                    style: TextStyle(
                        color: AppTheme.alertRed,
                        fontSize: 12,
                        fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          confirmDismiss: (_) async {
            await onRemove(stock);
            return false; // 讓 _remove() 自己控制 setState，不用 Dismissible 自動移除
          },
          // 左滑刪除為觸控手勢，桌機/web 滑鼠不易觸發，
          // 故另加一顆永遠可見的刪除按鈕，確保各平台皆可移除
          child: Row(
            children: [
              Expanded(child: StockCard(stock: stock, isTablet: isTablet)),
              const SizedBox(width: 4),
              IconButton(
                icon: const Icon(Icons.delete_outline_rounded,
                    color: AppTheme.alertRed),
                tooltip: '移除',
                onPressed: () => onRemove(stock),
              ),
            ],
          ),
        );
      },
    );
  }
}

// ── 空清單引導 ─────────────────────────────────────────────

class _EmptyView extends StatelessWidget {
  final VoidCallback? onAdd;
  const _EmptyView({this.onAdd});

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
                  color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 8),
            const Text(
              '把感興趣的股票加入追蹤清單\n免費版最多可加入 3 檔',
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: 14, color: AppTheme.textSecondary, height: 1.6),
            ),
            const SizedBox(height: 32),
            FilledButton.icon(
              onPressed: onAdd,
              icon: const Icon(Icons.add_rounded),
              label: const Text('加入第一檔股票'),
            ),
          ],
        ),
      ),
    );
  }
}

// ── 錯誤畫面 ───────────────────────────────────────────────

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_rounded,
                  size: 56, color: AppTheme.textSecondary),
              const SizedBox(height: 16),
              Text(message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: AppTheme.textSecondary, fontSize: 15)),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('重新載入'),
              ),
            ],
          ),
        ),
      );
}
