// 個人年度股利試算相關模型。
//
// Holding：使用者持股（存於裝置端 shared_preferences）。
// PortfolioItem / PortfolioEstimate：後端 /portfolio/estimate 回傳結果。

/// 估算基準（今年尚未除息完整時，全年估算依此推算）
const String basis1Y = '1y';
const String basis5Y = '5y';

String basisLabel(String? basis) {
  switch (basis) {
    case basis5Y:
      return '近5年平均';
    case basis1Y:
      return '近1年';
    default:
      return '近1年';
  }
}

class Holding {
  final String stockId; // 含後綴，如 "2330.TW"
  final String name; // 顯示用名稱
  final int quantity; // 股數（含零股，任意正整數）
  final String basis; // "1y" | "5y"

  const Holding({
    required this.stockId,
    required this.name,
    required this.quantity,
    this.basis = basis1Y,
  });

  Holding copyWith({String? name, int? quantity, String? basis}) => Holding(
        stockId: stockId,
        name: name ?? this.name,
        quantity: quantity ?? this.quantity,
        basis: basis ?? this.basis,
      );

  Map<String, dynamic> toJson() => {
        'stock_id': stockId,
        'name': name,
        'quantity': quantity,
        'basis': basis,
      };

  factory Holding.fromJson(Map<String, dynamic> j) => Holding(
        stockId: j['stock_id'] as String,
        name: j['name'] as String? ?? j['stock_id'] as String,
        quantity: (j['quantity'] as num).toInt(),
        basis: j['basis'] as String? ?? basis1Y,
      );

  /// 顯示用純代號
  String get code => stockId.replaceAll(RegExp(r'\.(TW|TWO)$'), '');
}

class PortfolioItem {
  final String stockId;
  final String name;
  final int quantity;
  final double perShare; // 每股股利
  final String? source; // "announced" | "1y" | "5y"
  final bool isEstimated; // 已公告為 false
  final double amount; // 全年金額
  final double paidThisYear; // 今年已實際除息金額（資訊）
  final double sharePct; // 占總額比重
  final bool available; // 查無資料時為 false

  const PortfolioItem({
    required this.stockId,
    required this.name,
    required this.quantity,
    required this.perShare,
    required this.source,
    required this.isEstimated,
    required this.amount,
    required this.paidThisYear,
    required this.sharePct,
    required this.available,
  });

  factory PortfolioItem.fromJson(Map<String, dynamic> j) => PortfolioItem(
        stockId: j['stock_id'] as String,
        name: j['name'] as String? ?? j['stock_id'] as String,
        quantity: (j['quantity'] as num).toInt(),
        perShare: (j['per_share'] as num?)?.toDouble() ?? 0,
        source: j['source'] as String?,
        isEstimated: j['is_estimated'] as bool? ?? true,
        amount: (j['amount'] as num?)?.toDouble() ?? 0,
        paidThisYear: (j['paid_this_year'] as num?)?.toDouble() ?? 0,
        sharePct: (j['share_pct'] as num?)?.toDouble() ?? 0,
        available: j['available'] as bool? ?? true,
      );

  String get code => stockId.replaceAll(RegExp(r'\.(TW|TWO)$'), '');

  /// 是否採用已公告值
  bool get isAnnounced => source == 'announced';
}

class PortfolioEstimate {
  final double total;
  final String currency;
  final String disclaimer;
  final List<PortfolioItem> items;
  final List<PortfolioItem> highImpact;

  const PortfolioEstimate({
    required this.total,
    required this.currency,
    required this.disclaimer,
    required this.items,
    required this.highImpact,
  });

  factory PortfolioEstimate.fromJson(Map<String, dynamic> j) {
    List<PortfolioItem> parse(String key) => ((j[key] as List?) ?? [])
        .map((e) => PortfolioItem.fromJson(e as Map<String, dynamic>))
        .toList();
    return PortfolioEstimate(
      total: (j['total'] as num?)?.toDouble() ?? 0,
      currency: j['currency'] as String? ?? 'TWD',
      disclaimer: j['disclaimer'] as String? ?? '',
      items: parse('items'),
      highImpact: parse('high_impact'),
    );
  }

  /// 有任何查無資料的股票
  bool get hasUnavailable => items.any((it) => !it.available);
  List<PortfolioItem> get unavailable =>
      items.where((it) => !it.available).toList();

  /// 今年已實際除息合計
  double get totalPaidThisYear =>
      items.fold(0.0, (sum, it) => sum + it.paidThisYear);
}
