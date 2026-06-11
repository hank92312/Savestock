import 'package:flutter/material.dart';
import '../models/stock.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/stock_card.dart';
import 'onboarding_screen.dart';
import 'add_stock_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Stock> _stocks = [];
  bool _loading = true;
  String? _error;
  String _selectedSector = '全部';

  @override
  void initState() {
    super.initState();
    _loadStocks();
  }

  /// [live] = true 時即時從 yfinance 抓最新價格（較慢，按鈕/下拉用）；
  /// false 為讀 DB 快照（開啟時快速載入）。
  /// [showSpinner] = false 時不切換整頁載入畫面（給下拉刷新用，避免清單閃爍）。
  Future<void> _loadStocks({bool live = false, bool showSpinner = true}) async {
    if (showSpinner) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final stocks = live
          ? await ApiService.refreshDefaultStocks()
          : await ApiService.fetchDefaultStocks();
      setState(() {
        _stocks = stocks;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      setState(() {
        _error = live ? '即時更新失敗，請稍後再試' : '無法載入資料，請確認網路連線';
        _loading = false;
      });
    }
  }

  /// 點警示徽章 → 在同頁以底部彈窗列出目前所有警示股票
  void _showAlerts() {
    final alerts = _stocks.where((s) => s.alertFlag).toList();
    if (alerts.isEmpty) return;
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _AlertSheet(stocks: alerts),
    );
  }

  List<String> get _sectors {
    final seen = <String>{'全部'};
    final result = ['全部'];
    for (final s in _stocks) {
      if (seen.add(s.sectorLabel)) result.add(s.sectorLabel);
    }
    return result;
  }

  List<Stock> get _filtered => _selectedSector == '全部'
      ? _stocks
      : _stocks.where((s) => s.sectorLabel == _selectedSector).toList();

  int get _alertCount => _stocks.where((s) => s.alertFlag).length;

  /// 所有股票中最新的資料日期（格式 YYYY/MM/DD），供首頁顯示數據時間
  String? get _dataDate {
    final dates = _stocks.map((s) => s.lastDate).whereType<String>().toList();
    if (dates.isEmpty) return null;
    dates.sort();
    return dates.last.replaceAll('-', '/');
  }

  @override
  Widget build(BuildContext context) {
    // 依螢幕寬度決定是否為平板佈局
    final width = MediaQuery.of(context).size.width;
    final isTablet = width >= 600;
    final isLandscapeTablet = width >= 900;

    return Scaffold(
      appBar: AppBar(
        title: const Text('存股追蹤'),
        actions: [
          if (_alertCount > 0)
            Padding(
              padding: const EdgeInsets.only(right: 4),
              child: _AlertChip(count: _alertCount, onTap: _showAlerts),
            ),
          IconButton(
            icon: const Icon(Icons.search_rounded),
            tooltip: '搜尋股票',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AddStockScreen()),
            ),
          ),
          // 用「圖示+文字」按鈕，手機無 hover tooltip 也看得懂功能
          TextButton.icon(
            onPressed: () => _loadStocks(live: true),
            icon: const Icon(Icons.refresh_rounded, size: 20),
            label: const Text('更新'),
            style: TextButton.styleFrom(
              foregroundColor: AppTheme.primary,
              padding: const EdgeInsets.symmetric(horizontal: 8),
            ),
          ),
          TextButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const OnboardingScreen(),
                fullscreenDialog: true,
              ),
            ),
            icon: const Icon(Icons.help_outline_rounded, size: 20),
            label: const Text('使用教學'),
            style: TextButton.styleFrom(
              foregroundColor: AppTheme.textSecondary,
              padding: const EdgeInsets.symmetric(horizontal: 8),
            ),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: _loading
          ? const _LoadingView()
          : _error != null
              ? _ErrorView(message: _error!, onRetry: _loadStocks)
              : _StocksView(
                  stocks: _filtered,
                  sectors: _sectors,
                  selectedSector: _selectedSector,
                  onSectorChanged: (s) =>
                      setState(() => _selectedSector = s),
                  onRefresh: () => _loadStocks(live: true, showSpinner: false),
                  isTablet: isTablet,
                  isLandscapeTablet: isLandscapeTablet,
                  dataDate: _dataDate,
                ),
    );
  }
}

// ── 主要內容區 ─────────────────────────────────────────────

class _StocksView extends StatelessWidget {
  final List<Stock> stocks;
  final List<String> sectors;
  final String selectedSector;
  final ValueChanged<String> onSectorChanged;
  final Future<void> Function() onRefresh;
  final bool isTablet;
  final bool isLandscapeTablet;
  final String? dataDate;

  const _StocksView({
    required this.stocks,
    required this.sectors,
    required this.selectedSector,
    required this.onSectorChanged,
    required this.onRefresh,
    required this.isTablet,
    required this.isLandscapeTablet,
    this.dataDate,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _SectorFilter(
          sectors: sectors,
          selected: selectedSector,
          onChanged: onSectorChanged,
        ),
        if (dataDate != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
            child: Row(
              children: [
                const Icon(Icons.access_time_rounded,
                    size: 12, color: AppTheme.textSecondary),
                const SizedBox(width: 4),
                Text(
                  '資料更新至 $dataDate',
                  style: const TextStyle(
                      fontSize: 11, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ),
        const Divider(height: 1, color: AppTheme.divider),
        Expanded(
          child: RefreshIndicator(
            onRefresh: onRefresh,
            child: stocks.isEmpty
                ? const _EmptyView()
                : isLandscapeTablet
                    ? _GridList(stocks: stocks, isTablet: isTablet)
                    : _SingleList(stocks: stocks, isTablet: isTablet),
          ),
        ),
      ],
    );
  }
}

// ── 產業篩選列 ──────────────────────────────────────────────

class _SectorFilter extends StatelessWidget {
  final List<String> sectors;
  final String selected;
  final ValueChanged<String> onChanged;

  const _SectorFilter(
      {required this.sectors,
      required this.selected,
      required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: sectors.asMap().entries.map((entry) {
          final i = entry.key;
          final s = entry.value;
          final isSelected = s == selected;
          return Padding(
            padding: EdgeInsets.only(right: i < sectors.length - 1 ? 8 : 0),
            child: FilterChip(
              label: Text(s),
              selected: isSelected,
              onSelected: (_) => onChanged(s),
              showCheckmark: false,
              labelStyle: TextStyle(
                fontSize: 13,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                color: isSelected ? Colors.white : AppTheme.textSecondary,
              ),
              selectedColor: AppTheme.primary,
              backgroundColor: Colors.white,
              side: BorderSide(
                color: isSelected ? AppTheme.primary : AppTheme.divider,
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ── 手機：單欄列表 ──────────────────────────────────────────

class _SingleList extends StatelessWidget {
  final List<Stock> stocks;
  final bool isTablet;
  const _SingleList({required this.stocks, required this.isTablet});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      itemCount: stocks.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (_, i) =>
          StockCard(stock: stocks[i], isTablet: isTablet),
    );
  }
}

// ── 平板橫式：雙欄 Grid ─────────────────────────────────────

class _GridList extends StatelessWidget {
  final List<Stock> stocks;
  final bool isTablet;
  const _GridList({required this.stocks, required this.isTablet});

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(20),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 2.2,
      ),
      itemCount: stocks.length,
      itemBuilder: (_, i) =>
          StockCard(stock: stocks[i], isTablet: isTablet),
    );
  }
}

// ── 警示徽章 ───────────────────────────────────────────────

class _AlertChip extends StatelessWidget {
  final int count;
  final VoidCallback onTap;
  const _AlertChip({required this.count, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.alertRed.withOpacity(0.1),
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.warning_rounded,
                  color: AppTheme.alertRed, size: 16),
              const SizedBox(width: 4),
              Text(
                '$count 筆警示',
                style: const TextStyle(
                  color: AppTheme.alertRed,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Icon(Icons.keyboard_arrow_down_rounded,
                  color: AppTheme.alertRed, size: 16),
            ],
          ),
        ),
      ),
    );
  }
}

// ── 警示清單底部彈窗 ───────────────────────────────────────────

class _AlertSheet extends StatelessWidget {
  final List<Stock> stocks;
  const _AlertSheet({required this.stocks});

  @override
  Widget build(BuildContext context) {
    final maxH = MediaQuery.of(context).size.height * 0.75;
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: maxH),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppTheme.divider,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  const Icon(Icons.warning_rounded,
                      color: AppTheme.alertRed, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    '今日警示（${stocks.length}）',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: stocks.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (_, i) => StockCard(stock: stocks[i]),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── 空狀態、載入、錯誤 ─────────────────────────────────────

class _LoadingView extends StatelessWidget {
  const _LoadingView();

  @override
  Widget build(BuildContext context) => const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('載入中…', style: TextStyle(color: AppTheme.textSecondary)),
          ],
        ),
      );
}

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
              Text(
                message,
                textAlign: TextAlign.center,
                style:
                    const TextStyle(color: AppTheme.textSecondary, fontSize: 15),
              ),
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

class _EmptyView extends StatelessWidget {
  const _EmptyView();

  @override
  Widget build(BuildContext context) => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 120),
          Center(
            child: Text('此產業目前沒有追蹤股票',
                style: TextStyle(color: AppTheme.textSecondary)),
          ),
        ],
      );
}
