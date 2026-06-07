import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/stock.dart';
import '../services/api_service.dart';
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

  static const _periods = [
    {'label': '30日', 'days': 30},
    {'label': '半年', 'days': 180},
    {'label': '1年',  'days': 365},
  ];

  @override
  void initState() {
    super.initState();
    _loadPrices();
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

            // ── 殖利率大字 ──────────────────────────────────
            _YieldHero(yield_: s.estimatedYield),

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
          ],
        ),
      ),
    );
  }
}

// ── 殖利率大字 ────────────────────────────────────────────────

class _YieldHero extends StatelessWidget {
  final double? yield_;
  const _YieldHero({this.yield_});

  @override
  Widget build(BuildContext context) {
    final hasValue = yield_ != null;
    final color = _yieldColor(yield_);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 24),
      decoration: BoxDecoration(
        color: color.withOpacity(0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          Text(
            hasValue ? '${yield_!.toStringAsFixed(2)}%' : '--',
            style: TextStyle(
              fontSize: 48,
              fontWeight: FontWeight.w900,
              color: color,
              letterSpacing: -1,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            '估算殖利率',
            style: TextStyle(fontSize: 14, color: AppTheme.textSecondary),
          ),
        ],
      ),
    );
  }

  Color _yieldColor(double? y) {
    if (y == null) return AppTheme.textSecondary;
    if (y >= 6) return AppTheme.gainGreen;
    if (y >= 4) return const Color(0xFF1565C0);
    return AppTheme.textPrimary;
  }
}

// ── 數據卡片 ──────────────────────────────────────────────────

class _MetricsCard extends StatelessWidget {
  final Stock stock;
  const _MetricsCard({required this.stock});

  @override
  Widget build(BuildContext context) {
    final isNew = stock.isNewListing;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.divider),
          ),
          child: Row(
            children: [
              _Stat(
                label: '最新收盤價',
                value: stock.closePrice != null
                    ? '\$${stock.closePrice!.toStringAsFixed(1)}'
                    : '--',
              ),
              _Divider(),
              _Stat(
                label: isNew ? '上市迄今平均股利' : '近2年平均股利',
                value: stock.avgDividend2y != null
                    ? '\$${stock.avgDividend2y!.toStringAsFixed(2)}'
                    : '--',
              ),
              _Divider(),
              _Stat(
                label: '資料日期',
                value: stock.lastDate ?? '--',
              ),
            ],
          ),
        ),
        if (isNew) ...[
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline_rounded,
                  size: 14, color: AppTheme.textSecondary),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  '此股上市未滿 2 年，股利為上市迄今約 ${stock.listingMonths} 個月資料年化估算，僅供參考',
                  style: const TextStyle(
                      fontSize: 12,
                      color: AppTheme.textSecondary,
                      height: 1.4),
                ),
              ),
            ],
          ),
        ],
      ],
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
                  '$dateLabel\$${s.y.toStringAsFixed(1)}${pt?.alertFlag == true ? '\n⚠️ 警示' : ''}',
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
