import 'package:flutter/material.dart';
import '../models/stock.dart';
import '../screens/stock_detail_screen.dart';
import '../theme/app_theme.dart';
import 'sector_badge.dart';

class StockCard extends StatelessWidget {
  final Stock stock;
  final bool isTablet;

  const StockCard({super.key, required this.stock, this.isTablet = false});

  @override
  Widget build(BuildContext context) {
    final yield_ = stock.estimatedYield;
    final price = stock.closePrice;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => StockDetailScreen(stock: stock),
          ),
        ),
        child: Padding(
          padding: EdgeInsets.all(isTablet ? 20 : 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _TopRow(stock: stock, isTablet: isTablet),
              const SizedBox(height: 12),
              _MetricsRow(
                yield_: yield_,
                price: price,
                avgDiv: stock.avgDividend2y,
                isTablet: isTablet,
              ),
              if (stock.alertFlag) ...[
                const SizedBox(height: 10),
                _AlertBanner(reason: stock.alertReason),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _TopRow extends StatelessWidget {
  final Stock stock;
  final bool isTablet;
  const _TopRow({required this.stock, required this.isTablet});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Flexible(
                    child: Text(
                      stock.name,
                      style: TextStyle(
                        fontSize: isTablet ? 18 : 16,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (stock.alertFlag) ...[
                    const SizedBox(width: 6),
                    const Icon(Icons.warning_rounded,
                        color: AppTheme.alertRed, size: 18),
                  ],
                ],
              ),
              const SizedBox(height: 4),
              Text(
                stock.stockId.replaceAll('.TW', ''),
                style: const TextStyle(
                  fontSize: 13,
                  color: AppTheme.textSecondary,
                ),
              ),
            ],
          ),
        ),
        SectorBadge(stock),
      ],
    );
  }
}

class _MetricsRow extends StatelessWidget {
  final double? yield_;
  final double? price;
  final double? avgDiv;
  final bool isTablet;
  const _MetricsRow(
      {this.yield_, this.price, this.avgDiv, required this.isTablet});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _Metric(
          label: '估算殖利率',
          value: yield_ != null ? '${yield_!.toStringAsFixed(2)}%' : '--',
          valueColor: _yieldColor(yield_),
          isLarge: true,
          isTablet: isTablet,
        ),
        const SizedBox(width: 24),
        _Metric(
          label: '現價',
          value: price != null ? '\$${price!.toStringAsFixed(2)}' : '--',
          isTablet: isTablet,
        ),
        const SizedBox(width: 24),
        _Metric(
          label: '近2年平均股利',
          value: avgDiv != null ? '\$${avgDiv!.toStringAsFixed(2)}' : '--',
          isTablet: isTablet,
        ),
      ],
    );
  }

  Color _yieldColor(double? y) {
    if (y == null) return AppTheme.textSecondary;
    if (y >= 6) return AppTheme.gainGreen;
    if (y >= 4) return const Color(0xFF1565C0);
    return AppTheme.textPrimary;
  }
}

class _Metric extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;
  final bool isLarge;
  final bool isTablet;

  const _Metric({
    required this.label,
    required this.value,
    this.valueColor,
    this.isLarge = false,
    required this.isTablet,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: isLarge
                ? (isTablet ? 22 : 20)
                : (isTablet ? 16 : 15),
            fontWeight: isLarge ? FontWeight.w800 : FontWeight.w600,
            color: valueColor ?? AppTheme.textPrimary,
          ),
        ),
      ],
    );
  }
}

class _AlertBanner extends StatelessWidget {
  final String reason;
  const _AlertBanner({required this.reason});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.alertRed.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.alertRed.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: AppTheme.alertRed, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              reason.isNotEmpty ? reason : '今日出現異常訊號，請留意',
              style: const TextStyle(
                fontSize: 13,
                color: AppTheme.alertRed,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
