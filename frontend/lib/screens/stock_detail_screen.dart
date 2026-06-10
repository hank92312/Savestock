import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/stock.dart';
import '../services/api_service.dart';
import '../services/user_service.dart';
import '../services/watchlist_notifier.dart';
import '../theme/app_theme.dart';
import '../widgets/sector_badge.dart';

class StockDetailScreen extends StatefulWidget {
  final Stock stock;
  const StockDetailScreen({super.key, required this.stock});

  @override
  State<StockDetailScreen> createState() => _StockDetailScreenState();
}

class _StockDetailScreenState extends State<StockDetailScreen> {
  List<PricePoint>? _prices;
  String? _error;
  int _selectedDays = 30;

  List<DividendPoint>? _dividends;
  String? _divError;
  int _selectedDivMonths = 24;

  int? _userId;
  bool? _inWatchlist; // null = 仍在確認中
  bool _adding = false;

  static const _periods = [
    {'label': '30日', 'days': 30},
    {'label': '半年', 'days': 180},
    {'label': '1年',  'days': 365},
  ];

  static const _divPeriods = [
    {'label': '半年', 'months': 6},
    {'label': '1年',  'months': 12},
    {'label': '2年',  'months': 24},
    {'label': '5年',  'months': 60},
  ];

  @override
  void initState() {
    super.initState();
    _loadPrices();
    _loadDividends();
    _loadWatchlistStatus();
  }

  Future<void> _loadDividends() async {
    setState(() { _dividends = null; _divError = null; });
    try {
      final pts = await ApiService.fetchDividends(
          widget.stock.stockId, months: _selectedDivMonths);
      if (!mounted) return;
      setState(() => _dividends = pts);
    } catch (_) {
      if (!mounted) return;
      setState(() => _divError = '無法載入股利資料');
    }
  }

  void _selectDivPeriod(int months) {
    if (_selectedDivMonths == months) return;
    setState(() => _selectedDivMonths = months);
    _loadDividends();
  }

  Future<void> _loadWatchlistStatus() async {
    try {
      final userId = await UserService.getOrCreateUserId();
      final list = await ApiService.fetchWatchlist(userId);
      if (!mounted) return;
      final sid = widget.stock.stockId.toUpperCase();
      setState(() {
        _userId = userId;
        _inWatchlist = list.any((s) => s.stockId.toUpperCase() == sid);
      });
    } catch (_) {
      // 無法確認時隱藏按鈕，不阻塞詳情頁
    }
  }

  Future<void> _addToWatchlist() async {
    if (_userId == null || _adding) return;
    setState(() => _adding = true);
    final error = await ApiService.addToWatchlist(_userId!, widget.stock.stockId);
    if (!mounted) return;
    if (error != null) {
      setState(() => _adding = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error), backgroundColor: AppTheme.alertRed),
      );
      return;
    }
    setState(() {
      _adding = false;
      _inWatchlist = true;
    });
    WatchlistNotifier.instance.markDirty();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('已加入我的股票'),
        backgroundColor: AppTheme.gainGreen,
      ),
    );
  }

  Future<void> _loadPrices() async {
    setState(() { _prices = null; _error = null; });
    try {
      final pts = await ApiService.fetchPrices(
          widget.stock.stockId, days: _selectedDays);
      if (!mounted) return;
      setState(() => _prices = pts.reversed.toList()); // 舊→新排序
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = '無法載入價格資料');
    }
  }

  void _selectPeriod(int days) {
    if (_selectedDays == days) return;
    setState(() => _selectedDays = days);
    _loadPrices();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.stock;
    final code = s.stockId.replaceAll(RegExp(r'\.(TW|TWO)$'), '');

    return Scaffold(
      appBar: AppBar(
        title: Text(s.name),
        actions: [
          if (_inWatchlist == null)
            const SizedBox(
              width: 48,
              child: Center(
                child: SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            )
          else if (_inWatchlist!)
            const Padding(
              padding: EdgeInsets.only(right: 12),
              child: Tooltip(
                message: '已在我的股票',
                child: Icon(Icons.bookmark_rounded, color: AppTheme.primary),
              ),
            )
          else
            IconButton(
              icon: _adding
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.bookmark_add_outlined),
              tooltip: '加入我的股票',
              onPressed: _adding ? null : _addToWatchlist,
            ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: AppTheme.divider),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── 標題區 ──────────────────────────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        s.name,
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        code,
                        style: const TextStyle(
                          fontSize: 15,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                SectorBadge(s),
              ],
            ),

            const SizedBox(height: 24),

            // ── 殖利率（近一年 + 2年平均並列）──────────────
            _YieldHeader(stock: s),

            const SizedBox(height: 20),

            // ── 數據列 ──────────────────────────────────────
            _MetricsCard(stock: s),

            const SizedBox(height: 24),

            // ── 警示 ─────────────────────────────────────────
            if (s.alertFlag) ...[
              _AlertCard(reason: s.alertReason),
              const SizedBox(height: 24),
            ],

            // ── 折線圖 ───────────────────────────────────────
            Row(
              children: [
                const Text(
                  '收盤價走勢',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const Spacer(),
                ..._periods.map((p) {
                  final days = p['days'] as int;
                  final selected = _selectedDays == days;
                  return Padding(
                    padding: const EdgeInsets.only(left: 6),
                    child: GestureDetector(
                      onTap: () => _selectPeriod(days),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 5),
                        decoration: BoxDecoration(
                          color: selected
                              ? AppTheme.primary
                              : AppTheme.surface,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: selected
                                ? AppTheme.primary
                                : AppTheme.divider,
                          ),
                        ),
                        child: Text(
                          p['label'] as String,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: selected
                                ? Colors.white
                                : AppTheme.textSecondary,
                          ),
                        ),
                      ),
                    ),
                  );
                }),
              ],
            ),
            const SizedBox(height: 12),
            _PriceChart(prices: _prices, error: _error),

            const SizedBox(height: 28),

            // ── 股利折線圖 ───────────────────────────────────
            Row(
              children: [
                const Text(
                  '歷年股利分配',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const Spacer(),
                _PeriodChips(
                  labels: [for (final p in _divPeriods) p['label'] as String],
                  values: [for (final p in _divPeriods) p['months'] as int],
                  selected: _selectedDivMonths,
                  onSelect: _selectDivPeriod,
                ),
              ],
            ),
            const SizedBox(height: 12),
            _DividendChart(
              dividends: _dividends,
              error: _divError,
              listingMonths: widget.stock.listingMonths,
              selectedMonths: _selectedDivMonths,
            ),
          ],
        ),
      ),
    );
  }
}

// ── 期間切換膠囊（股利圖用）────────────────────────────────────

class _PeriodChips extends StatelessWidget {
  final List<String> labels;
  final List<int> values;
  final int selected;
  final ValueChanged<int> onSelect;

  const _PeriodChips({
    required this.labels,
    required this.values,
    required this.selected,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 0; i < labels.length; i++)
          Padding(
            padding: const EdgeInsets.only(left: 6),
            child: GestureDetector(
              onTap: () => onSelect(values[i]),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color:
                      selected == values[i] ? AppTheme.primary : AppTheme.surface,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: selected == values[i]
                        ? AppTheme.primary
                        : AppTheme.divider,
                  ),
                ),
                child: Text(
                  labels[i],
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: selected == values[i]
                        ? Colors.white
                        : AppTheme.textSecondary,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

// ── 殖利率（近一年 + 2年平均並列）────────────────────────────

Color _yieldColor(double? y) {
  if (y == null) return AppTheme.textSecondary;
  if (y >= 6) return AppTheme.gainGreen;
  if (y >= 4) return const Color(0xFF1565C0);
  return AppTheme.textPrimary;
}

class _YieldHeader extends StatelessWidget {
  final Stock stock;
  const _YieldHeader({required this.stock});

  /// 指標②（基準）的標籤，依上市時間調整，不沿用誤導名稱
  String get _baselineLabel {
    final m = stock.listingMonths;
    if (m == null || m >= 24) return '2年平均殖利率';
    if (m >= 12) return '上市以來年化';
    return '上市以來年化（涵蓋 $m 月）';
  }

  /// 指標③：5年平均殖利率標籤
  String get _fiveYearLabel {
    final m = stock.listingMonths;
    if (m == null || m >= 60) return '5年平均殖利率';
    return '上市以來年化（${(m / 12).round()}年）';
  }

  /// 上市不滿2年的新上市股不顯示5年指標
  bool get _show5y => !stock.isNewListing;

  @override
  Widget build(BuildContext context) {
    final hasBaseline = stock.estimatedYield != null;
    final hasOneYear = stock.yield1y != null;

    // 完全無配息紀錄
    if (!hasBaseline && !hasOneYear) {
      return _card(
        child: const Center(
          child: Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text('尚無配息紀錄',
                style: TextStyle(fontSize: 16, color: AppTheme.textSecondary)),
          ),
        ),
      );
    }

    // 計算顯示幾個 block，決定字體大小（3欄縮小避免截字）
    final blockCount = [
      if (!stock.isUnder1Y) 1,
      1, // baseline always shown
      if (_show5y) 1,
    ].length;
    final yieldFontSize = blockCount >= 3 ? 28.0 : 38.0;

    final blocks = <Widget>[
      // 上市滿 1 年才顯示「近一年殖利率」
      if (!stock.isUnder1Y) _yieldBlock('近一年殖利率', stock.yield1y, fontSize: yieldFontSize),
      _yieldBlock(_baselineLabel, stock.estimatedYield, fontSize: yieldFontSize),
      // 上市滿 2 年才顯示 5 年均（新上市股無意義）
      if (_show5y) _yieldBlock(_fiveYearLabel, stock.yield5y, fontSize: yieldFontSize),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _card(
          child: Row(
            children: [
              for (var i = 0; i < blocks.length; i++) ...[
                if (i > 0)
                  Container(width: 1, height: 52, color: AppTheme.divider),
                Expanded(child: blocks[i]),
              ],
            ],
          ),
        ),

        // 計算口徑說明：殖利率與股利皆含股票股利（配股面額還原）
        _caveat('殖利率／股利為股利合計（現金＋股票股利，配股按面額還原 =（配股比−1）×10）',
            AppTheme.textSecondary),
        // 邊界提示
        if (stock.isUnder1Y)
          _caveat('上市未滿 1 年，資料極有限，僅供參考', AppTheme.alertRed)
        else if (stock.isNewListing)
          _caveat('上市未滿 2 年，殖利率為上市迄今年化估算', AppTheme.textSecondary),
      ],
    );
  }

  Widget _card({required Widget child}) => Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.divider),
        ),
        child: child,
      );

  Widget _yieldBlock(String label, double? y, {double fontSize = 38}) {
    final color = _yieldColor(y);
    return Column(
      children: [
        Text(
          y != null ? '${y.toStringAsFixed(2)}%' : '—',
          style: TextStyle(
            fontSize: fontSize,
            fontWeight: FontWeight.w900,
            color: color,
            letterSpacing: -1,
          ),
        ),
        const SizedBox(height: 4),
        Text(label,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
      ],
    );
  }

  Widget _caveat(String text, Color color) => Padding(
        padding: const EdgeInsets.only(top: 8, left: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline_rounded, size: 14, color: color),
            const SizedBox(width: 6),
            Expanded(
              child: Text(text,
                  style: TextStyle(fontSize: 12, color: color, height: 1.4)),
            ),
          ],
        ),
      );
}

// ── 數據卡片 ──────────────────────────────────────────────────

class _MetricsCard extends StatelessWidget {
  final Stock stock;
  const _MetricsCard({required this.stock});

  /// 近一年股利標籤：上市不滿 12 月改標「近 X 月股利」
  String get _oneYearLabel {
    final m = stock.listingMonths;
    if (m != null && m < 12) return '近$m月股利';
    return '近1年股利';
  }

  @override
  Widget build(BuildContext context) {
    final isNew = stock.isNewListing;
    final isUnder5y = stock.listingMonths != null && stock.listingMonths! < 60;
    final label5y = isUnder5y ? '上市以來年化股利' : '近5年平均股利';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.divider),
      ),
      child: Column(
        children: [
          Row(
            children: [
              _Stat(
                label: '最新收盤價',
                value: stock.closePrice != null
                    ? '\$${stock.closePrice!.toStringAsFixed(2)}'
                    : '--',
              ),
              _Divider(),
              _Stat(
                label: _oneYearLabel,
                value: stock.dividend1y != null
                    ? '\$${stock.dividend1y!.toStringAsFixed(2)}'
                    : '--',
              ),
              _Divider(),
              _Stat(
                label: isNew ? '上市迄今平均股利' : '近2年平均股利',
                value: stock.avgDividend2y != null
                    ? '\$${stock.avgDividend2y!.toStringAsFixed(2)}'
                    : '--',
              ),
            ],
          ),
          // 近5年平均股利（新上市 <2年 不顯示）
          if (!isNew) ...[
            const SizedBox(height: 10),
            Container(height: 1, color: AppTheme.divider),
            const SizedBox(height: 10),
            Row(
              children: [
                _Stat(
                  label: label5y,
                  value: stock.avgDividend5y != null
                      ? '\$${stock.avgDividend5y!.toStringAsFixed(2)}'
                      : '--',
                ),
              ],
            ),
          ],
          if (stock.lastDate != null) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                '資料日期：${stock.lastDate}',
                style: const TextStyle(
                    fontSize: 11, color: AppTheme.textSecondary),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  final String label;
  final String value;
  const _Stat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 11, color: AppTheme.textSecondary)),
          const SizedBox(height: 4),
          Text(value,
              style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary)),
        ],
      ),
    );
  }
}

class _Divider extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        width: 1, height: 36, color: AppTheme.divider,
        margin: const EdgeInsets.symmetric(horizontal: 8),
      );
}

// ── 警示卡片 ──────────────────────────────────────────────────

class _AlertCard extends StatelessWidget {
  final String reason;
  const _AlertCard({required this.reason});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.alertRed.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.alertRed.withOpacity(0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.warning_rounded, color: AppTheme.alertRed, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('今日異常警示',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.alertRed)),
                const SizedBox(height: 4),
                Text(
                  reason.isNotEmpty ? reason : '今日出現異常訊號，請留意',
                  style: const TextStyle(
                      fontSize: 13, color: AppTheme.alertRed, height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── 折線圖 ────────────────────────────────────────────────────

class _PriceChart extends StatelessWidget {
  final List<PricePoint>? prices;
  final String? error;
  const _PriceChart({this.prices, this.error});

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return _ChartPlaceholder(message: error!);
    }
    if (prices == null) {
      return const SizedBox(
        height: 200,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (prices!.isEmpty) {
      return const _ChartPlaceholder(message: '暫無價格資料');
    }

    final spots = prices!.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value.close);
    }).toList();

    final closes = prices!.map((p) => p.close).toList();
    final minY = (closes.reduce((a, b) => a < b ? a : b) * 0.98);
    final maxY = (closes.reduce((a, b) => a > b ? a : b) * 1.02);

    return Container(
      height: 220,
      padding: const EdgeInsets.only(right: 8, top: 8, bottom: 4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.divider),
      ),
      child: LineChart(
        LineChartData(
          minY: minY,
          maxY: maxY,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => FlLine(
              color: AppTheme.divider,
              strokeWidth: 1,
            ),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 52,
                getTitlesWidget: (v, _) => Text(
                  v.toStringAsFixed(0),
                  style: const TextStyle(
                      fontSize: 10, color: AppTheme.textSecondary),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: (prices!.length / 5).ceilToDouble(),
                getTitlesWidget: (v, _) {
                  final idx = v.toInt();
                  if (idx < 0 || idx >= prices!.length) return const SizedBox();
                  final d = prices![idx].date;
                  // 超過 60 天顯示 年/月，否則顯示 月/日
                  final label = prices!.length > 60
                      ? '${d.year.toString().substring(2)}/${d.month.toString().padLeft(2, '0')}'
                      : '${d.month}/${d.day}';
                  return Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      label,
                      style: const TextStyle(
                          fontSize: 10, color: AppTheme.textSecondary),
                    ),
                  );
                },
              ),
            ),
            topTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              curveSmoothness: 0.3,
              color: AppTheme.primary,
              barWidth: 2.5,
              dotData: FlDotData(
                show: true,
                checkToShowDot: (spot, _) {
                  final idx = spot.x.toInt();
                  if (idx < 0 || idx >= prices!.length) return false;
                  return prices![idx].alertFlag;
                },
                getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
                  radius: 4,
                  color: AppTheme.alertRed,
                  strokeWidth: 0,
                ),
              ),
              belowBarData: BarAreaData(
                show: true,
                color: AppTheme.primary.withOpacity(0.08),
              ),
            ),
          ],
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (spots) => spots.map((s) {
                final idx = s.x.toInt();
                final pt = (idx >= 0 && idx < prices!.length)
                    ? prices![idx]
                    : null;
                final dateLabel = pt != null
                    ? '${pt.date.year}/${pt.date.month.toString().padLeft(2, '0')}/${pt.date.day.toString().padLeft(2, '0')}\n'
                    : '';
                return LineTooltipItem(
                  '$dateLabel\$${s.y.toStringAsFixed(2)}${pt?.alertFlag == true ? '\n⚠️ 警示' : ''}',
                  const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600),
                );
              }).toList(),
            ),
          ),
        ),
      ),
    );
  }
}

class _ChartPlaceholder extends StatelessWidget {
  final String message;
  const _ChartPlaceholder({required this.message});

  @override
  Widget build(BuildContext context) => Container(
        height: 200,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.divider),
        ),
        child: Text(message,
            style: const TextStyle(color: AppTheme.textSecondary)),
      );
}

// ── 股利堆疊直條圖 ────────────────────────────────────────────
// 每根 bar = 該次除權息的現金股利（淺藍）＋ 股票股利（深紫，配股面額還原）堆疊

class _DividendChart extends StatelessWidget {
  final List<DividendPoint>? dividends;
  final String? error;
  final int? listingMonths;
  final int selectedMonths;
  const _DividendChart({
    this.dividends,
    this.error,
    this.listingMonths,
    this.selectedMonths = 24,
  });

  static const Color _cashColor = Color(0xFF4FC3F7); // 淺藍＝現金股利
  static const Color _stockColor = Color(0xFF7E57C2); // 深紫＝股票股利

  @override
  Widget build(BuildContext context) {
    if (error != null) return _ChartPlaceholder(message: error!);
    if (dividends == null) {
      return const SizedBox(
        height: 200,
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (dividends!.isEmpty) {
      return const _ChartPlaceholder(message: '此期間無股利發放紀錄');
    }

    final divs = dividends!;
    final maxAmt = divs.map((d) => d.total).reduce((a, b) => a > b ? a : b);
    final maxY = maxAmt * 1.25;

    final groups = divs.asMap().entries.map((e) {
      final d = e.value;
      return BarChartGroupData(
        x: e.key,
        barRods: [
          BarChartRodData(
            toY: d.total,
            width: 18,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
            rodStackItems: [
              BarChartRodStackItem(0, d.cash, _cashColor),
              if (d.stock > 0)
                BarChartRodStackItem(d.cash, d.total, _stockColor),
            ],
          ),
        ],
      );
    }).toList();

    final bool show5yCaveat =
        selectedMonths == 60 && listingMonths != null && listingMonths! < 60;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 圖例
        Row(
          children: [
            _legendDot(_cashColor, '現金股利'),
            const SizedBox(width: 16),
            _legendDot(_stockColor, '股票股利'),
          ],
        ),
        const SizedBox(height: 10),
        Container(
          height: 220,
          padding: const EdgeInsets.only(right: 8, top: 8, bottom: 4, left: 4),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.divider),
          ),
          child: BarChart(
            BarChartData(
              maxY: maxY,
              minY: 0,
              alignment: BarChartAlignment.spaceAround,
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                getDrawingHorizontalLine: (_) =>
                    FlLine(color: AppTheme.divider, strokeWidth: 1),
              ),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 44,
                    getTitlesWidget: (v, _) => Text(
                      v.toStringAsFixed(1),
                      style: const TextStyle(
                          fontSize: 10, color: AppTheme.textSecondary),
                    ),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 22,
                    interval: 1,
                    getTitlesWidget: (v, _) {
                      final idx = v.toInt();
                      if (idx < 0 ||
                          idx >= divs.length ||
                          v != idx.toDouble()) {
                        return const SizedBox();
                      }
                      // 條數多時稀疏顯示，避免標籤重疊
                      final step = divs.length > 6
                          ? (divs.length / 5).ceil()
                          : 1;
                      if (idx % step != 0) return const SizedBox();
                      final d = divs[idx].date;
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          '${d.year.toString().substring(2)}/${d.month.toString().padLeft(2, '0')}',
                          style: const TextStyle(
                              fontSize: 10, color: AppTheme.textSecondary),
                        ),
                      );
                    },
                  ),
                ),
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              ),
              barGroups: groups,
              barTouchData: BarTouchData(
                touchTooltipData: BarTouchTooltipData(
                  getTooltipItem: (group, _, rod, __) {
                    final d = divs[group.x];
                    final dateLabel =
                        '${d.date.year}/${d.date.month.toString().padLeft(2, '0')}/${d.date.day.toString().padLeft(2, '0')}';
                    // 有配股時拆解現金／股票，否則只顯示現金配息
                    final body = d.stock > 0
                        ? '現金 \$${d.cash.toStringAsFixed(2)} ＋股票 \$${d.stock.toStringAsFixed(2)}\n合計 \$${d.total.toStringAsFixed(2)}'
                        : '配息 \$${d.total.toStringAsFixed(2)}';
                    return BarTooltipItem(
                      '$dateLabel\n$body',
                      const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w600),
                    );
                  },
                ),
              ),
            ),
          ),
        ),
        if (show5yCaveat) ...[
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline_rounded,
                  size: 14, color: AppTheme.textSecondary),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  '此股上市約 $listingMonths 個月，資料未滿 5 年，圖表僅顯示上市迄今紀錄',
                  style: const TextStyle(
                      fontSize: 12, color: AppTheme.textSecondary, height: 1.4),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _legendDot(Color c, String label) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: c,
              borderRadius: BorderRadius.circular(3),
            ),
          ),
          const SizedBox(width: 6),
          Text(label,
              style: const TextStyle(
                  fontSize: 12, color: AppTheme.textSecondary)),
        ],
      );
}
