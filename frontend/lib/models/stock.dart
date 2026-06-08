class Stock {
  final String stockId;
  final String name;
  final String sector;
  final double? avgDividend2y;
  final double? dividend1y; // 近12個月現金股利合計
  final int? listingMonths; // 上市迄今月數；< 24 視為新上市
  final double? closePrice;
  final double? estimatedYield; // 基準殖利率（2年平均 / 上市以來年化）
  final double? yield1y; // 近一年殖利率
  final bool alertFlag;
  final String alertReason;
  final String? lastDate;

  const Stock({
    required this.stockId,
    required this.name,
    required this.sector,
    this.avgDividend2y,
    this.dividend1y,
    this.listingMonths,
    this.closePrice,
    this.estimatedYield,
    this.yield1y,
    required this.alertFlag,
    required this.alertReason,
    this.lastDate,
  });

  factory Stock.fromJson(Map<String, dynamic> json) => Stock(
        stockId: json['stock_id'] as String,
        name: json['name'] as String,
        sector: json['sector'] as String,
        avgDividend2y: (json['avg_dividend_2y'] as num?)?.toDouble(),
        dividend1y: (json['dividend_1y'] as num?)?.toDouble(),
        listingMonths: (json['listing_months'] as num?)?.toInt(),
        closePrice: (json['close_price'] as num?)?.toDouble(),
        estimatedYield: (json['estimated_yield'] as num?)?.toDouble(),
        yield1y: (json['yield_1y'] as num?)?.toDouble(),
        alertFlag: json['alert_flag'] as bool? ?? false,
        alertReason: json['alert_reason'] as String? ?? '',
        lastDate: json['last_date'] as String?,
      );

  /// 上市不滿 2 年（24 個月）視為新上市，股利為上市迄今年化估算
  bool get isNewListing => listingMonths != null && listingMonths! < 24;

  /// 上市不滿 1 年（12 個月）：近一年殖利率資料不足
  bool get isUnder1Y => listingMonths != null && listingMonths! < 12;

  String get sectorLabel => switch (sector) {
        'ETF' => 'ETF',
        'Finance' => '金融',
        'Construction' => '營建',
        'Telecom' => '電信',
        'Food' => '食品',
        'Semiconductor' => '半導體',
        _ => sector,
      };
}
