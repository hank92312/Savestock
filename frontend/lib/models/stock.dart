class Stock {
  final String stockId;
  final String name;
  final String sector;
  final double? avgDividend2y;
  final int? listingMonths; // 上市迄今月數；< 24 視為新上市
  final double? closePrice;
  final double? estimatedYield;
  final bool alertFlag;
  final String alertReason;
  final String? lastDate;

  const Stock({
    required this.stockId,
    required this.name,
    required this.sector,
    this.avgDividend2y,
    this.listingMonths,
    this.closePrice,
    this.estimatedYield,
    required this.alertFlag,
    required this.alertReason,
    this.lastDate,
  });

  factory Stock.fromJson(Map<String, dynamic> json) => Stock(
        stockId: json['stock_id'] as String,
        name: json['name'] as String,
        sector: json['sector'] as String,
        avgDividend2y: (json['avg_dividend_2y'] as num?)?.toDouble(),
        listingMonths: (json['listing_months'] as num?)?.toInt(),
        closePrice: (json['close_price'] as num?)?.toDouble(),
        estimatedYield: (json['estimated_yield'] as num?)?.toDouble(),
        alertFlag: json['alert_flag'] as bool? ?? false,
        alertReason: json['alert_reason'] as String? ?? '',
        lastDate: json['last_date'] as String?,
      );

  /// 上市不滿 2 年（24 個月）視為新上市，股利為上市迄今年化估算
  bool get isNewListing => listingMonths != null && listingMonths! < 24;

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
