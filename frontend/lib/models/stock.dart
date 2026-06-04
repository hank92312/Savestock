class Stock {
  final String stockId;
  final String name;
  final String sector;
  final double? avgDividend2y;
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
        closePrice: (json['close_price'] as num?)?.toDouble(),
        estimatedYield: (json['estimated_yield'] as num?)?.toDouble(),
        alertFlag: json['alert_flag'] as bool? ?? false,
        alertReason: json['alert_reason'] as String? ?? '',
        lastDate: json['last_date'] as String?,
      );

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
