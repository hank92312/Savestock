import 'dart:async';
import 'dart:convert';
import 'dart:js_interop';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:web/web.dart' as web;
import '../models/portfolio.dart';
import '../services/api_service.dart';
import '../services/portfolio_service.dart';
import '../theme/app_theme.dart';

/// 個人年度股利試算：輸入持股 → 估算今年度可領股利。
/// 持股存於裝置端；估算由後端 /portfolio/estimate 計算（口徑與 App/Django 共用）。
class DividendCalcScreen extends StatefulWidget {
  const DividendCalcScreen({super.key});

  @override
  State<DividendCalcScreen> createState() => _DividendCalcScreenState();
}

class _DividendCalcScreenState extends State<DividendCalcScreen> {
  final _repaintKey = GlobalKey();

  List<Holding> _holdings = [];
  PortfolioEstimate? _result;
  bool _loading = true;
  bool _calculating = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final holdings = await PortfolioService.load();
    if (!mounted) return;
    setState(() {
      _holdings = holdings;
      _loading = false;
    });
  }

  Future<void> _persist() => PortfolioService.save(_holdings);

  Future<void> _addHolding() async {
    final holding = await showModalBottomSheet<Holding>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => const _AddHoldingSheet(),
    );
    if (holding == null) return;

    setState(() {
      // 同一檔已存在 → 覆蓋股數與基準，避免重複列
      final idx = _holdings.indexWhere((h) => h.stockId == holding.stockId);
      if (idx >= 0) {
        _holdings[idx] = holding;
      } else {
        _holdings.add(holding);
      }
      _result = null;
    });
    await _persist();
  }

  Future<void> _removeHolding(Holding h) async {
    setState(() {
      _holdings.removeWhere((x) => x.stockId == h.stockId);
      _result = null;
    });
    await _persist();
  }

  Future<void> _setBasis(Holding h, String basis) async {
    setState(() {
      final idx = _holdings.indexWhere((x) => x.stockId == h.stockId);
      if (idx >= 0) _holdings[idx] = _holdings[idx].copyWith(basis: basis);
      _result = null;
    });
    await _persist();
  }

  Future<void> _calculate() async {
    if (_holdings.isEmpty) return;
    setState(() => _calculating = true);
    try {
      final result = await ApiService.estimatePortfolio(_holdings);
      if (!mounted) return;
      setState(() {
        _result = result;
        _calculating = false;
      });
      _showDisclaimerDialog(result); // 點 5：估算後顯示提示窗
    } catch (_) {
      if (!mounted) return;
      setState(() => _calculating = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('估算失敗，請稍後再試（部分股票首次查詢較慢）')),
      );
    }
  }

  String _buildReportUrl() {
    final json = jsonEncode(_holdings
        .map((h) => {'s': h.stockId, 'q': h.quantity, 'b': h.basis})
        .toList());
    final d = base64Url.encode(utf8.encode(json)).replaceAll('=', '');
    return '${ApiService.reportBase}/report?d=$d';
  }

  void _openUrl(String url) {
    web.window.open(url, '_blank');
  }

  Future<void> _showShareSheet() async {
    if (_result == null || !mounted) return;
    final reportUrl = _buildReportUrl();
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: SingleChildScrollView(
          child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40, height: 4,
                  decoration: BoxDecoration(
                    color: AppTheme.divider,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text('分享',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              _ShareTile(
                icon: Icons.link_rounded,
                label: '複製連結',
                subtitle: '複製報表網址到剪貼簿',
                onTap: () {
                  Navigator.pop(ctx);
                  Clipboard.setData(ClipboardData(text: reportUrl));
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('連結已複製')),
                    );
                  }
                },
              ),
              _ShareTile(
                icon: Icons.description_outlined,
                label: '開啟報表',
                subtitle: '在新分頁開啟完整網頁報表（可列印）',
                onTap: () {
                  Navigator.pop(ctx);
                  _openUrl(reportUrl);
                },
              ),
              const Divider(height: 20),
              _ShareTile(
                icon: Icons.chat_rounded,
                iconColor: const Color(0xFF06C755),
                label: 'LINE',
                subtitle: '分享報表連結到 LINE',
                onTap: () {
                  Navigator.pop(ctx);
                  _openUrl(
                    'https://social-plugins.line.me/lineit/share'
                    '?url=${Uri.encodeComponent(reportUrl)}',
                  );
                },
              ),
              _ShareTile(
                icon: Icons.facebook,
                iconColor: const Color(0xFF1877F2),
                label: 'Facebook',
                subtitle: '分享報表連結到 Facebook',
                onTap: () {
                  Navigator.pop(ctx);
                  _openUrl(
                    'https://www.facebook.com/sharer/sharer.php'
                    '?u=${Uri.encodeComponent(reportUrl)}',
                  );
                },
              ),
              const Divider(height: 20),
              _ShareTile(
                icon: Icons.download_rounded,
                label: '下載試算圖片',
                subtitle: '儲存為 PNG，可直接分享到 IG 等社群',
                onTap: () {
                  Navigator.pop(ctx);
                  _captureAndDownloadImage();
                },
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
        ),
      ),
    );
  }

  Future<void> _captureAndDownloadImage() async {
    try {
      final boundary = _repaintKey.currentContext?.findRenderObject()
          as RenderRepaintBoundary?;
      if (boundary == null) return;

      final image = await boundary.toImage(pixelRatio: 3.0);
      final byteData =
          await image.toByteData(format: ui.ImageByteFormat.png);
      if (byteData == null) return;

      final bytes = byteData.buffer.asUint8List();
      final blob = web.Blob(
        <JSAny>[bytes.toJS].toJS,
        web.BlobPropertyBag(type: 'image/png'),
      );
      final url = web.URL.createObjectURL(blob);
      final anchor =
          web.document.createElement('a') as web.HTMLAnchorElement;
      anchor.href = url;
      anchor.download = 'savestock_股利試算.png';
      web.document.body!.append(anchor);
      anchor.click();
      anchor.remove();
      web.URL.revokeObjectURL(url);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('圖片已下載')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('截圖失敗，請稍後再試')),
        );
      }
    }
  }

  void _showDisclaimerDialog(PortfolioEstimate result) {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.info_outline_rounded, color: AppTheme.primary),
            SizedBox(width: 8),
            Text('估算說明', style: TextStyle(fontSize: 17)),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                result.disclaimer,
                style: const TextStyle(
                    fontSize: 13.5, height: 1.6, color: AppTheme.textPrimary),
              ),
              if (result.highImpact.isNotEmpty) ...[
                const SizedBox(height: 16),
                const Text(
                  '影響較大的個股',
                  style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      color: AppTheme.textPrimary),
                ),
                const SizedBox(height: 4),
                const Text(
                  '這些個股占你估算股利比重較高，一旦實際配息與歷史不同，最會影響總額：',
                  style: TextStyle(fontSize: 12.5, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 8),
                ...result.highImpact.map((it) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Row(
                        children: [
                          const Icon(Icons.circle,
                              size: 6, color: AppTheme.primary),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              '${it.name}（${it.code}）',
                              style: const TextStyle(fontSize: 13),
                            ),
                          ),
                          Text(
                            '占 ${it.sharePct.toStringAsFixed(0)}%',
                            style: const TextStyle(
                                fontSize: 12.5,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.primary),
                          ),
                        ],
                      ),
                    )),
              ],
              if (result.hasUnavailable) ...[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.alertRed.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '以下股票查無股利資料，未計入總額：'
                    '${result.unavailable.map((e) => e.code).join('、')}',
                    style: const TextStyle(
                        fontSize: 12.5, color: AppTheme.alertRed),
                  ),
                ),
              ],
            ],
          ),
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('我了解了'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('年度股利試算'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_rounded),
            tooltip: '新增持股',
            onPressed: _addHolding,
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _holdings.isEmpty
              ? _EmptyView(onAdd: _addHolding)
              : _buildContent(),
      bottomNavigationBar: _holdings.isEmpty
          ? null
          : SafeArea(
              minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: SizedBox(
                height: 50,
                child: FilledButton.icon(
                  onPressed: _calculating ? null : _calculate,
                  icon: _calculating
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.calculate_rounded),
                  label: Text(_calculating ? '估算中…' : '計算今年可領股利'),
                  style: FilledButton.styleFrom(
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ),
    );
  }

  Widget _buildContent() {
    return Stack(
      children: [
        ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_result != null) ...[
              _ResultSummary(result: _result!),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _showShareSheet,
                  icon: const Icon(Icons.share_rounded, size: 20),
                  label: const Text('分享'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
              const SizedBox(height: 20),
            ],
            Row(
              children: [
                const Text('我的持股',
                    style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary)),
                const SizedBox(width: 6),
                Text('（${_holdings.length} 檔）',
                    style: const TextStyle(
                        fontSize: 13, color: AppTheme.textSecondary)),
              ],
            ),
            const SizedBox(height: 10),
            ..._holdings.map((h) {
              final item = _result?.items
                  .where((it) => it.stockId == h.stockId)
                  .cast<PortfolioItem?>()
                  .firstWhere((it) => true, orElse: () => null);
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _HoldingCard(
                  holding: h,
                  item: item,
                  onRemove: () => _removeHolding(h),
                  onBasisChanged: (b) => _setBasis(h, b),
                ),
              );
            }),
            const SizedBox(height: 4),
            OutlinedButton.icon(
              onPressed: _addHolding,
              icon: const Icon(Icons.add_rounded, size: 20),
              label: const Text('新增持股'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
        if (_result != null)
          Positioned(
            left: -2000,
            top: 0,
            width: 375,
            child: RepaintBoundary(
              key: _repaintKey,
              child: _ShareCard(result: _result!),
            ),
          ),
      ],
    );
  }
}

// ── 千分位格式 ────────────────────────────────────────────────────
String _money(double v) {
  final s = v.round().toString();
  final buf = StringBuffer();
  for (int i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) buf.write(',');
    buf.write(s[i]);
  }
  return buf.toString();
}

// ── 結果摘要卡 ────────────────────────────────────────────────────
class _ResultSummary extends StatelessWidget {
  final PortfolioEstimate result;
  const _ResultSummary({required this.result});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppTheme.primary, AppTheme.primary.withOpacity(0.78)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppTheme.cardRadius),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('今年度預估可領股利',
              style: TextStyle(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 6),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              const Text('NT\$ ',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w600)),
              Text(_money(result.total),
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 32,
                      fontWeight: FontWeight.w800)),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '今年已實際除息 NT\$ ${_money(result.totalPaidThisYear)}',
            style: const TextStyle(color: Colors.white70, fontSize: 12.5),
          ),
        ],
      ),
    );
  }
}

// ── 單檔持股卡 ────────────────────────────────────────────────────
class _HoldingCard extends StatelessWidget {
  final Holding holding;
  final PortfolioItem? item; // 計算後對應結果（未計算時為 null）
  final VoidCallback onRemove;
  final ValueChanged<String> onBasisChanged;

  const _HoldingCard({
    required this.holding,
    required this.item,
    required this.onRemove,
    required this.onBasisChanged,
  });

  @override
  Widget build(BuildContext context) {
    final unavailable = item != null && !item!.available;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
      decoration: AppTheme.cardDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(holding.name,
                        style: const TextStyle(
                            fontSize: 15, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text('${holding.code} ・ ${holding.quantity} 股',
                        style: const TextStyle(
                            fontSize: 12.5, color: AppTheme.textSecondary)),
                  ],
                ),
              ),
              if (item != null && item!.available)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('NT\$ ${_money(item!.amount)}',
                        style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                            color: AppTheme.primary)),
                    Text(
                        item!.isAnnounced
                            ? '每股 ${item!.perShare.toStringAsFixed(2)}・已公告'
                            : '每股 ${item!.perShare.toStringAsFixed(2)}',
                        style: TextStyle(
                            fontSize: 11.5,
                            color: item!.isAnnounced
                                ? AppTheme.gainGreen
                                : AppTheme.textSecondary,
                            fontWeight: item!.isAnnounced
                                ? FontWeight.w600
                                : FontWeight.normal)),
                  ],
                ),
              IconButton(
                icon: const Icon(Icons.close_rounded,
                    size: 20, color: AppTheme.textSecondary),
                tooltip: '移除',
                onPressed: onRemove,
              ),
            ],
          ),
          if (unavailable)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text('查無股利資料，未計入',
                  style: TextStyle(fontSize: 12, color: AppTheme.alertRed)),
            ),
          const SizedBox(height: 8),
          // 估算基準切換
          Row(
            children: [
              const Text('估算基準：',
                  style:
                      TextStyle(fontSize: 12.5, color: AppTheme.textSecondary)),
              const SizedBox(width: 4),
              _BasisChip(
                label: '近1年',
                selected: holding.basis == basis1Y,
                onTap: () => onBasisChanged(basis1Y),
              ),
              const SizedBox(width: 6),
              _BasisChip(
                label: '近5年平均',
                selected: holding.basis == basis5Y,
                onTap: () => onBasisChanged(basis5Y),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _BasisChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _BasisChip(
      {required this.label, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
        decoration: BoxDecoration(
          color: selected
              ? AppTheme.primary.withOpacity(0.12)
              : AppTheme.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? AppTheme.primary : AppTheme.divider,
            width: selected ? 1.4 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            color: selected ? AppTheme.primary : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }
}

// ── 空清單引導 ────────────────────────────────────────────────────
class _EmptyView extends StatelessWidget {
  final VoidCallback onAdd;
  const _EmptyView({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.savings_outlined, size: 64, color: Colors.grey.shade300),
            const SizedBox(height: 20),
            const Text('試算你的年度股利',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary)),
            const SizedBox(height: 10),
            const Text(
              '輸入你持有的股票與股數（可含零股）\n系統依歷史配息估算今年可領股利',
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: 14, color: AppTheme.textSecondary, height: 1.6),
            ),
            const SizedBox(height: 28),
            FilledButton.icon(
              onPressed: onAdd,
              icon: const Icon(Icons.add_rounded),
              label: const Text('新增第一檔持股'),
              style: FilledButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── 分享圖片卡（off-screen 渲染，供 RepaintBoundary 截圖）────────────
class _ShareCard extends StatelessWidget {
  final PortfolioEstimate result;
  const _ShareCard({required this.result});

  @override
  Widget build(BuildContext context) {
    final availableItems = result.items.where((it) => it.available).toList();
    final year = DateTime.now().year;
    return Container(
      width: 375,
      color: Colors.white,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
            child: Row(
              children: [
                const Icon(Icons.savings_rounded,
                    color: AppTheme.primary, size: 20),
                const SizedBox(width: 8),
                const Text('Savestock',
                    style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.primary)),
                const Spacer(),
                Text('$year 年度股利試算',
                    style: const TextStyle(
                        fontSize: 12, color: AppTheme.textSecondary)),
              ],
            ),
          ),
          // Summary gradient card
          Container(
            width: double.infinity,
            margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [AppTheme.primary, AppTheme.primary.withOpacity(0.78)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(AppTheme.cardRadius),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('今年度預估可領股利',
                    style: TextStyle(color: Colors.white70, fontSize: 12)),
                const SizedBox(height: 4),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    const Text('NT\$ ',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                    Text(_money(result.total),
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w800)),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  '今年已實際除息 NT\$ ${_money(result.totalPaidThisYear)}',
                  style:
                      const TextStyle(color: Colors.white70, fontSize: 11.5),
                ),
              ],
            ),
          ),
          // Holdings
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('持股明細',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary)),
                const SizedBox(height: 8),
                ...availableItems.map((it) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _ShareHoldingRow(item: it),
                    )),
                if (result.unavailable.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2, bottom: 4),
                    child: Text(
                      '查無資料：${result.unavailable.map((e) => e.code).join('、')}',
                      style: const TextStyle(
                          fontSize: 11, color: AppTheme.alertRed),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // Footer
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppTheme.divider)),
            ),
            child: const Center(
              child: Text('savestock.netlify.app',
                  style: TextStyle(
                      fontSize: 11, color: AppTheme.textSecondary)),
            ),
          ),
        ],
      ),
    );
  }
}

class _ShareHoldingRow extends StatelessWidget {
  final PortfolioItem item;
  const _ShareHoldingRow({required this.item});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name,
                    style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary)),
                Row(
                  children: [
                    Text(item.code,
                        style: const TextStyle(
                            fontSize: 11.5, color: AppTheme.textSecondary)),
                    const SizedBox(width: 4),
                    Text('${item.quantity} 股',
                        style: const TextStyle(
                            fontSize: 11.5, color: AppTheme.textSecondary)),
                  ],
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('NT\$ ${_money(item.amount)}',
                  style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.primary)),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('每股 ${item.perShare.toStringAsFixed(2)}',
                      style: const TextStyle(
                          fontSize: 11, color: AppTheme.textSecondary)),
                  const SizedBox(width: 4),
                  if (item.isAnnounced)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: AppTheme.gainGreen.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text('已公告',
                          style: TextStyle(
                              fontSize: 10,
                              color: AppTheme.gainGreen,
                              fontWeight: FontWeight.w600)),
                    )
                  else
                    const Text('估算',
                        style: TextStyle(
                            fontSize: 10, color: AppTheme.textSecondary)),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── 分享選項列 ────────────────────────────────────────────────────
class _ShareTile extends StatelessWidget {
  final IconData icon;
  final Color? iconColor;
  final String label;
  final String subtitle;
  final VoidCallback onTap;

  const _ShareTile({
    required this.icon,
    this.iconColor,
    required this.label,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = iconColor ?? AppTheme.primary;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: color, size: 22),
      ),
      title: Text(label,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
      subtitle: Text(subtitle,
          style: const TextStyle(
              fontSize: 12.5, color: AppTheme.textSecondary)),
      onTap: onTap,
    );
  }
}

// ── 新增持股的底部彈窗（搜尋 → 選股 → 輸入股數 + 基準）──────────────
class _AddHoldingSheet extends StatefulWidget {
  const _AddHoldingSheet();

  @override
  State<_AddHoldingSheet> createState() => _AddHoldingSheetState();
}

class _AddHoldingSheetState extends State<_AddHoldingSheet> {
  final _searchController = TextEditingController();
  final _qtyController = TextEditingController();
  Timer? _debounce;

  List<SearchCandidate> _candidates = [];
  bool _loadingCandidates = false;
  SearchCandidate? _selected; // 已選股票（進入股數輸入階段）
  String _basis = basis1Y;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    _qtyController.dispose();
    super.dispose();
  }

  void _onSearchChanged() {
    final q = _searchController.text.trim();
    _debounce?.cancel();
    if (q.isEmpty) {
      setState(() => _candidates = []);
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 300), () => _search(q));
  }

  Future<void> _search(String q) async {
    setState(() => _loadingCandidates = true);
    try {
      final candidates = await ApiService.searchStocks(q);
      if (!mounted) return;
      setState(() {
        _candidates = candidates;
        _loadingCandidates = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loadingCandidates = false);
    }
  }

  void _select(SearchCandidate c) {
    setState(() {
      _selected = c;
      _candidates = [];
    });
  }

  void _confirm() {
    final qty = int.tryParse(_qtyController.text.trim());
    if (_selected == null || qty == null || qty <= 0) return;
    Navigator.pop(
      context,
      Holding(
        stockId: _selected!.stockId,
        name: _selected!.name,
        quantity: qty,
        basis: _basis,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: Container(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.8,
        ),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
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
            const SizedBox(height: 16),
            Text(_selected == null ? '搜尋股票' : '輸入持股資訊',
                style: const TextStyle(
                    fontSize: 17, fontWeight: FontWeight.w700)),
            const SizedBox(height: 14),
            if (_selected == null) ..._buildSearchPhase() else ..._buildDetailPhase(),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildSearchPhase() {
    return [
      TextField(
        controller: _searchController,
        autofocus: true,
        decoration: InputDecoration(
          hintText: '輸入代號或中文名稱（如 0050、台積電）',
          prefixIcon: const Icon(Icons.search_rounded),
          suffixIcon: _loadingCandidates
              ? const Padding(
                  padding: EdgeInsets.all(14),
                  child: SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2)),
                )
              : null,
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
        ),
      ),
      const SizedBox(height: 8),
      Flexible(
        child: ListView.separated(
          shrinkWrap: true,
          itemCount: _candidates.length,
          separatorBuilder: (_, __) =>
              const Divider(height: 1, color: AppTheme.divider),
          itemBuilder: (_, i) {
            final c = _candidates[i];
            return ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(c.name,
                  style: const TextStyle(
                      fontWeight: FontWeight.w600, fontSize: 15)),
              subtitle: Text(c.code,
                  style: const TextStyle(
                      color: AppTheme.textSecondary, fontSize: 13)),
              trailing: const Icon(Icons.chevron_right_rounded,
                  color: AppTheme.textSecondary),
              onTap: () => _select(c),
            );
          },
        ),
      ),
    ];
  }

  List<Widget> _buildDetailPhase() {
    return [
      Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_selected!.name,
                      style: const TextStyle(
                          fontSize: 15, fontWeight: FontWeight.w700)),
                  Text(_selected!.code,
                      style: const TextStyle(
                          fontSize: 13, color: AppTheme.textSecondary)),
                ],
              ),
            ),
            TextButton(
              onPressed: () => setState(() => _selected = null),
              child: const Text('重新選擇'),
            ),
          ],
        ),
      ),
      const SizedBox(height: 16),
      const Text('持有股數（可輸入零股）',
          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
      const SizedBox(height: 6),
      TextField(
        controller: _qtyController,
        autofocus: true,
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        onSubmitted: (_) => _confirm(),
        decoration: InputDecoration(
          hintText: '例如 1000、50',
          suffixText: '股',
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
        ),
      ),
      const SizedBox(height: 16),
      const Text('今年未公布配息時的估算基準',
          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
      const SizedBox(height: 8),
      Row(
        children: [
          _BasisChip(
            label: '近1年',
            selected: _basis == basis1Y,
            onTap: () => setState(() => _basis = basis1Y),
          ),
          const SizedBox(width: 8),
          _BasisChip(
            label: '近5年平均',
            selected: _basis == basis5Y,
            onTap: () => setState(() => _basis = basis5Y),
          ),
        ],
      ),
      const SizedBox(height: 20),
      SizedBox(
        width: double.infinity,
        height: 48,
        child: FilledButton(
          onPressed: _confirm,
          style: FilledButton.styleFrom(
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
          child: const Text('加入持股'),
        ),
      ),
    ];
  }
}
