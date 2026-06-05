import 'package:flutter/material.dart';
import '../models/stock.dart';
import '../services/api_service.dart';
import '../services/user_service.dart';
import '../theme/app_theme.dart';
import '../widgets/stock_card.dart';

class AddStockScreen extends StatefulWidget {
  const AddStockScreen({super.key});

  @override
  State<AddStockScreen> createState() => _AddStockScreenState();
}

class _AddStockScreenState extends State<AddStockScreen> {
  final _controller = TextEditingController();
  Stock? _result;
  bool _searching = false;
  bool _adding = false;
  String? _error;
  bool _added = false; // 是否已加入此股票

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    final q = _controller.text.trim();
    if (q.isEmpty) return;

    setState(() {
      _searching = true;
      _result = null;
      _error = null;
      _added = false;
    });

    try {
      final stock = await ApiService.lookupStock(q);
      setState(() {
        _result = stock;
        _searching = false;
        if (stock == null) _error = '查無「$q」，請確認代號是否正確（例如：0050、2330）';
      });
    } catch (_) {
      setState(() {
        _error = '查詢失敗，請確認網路連線後再試';
        _searching = false;
      });
    }
  }

  Future<void> _add() async {
    if (_result == null) return;
    setState(() => _adding = true);

    try {
      final userId = await UserService.getOrCreateUserId();
      final error = await ApiService.addToWatchlist(userId, _result!.stockId);

      if (!mounted) return;
      if (error != null) {
        setState(() {
          _error = error;
          _adding = false;
        });
        return;
      }
      setState(() {
        _added = true;
        _adding = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = '加入失敗，請確認網路連線後再試';
        _adding = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isTablet = width >= 600;

    return Scaffold(
      appBar: AppBar(title: const Text('查詢股票')),
      body: Column(
        children: [
          _SearchBar(
            controller: _controller,
            onSearch: _search,
            isSearching: _searching,
          ),
          const Divider(height: 1, color: AppTheme.divider),
          Expanded(
            child: _searching
                ? const _LoadingView()
                : _result != null
                    ? _ResultView(
                        stock: _result!,
                        isTablet: isTablet,
                        added: _added,
                        adding: _adding,
                        error: _error,
                        onAdd: _added ? null : _add,
                      )
                    : _EmptyView(error: _error),
          ),
        ],
      ),
    );
  }
}

// ── 搜尋列 ──────────────────────────────────────────────────

class _SearchBar extends StatelessWidget {
  final TextEditingController controller;
  final VoidCallback onSearch;
  final bool isSearching;

  const _SearchBar({
    required this.controller,
    required this.onSearch,
    required this.isSearching,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              autofocus: true,
              keyboardType: TextInputType.text,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => onSearch(),
              decoration: InputDecoration(
                hintText: '輸入股票代號（如 0050、2330、2412）',
                prefixIcon: const Icon(Icons.search_rounded),
                filled: true,
                fillColor: AppTheme.surface,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: AppTheme.divider),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: AppTheme.divider),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide:
                      const BorderSide(color: AppTheme.primary, width: 2),
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          const SizedBox(width: 12),
          FilledButton(
            onPressed: isSearching ? null : onSearch,
            style: FilledButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
            child: isSearching
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  )
                : const Text('查詢'),
          ),
        ],
      ),
    );
  }
}

// ── 查詢結果 ─────────────────────────────────────────────────

class _ResultView extends StatelessWidget {
  final Stock stock;
  final bool isTablet;
  final bool added;
  final bool adding;
  final String? error;
  final VoidCallback? onAdd;

  const _ResultView({
    required this.stock,
    required this.isTablet,
    required this.added,
    required this.adding,
    this.error,
    this.onAdd,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '查詢結果',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppTheme.textSecondary,
            ),
          ),
          const SizedBox(height: 12),
          // 與首頁相同的股票卡片
          StockCard(stock: stock, isTablet: isTablet),
          const SizedBox(height: 16),
          if (error != null)
            _Banner(
              message: error!,
              isError: true,
            ),
          if (added)
            const _Banner(
              message: '已加入我的股票，下次開啟時將自動更新最新資料',
              isError: false,
            ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: added
                ? OutlinedButton.icon(
                    onPressed: () => Navigator.pop(context, true),
                    icon: const Icon(Icons.check_rounded),
                    label: const Text('返回我的股票'),
                  )
                : FilledButton.icon(
                    onPressed: adding ? null : onAdd,
                    icon: adding
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.bookmark_add_rounded),
                    label: Text(adding ? '加入中…' : '加入我的股票'),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

// ── 初始引導畫面 ─────────────────────────────────────────────

class _EmptyView extends StatelessWidget {
  final String? error;
  const _EmptyView({this.error});

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.search_off_rounded,
                  size: 56, color: AppTheme.textSecondary),
              const SizedBox(height: 16),
              Text(
                error!,
                textAlign: TextAlign.center,
                style: const TextStyle(
                    color: AppTheme.textSecondary, fontSize: 15),
              ),
            ],
          ),
        ),
      );
    }

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.manage_search_rounded,
                size: 64, color: Colors.grey.shade300),
            const SizedBox(height: 20),
            const Text(
              '輸入股票代號查詢',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 10),
            const Text(
              '輸入股票代號即可查詢任意台股\n\n例如：\n0050 → 元大台灣50\n2330 → 台積電\n2412 → 中華電信\n\n系統會即時從網路取得最新股價與股利，計算估算殖利率後顯示',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: AppTheme.textSecondary,
                height: 1.7,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── 載入中 ───────────────────────────────────────────────────

class _LoadingView extends StatelessWidget {
  const _LoadingView();

  @override
  Widget build(BuildContext context) => const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('從網路查詢股票資料中…',
                style: TextStyle(color: AppTheme.textSecondary)),
          ],
        ),
      );
}

// ── 訊息橫幅 ─────────────────────────────────────────────────

class _Banner extends StatelessWidget {
  final String message;
  final bool isError;
  const _Banner({required this.message, required this.isError});

  @override
  Widget build(BuildContext context) {
    final color = isError ? AppTheme.alertRed : AppTheme.gainGreen;
    final icon = isError ? Icons.info_outline : Icons.check_circle_outline;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                  color: color, fontSize: 13, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
