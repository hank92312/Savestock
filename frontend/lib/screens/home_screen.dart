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

  Future<void> _loadStocks() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final stocks = await ApiService.fetchDefaultStocks();
      setState(() {
        _stocks = stocks;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = '無法載入資料，請確認網路連線';
        _loading = false;
      });
    }
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
              padding: const EdgeInsets.only(right: 8),
              child: _AlertChip(count: _alertCount),
            ),
          IconButton(
            icon: const Icon(Icons.search_rounded),
            tooltip: '搜尋股票',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AddStockScreen()),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: '更新資料',
            onPressed: _loadStocks,
          ),
          IconButton(
            icon: const Icon(Icons.help_outline_rounded),
            tooltip: '使用教學',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const OnboardingScreen(),
                fullscreenDialog: true,
              ),
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
                  onRefresh: _loadStocks,
                  isTablet: isTablet,
                  isLandscapeTablet: isLandscapeTablet,
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

  const _StocksView({
    required this.stocks,
    required this.sectors,
    required this.selectedSector,
    required this.onSectorChanged,
    required this.onRefresh,
    required this.isTablet,
    required this.isLandscapeTablet,
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
  const _AlertChip({required this.count});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.alertRed.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
      ),
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
        ],
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
