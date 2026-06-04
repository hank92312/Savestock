import 'package:flutter/material.dart';
import '../models/stock.dart';

class SectorBadge extends StatelessWidget {
  final Stock stock;
  const SectorBadge(this.stock, {super.key});

  Color get _color => switch (stock.sector) {
        'ETF' => const Color(0xFF1565C0),
        'Finance' => const Color(0xFF6A1B9A),
        'Construction' => const Color(0xFFE65100),
        'Telecom' => const Color(0xFF00695C),
        'Food' => const Color(0xFF558B2F),
        _ => const Color(0xFF455A64),
      };

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: _color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: _color.withOpacity(0.3)),
      ),
      child: Text(
        stock.sectorLabel,
        style: TextStyle(
          color: _color,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
